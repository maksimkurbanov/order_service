from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.domain.models import Order, Payment, Outbox, Inbox
from app.infrastructure.repositories import (
    OrderRepository,
    PaymentRepository,
    OutboxRepository,
    InboxRepository,
)


class UnitOfWork:
    def __init__(self, session_factory=async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def __call__(self):
        async with self._session_factory() as session:
            try:
                yield _UnitOfWorkImplementation(session)
                await session.rollback()
            except Exception:
                await session.rollback()
                raise


class _UnitOfWorkImplementation:
    def __init__(self, session):
        self.session = session
        self._order_repo = OrderRepository(session, Order)
        self._payment_repo = PaymentRepository(session, Payment)
        self._outbox_repo = OutboxRepository(session, Outbox)
        self._inbox_repo = InboxRepository(session, Inbox)

    @property
    def orders(self) -> OrderRepository:
        return self._order_repo

    @property
    def payments(self) -> PaymentRepository:
        return self._payment_repo

    @property
    def outbox(self) -> OutboxRepository:
        return self._outbox_repo

    @property
    def inbox(self) -> InboxRepository:
        return self._inbox_repo

    async def commit(self):
        return await self.session.commit()
