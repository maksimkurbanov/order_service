from app.domain.models import InboxStatusEnum, OrderStatusEnum
from app.infrastructure.repositories import (
    InboxRepository,
    OrderRepository,
    OutboxRepository,
)
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
            log.debug("Processing inbox messages: %s", order_ids)
            orders = await uow.orders.get_many_with_lock(
                order_ids, order_by="created_at"
            )

            for message in messages:
                order = orders.get(message.order_id)
                if not order:
                    continue

                async with uow.session.begin_nested():
                    try:
                        log.debug("Processing inbox message: %s", message)
                        await uow.inbox.update(
                            message,
                            InboxRepository.UpdateDTO(status=InboxStatusEnum.PROCESSED),
                        )
                        (
                            await uow.orders.update(
                                order,
                                OrderRepository.UpdateDTO(
                                    status=OrderStatusEnum.from_event_type(
                                        message.event_type
                                    ),
                                ),
                            ),
                        )
                        await uow.outbox.create(
                            OutboxRepository.CreateDTO(
                                order_id=order.id,
                                event_type=message.event_type.upper(),
                                item_id=order.item_id,
                                quantity=order.quantity,
                            )
                        )
                    except Exception as e:
                        log.warning(
                            "Inbox message processing failed: %s",
                            e,
                        )
            await uow.commit()
