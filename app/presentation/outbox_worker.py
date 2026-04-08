import asyncio

from app.application.process_outbox import ProcessOutboxUseCase


class OutboxWorker:
    def __init__(self, use_case: ProcessOutboxUseCase) -> None:
        self._use_case = use_case

    async def run(self):
        while True:
            await self._use_case()
            await asyncio.sleep(0.01)
