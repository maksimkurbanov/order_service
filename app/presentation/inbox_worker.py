import asyncio

from app.application.process_inbox import ProcessInboxUseCase


class InboxWorker:
    def __init__(self, use_case: ProcessInboxUseCase) -> None:
        self._use_case = use_case

    async def run(self):
        pass
        while True:
            await self._use_case()
            await asyncio.sleep(0.01)
