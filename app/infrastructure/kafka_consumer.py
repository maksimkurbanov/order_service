import json

from aiokafka import AIOKafkaConsumer


class KafkaConsumer(AIOKafkaConsumer):
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self):
        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            enable_auto_commit=False,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            key_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        await self._consumer.start()

    async def stop(self):
        if self._consumer:
            await self._consumer.stop()

    async def consume(self):
        if not self._consumer:
            raise RuntimeError("Kafka Consumer not initialized")
        return await self._consumer.getone()

    async def __aenter__(self) -> KafkaConsumer:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
