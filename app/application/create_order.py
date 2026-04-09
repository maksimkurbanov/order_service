from uuid import UUID

from pydantic import BaseModel, Field

from app.application.exceptions import (
    OperationFailedError,
)
from app.domain.models import OrderStatusEnum, Order
from app.infrastructure.http_clients import CatalogServiceClient, PaymentsServiceClient
from app.infrastructure.repositories import OrderRepository, PaymentRepository
from app.infrastructure.unit_of_work import UnitOfWork
from app.utils import logging

log = logging.get_logger(__name__)


class InsufficientStock(OperationFailedError):
    pass


class OrderDTO(BaseModel):
    user_id: str
    quantity: int = Field(ge=1)
    item_id: UUID
    idempotency_key: str | None = None


class CreateOrderUseCase:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        catalog_client: CatalogServiceClient,
        payments_client: PaymentsServiceClient,
    ):
        self._unit_of_work = unit_of_work
        self._catalog_client = catalog_client
        self._payments_client = payments_client

    async def __call__(self, order: OrderDTO) -> Order:
        log.info("Create order request with data: %s", order)
        async with self._unit_of_work() as uow:
            if order.idempotency_key:
                existing_order = await uow.orders.get_by_idempotency_key(
                    order.idempotency_key
                )
                if existing_order:
                    log.debug(
                        "Idempotency key %s in DB, creation aborted, returning DB entry",
                        order.idempotency_key,
                    )
                    return existing_order
                log.debug(
                    "Idempotency key %s not in DB, proceeding with order creation",
                    order.idempotency_key,
                )

            sufficient_qty, item = await self._catalog_client.check_stock(
                order.item_id, order.quantity
            )
            if not sufficient_qty:
                raise InsufficientStock("Insufficient stock")

            try:
                new_order = await uow.orders.create(
                    OrderRepository.CreateDTO(
                        **order.model_dump(), status=OrderStatusEnum.NEW
                    )
                )
                amount = f"{(order.quantity * item.price):.2f}"
                payment = await self._payments_client.create_payment(new_order, amount)
                await uow.payments.create(
                    PaymentRepository.CreateDTO(
                        **payment.model_dump(exclude={"created_at"})
                    )
                )
            except Exception as e:
                await uow.orders.update(
                    new_order,
                    OrderRepository.UpdateDTO(status=OrderStatusEnum.CANCELLED),
                )
                log.error("Failed to create order: %s", str(e))
                raise
            finally:
                await uow.commit()
            return new_order
