from uuid import UUID

from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from app.domain.models import OrderStatusEnum, Order
from app.infrastructure.http_clients import CatalogServiceClient
from app.infrastructure.repositories import OrderRepository, DoesNotExist
from app.infrastructure.unit_of_work import UnitOfWork
from app.utils import logging

log = logging.get_logger(__name__)


class OrderDTO(BaseModel):
    user_id: str
    quantity: int = Field(ge=1)
    item_id: UUID
    idempotency_key: str | None = None


class CreateOrderUseCase:
    def __init__(self, unit_of_work: UnitOfWork, catalog_client: CatalogServiceClient):
        self._unit_of_work = unit_of_work
        self._catalog_client = catalog_client

    async def __call__(self, order: OrderDTO) -> Order:
        log.info("Creating order: %s", order)
        async with self._unit_of_work() as uow:
            try:
                if order.idempotency_key:
                    try:
                        existing_order = await uow.orders.get_by_idempotency_key(
                            order.idempotency_key
                        )
                        if existing_order:
                            return existing_order
                    except DoesNotExist:
                        log.debug(
                            "Idempotency key %s not in DB, proceeding with order creation",
                            order,
                        )
                        pass
                sufficient_qty = await self._catalog_client.check_stock(
                    order.item_id, order.quantity
                )
                if not sufficient_qty:
                    return JSONResponse(status_code=400, detail="Insufficient stock")
                order = await uow.orders.create(
                    OrderRepository.CreateDTO(
                        **order.model_dump(), status=OrderStatusEnum.NEW
                    )
                )
                await uow.commit()
                return order
            except Exception as e:
                log.error("Failed to create order: %s", str(e))
                raise
