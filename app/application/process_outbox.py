import asyncio
import random

from pydantic import BaseModel, field_validator

from app.domain.models import OutboxStatusEnum
from app.infrastructure.kafka_producer import KafkaProducer
from app.infrastructure.repositories import OutboxRepository
from app.infrastructure.unit_of_work import UnitOfWork
from app.utils import logging

log = logging.get_logger(__name__)


class OutboxDTO(BaseModel):
    event_type: str
    order_id: str
    item_id: str
    quantity: int
    idempotency_key: str

    @field_validator("event_type", mode="before")
    @classmethod
    def lowercase_event_type(cls, v) -> str:
        return v.lower()


class ProcessOutboxUseCase:
    def __init__(
        self, unit_of_work: UnitOfWork, kafka_producer: KafkaProducer, max_retries: int
    ):
        self._unit_of_work = unit_of_work
        self._kafka_producer = kafka_producer
        self._max_retries = max_retries

    async def __call__(self):
        async with self._unit_of_work() as uow:
            events = await uow.outbox.get_pending()
            if not events:
                return

            async with self._kafka_producer as kp:
                for event in events:
                    for attempt in range(1, self._max_retries + 1):
                        async with uow.session.begin_nested():
                            try:
                                log.debug("Sending event: %s", event)
                                await kp.send_message(
                                    message=OutboxDTO(
                                        **event.model_dump(mode="json")
                                    ).model_dump(),
                                    key=event.idempotency_key,
                                )
                                await uow.outbox.update(
                                    event,
                                    OutboxRepository.UpdateDTO(
                                        status=OutboxStatusEnum.SENT
                                    ),
                                )
                                break
                            except Exception as e:
                                log.warning(
                                    "Attempt %s/%s failed for event: %s: %s",
                                    attempt,
                                    self._max_retries,
                                    event.idempotency_key,
                                    e,
                                )
                                if attempt == self._max_retries:
                                    log.error(
                                        "All retries exhausted for event: %s",
                                        event.idempotency_key,
                                    )
                                else:
                                    delay = 1 * (2 ** (attempt - 1)) + random.uniform(
                                        0, 1
                                    )
                                    await asyncio.sleep(delay)
            await uow.commit()
