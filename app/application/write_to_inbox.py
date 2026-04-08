from uuid import UUID

from app.domain.models import EventTypeEnum, InboxStatusEnum
from app.infrastructure.kafka_consumer import KafkaConsumer
from app.infrastructure.repositories import InboxRepository
from app.infrastructure.unit_of_work import UnitOfWork
from app.utils import logging

log = logging.get_logger(__name__)


class IncomingDTO:
    event_type: EventTypeEnum
    order_id: UUID
    item_id: UUID
    quantity: int


class WriteToInboxUseCase:
    def __init__(self, unit_of_work: UnitOfWork, kafka_consumer: KafkaConsumer) -> None:
        self._unit_of_work = unit_of_work
        self._consumer = kafka_consumer

    async def __call__(self) -> None:
        async with self._unit_of_work() as uow, self._consumer as consumer:
            try:
                message = await consumer.consume()
                if not message:
                    return

                log.info("Handling incoming message: %s", message)
                inc_event_type = message.value["event_type"].upper()
                existing_msg = await uow.inbox.get_by_id(
                    (
                        inc_event_type,
                        message.value["order_id"],
                        message.value["item_id"],
                    )
                )
                if existing_msg and inc_event_type != existing_msg.event_type:
                    uow.inbox.update(
                        existing_msg,
                        InboxRepository.UpdateDTO(event_type=inc_event_type),
                    )
                if not existing_msg:
                    uow.inbox.create(
                        InboxRepository.CreateDTO(
                            **message.value,
                            status=InboxStatusEnum.PENDING,
                            retry_count=0,
                        )
                    )
                await uow.commit()
                await consumer.commit()
            except Exception as e:
                log.error("Error while handling incoming message", e)
