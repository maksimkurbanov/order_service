from uuid import UUID

from pydantic import BaseModel

from app.domain.models import Payment, OrderStatusEnum
from app.infrastructure.repositories import PaymentRepository, OrderRepository
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
                if existing_payment.status != payment.status:
                    await uow.payments.update(
                        payment.payment_id,
                        PaymentRepository.UpdateDTO(status=payment.status),
                    )
                    await uow.orders.update(
                        payment.order_id,
                        OrderRepository.UpdateDTO(
                            status=OrderStatusEnum.from_payment_status(payment.status)
                        ),
                    )
                    await uow.commit()
                return existing_payment
            except Exception as e:
                log.error("Failed to process payment callback: %s", str(e))
                raise
