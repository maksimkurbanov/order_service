from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.domain.models import EventTypeEnum
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
                await uow.inbox.create(
                    InboxRepository.CreateDTO(
                        **message.value,
                    )
                )
                await uow.commit()
            except Exception as e:
                if isinstance(e, IntegrityError):
                    log.info(
                        "Message with id %s %s already exists, skipping creation",
                        message.value.order_id,
                        message.value.event_type,
                    )
                log.error("Error while handling incoming message: %s", e)
