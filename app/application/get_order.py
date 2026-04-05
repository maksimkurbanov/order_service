from app.infrastructure.unit_of_work import UnitOfWork
from app.utils import logging

log = logging.get_logger(__name__)


class GetOrderUseCase:
    def __init__(self, unit_of_work: UnitOfWork):
        self._unit_of_work = unit_of_work

    async def __call__(self, order_id):
        async with self._unit_of_work() as uow:
            try:
                return await uow.orders.get_by_id(order_id)
            except Exception as e:
                log.error("Failed to get order: %s", str(e))
                raise
