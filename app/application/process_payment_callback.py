from uuid import UUID

from pydantic import BaseModel

from app.domain.models import (
    Payment,
    OrderStatusEnum,
    EventTypeEnum,
)
from app.infrastructure.repositories import (
    PaymentRepository,
    OrderRepository,
    OutboxRepository,
)
from app.infrastructure.unit_of_work import UnitOfWork
from app.utils import logging

log = logging.get_logger(__name__)


class PaymentDTO(BaseModel):
    payment_id: UUID
    order_id: UUID
    status: str
    amount: str
    error_message: str | None


class ProcessPaymentCallbackUseCase:
    def __init__(self, unit_of_work: UnitOfWork):
        self._unit_of_work = unit_of_work

    async def __call__(self, payment: PaymentDTO) -> Payment:
        log.debug("Processing payment callback request with data: %s", payment)
        async with self._unit_of_work() as uow:
            try:
                existing_payment = await uow.payments.get_by_id((payment.payment_id,))
                if existing_payment and existing_payment.status != payment.status:
                    existing_payment = await uow.payments.update(
                        existing_payment,
                        PaymentRepository.UpdateDTO(status=payment.status),
                    )
                    order = await uow.orders.get_by_id((payment.order_id,))
                    inc_order_status = OrderStatusEnum.from_payment_status(
                        payment.status
                    )
                    await uow.orders.update(
                        target=order,
                        obj_update=OrderRepository.UpdateDTO(status=inc_order_status),
                    )
                    await uow.outbox.create(
                        OutboxRepository.CreateDTO(
                            order_id=order.id,
                            event_type=EventTypeEnum.from_payment_status(
                                payment.status
                            ),
                            item_id=order.item_id,
                            quantity=order.quantity,
                        )
                    )
                    await uow.commit()
                return existing_payment
            except Exception as e:
                log.error("Failed to process payment callback: %s", str(e))
                raise
