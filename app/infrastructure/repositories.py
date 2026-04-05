from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import insert, ScalarResult, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Order, OrderStatusEnum
from app.infrastructure.db_schema import OrderTable
from app.utils import logging

log = logging.get_logger(__name__)


class DoesNotExist(Exception):
    pass


class OrderRepository:
    class CreateDTO(BaseModel):
        user_id: str
        quantity: int
        item_id: UUID
        idempotency_key: UUID
        status: OrderStatusEnum

    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _construct(row: ScalarResult | None) -> Order:
        if not row:
            raise DoesNotExist("Order does not exist")
        return Order.model_validate(row)

    async def create(self, order: CreateDTO) -> Order:

        stmt = insert(OrderTable).values(**order.model_dump()).returning(OrderTable)
        result = await self._session.execute(stmt)

        return self._construct(result.scalars().first())

    async def get_by_id(self, order_id: UUID) -> Order:
        stmt = select(OrderTable).filter(OrderTable.id == order_id)
        result = await self._session.execute(stmt)

        return self._construct(result.scalars().first())

    async def get_by_idempotency_key(self, idempotency_key: str) -> Order:
        stmt = select(OrderTable).filter(OrderTable.idempotency_key == idempotency_key)
        result = await self._session.execute(stmt)

        return self._construct(result.scalars().first())
