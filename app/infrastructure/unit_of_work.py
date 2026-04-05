from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.infrastructure.repositories import OrderRepository


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
        self._session = session
        self._order_repo = OrderRepository(session)

    @property
    def orders(self) -> OrderRepository:
        return self._order_repo

    async def commit(self):
        return await self._session.commit()
