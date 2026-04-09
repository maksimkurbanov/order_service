from app.domain.models import InboxStatusEnum, OrderStatusEnum
from app.infrastructure.repositories import InboxRepository, OrderRepository
from app.infrastructure.unit_of_work import UnitOfWork
from app.utils import logging

log = logging.get_logger(__name__)


class ProcessInboxUseCase:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def __call__(self):
        async with self._unit_of_work() as uow:
            messages = await uow.inbox.get_pending()
            if not messages:
                return

            order_ids = [tuple([msg.order_id]) for msg in messages]
            orders = await uow.orders.get_many_with_lock(
                order_ids, order_by="created_at"
            )
            order_map = {order.id: order for order in orders}

            for message in messages:
                order = order_map.get(message.order_id)
                if not order:
                    continue

                async with uow.session.begin_nested():
                    try:
                        log.debug("Processing inbox message: %s", message)
                        await uow.inbox.update(
                            message,
                            InboxRepository.UpdateDTO(status=InboxStatusEnum.PROCESSED),
                        )
                        await uow.orders.update(
                            order,
                            OrderRepository.UpdateDTO(
                                status=OrderStatusEnum(
                                    message.value["event_type"].split(".")[1]
                                ),
                            ),
                        )
                    except Exception as e:
                        log.warning(
                            "Inbox message processing failed: %s",
                            e,
                        )
                        raise
            await uow.commit()
