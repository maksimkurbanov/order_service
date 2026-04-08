import asyncio

from app.application.write_to_inbox import WriteToInboxUseCase


class InboxWriter:
    def __init__(self, use_case: WriteToInboxUseCase):
        self._use_case = use_case

    async def run(self):
        while True:
            await self._use_case()
            await asyncio.sleep(0.01)
