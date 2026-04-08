from abc import abstractmethod, ABC
from datetime import datetime
from typing import TypeVar, Sequence
from uuid import UUID

from pydantic import BaseModel, field_validator
from sqlalchemy import insert, ScalarResult, select, update, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.exceptions import EntityNotFoundError
from app.domain.models import (
    OrderStatusEnum,
    PaymentStatusEnum,
    OutboxStatusEnum,
    EventTypeEnum,
)
from app.infrastructure.db_schema import OrderTable, PaymentTable, OutboxTable
from app.utils import logging

log = logging.get_logger(__name__)


DomainModel = TypeVar("DomainModel")
ORMModel = TypeVar("ORMModel")


class BaseRepository(ABC):
    class CreateDTO(BaseModel):
        pass

    class UpdateDTO(BaseModel):
        pass

    def __init__(self, session: AsyncSession, domain_model: DomainModel):
        self._session = session
        self._domain_model = domain_model
        self._table_name = self._get_table_name()
        self._id_cols = self._get_primary_key_cols()

    @abstractmethod
    def _get_table_name(self) -> ORMModel:
        pass

    def _get_primary_key_cols(self) -> list[str]:
        """Create and return a list of Primary Key SQL Alchemy Column objects"""
        pk_list = [column.name for column in inspect(self._table_name).primary_key]
        return pk_list

    def _construct(self, row: ScalarResult | None) -> DomainModel:
        if not row:
            raise EntityNotFoundError("Entity does not exist")
        return self._domain_model.model_validate(row)

    async def create(self, obj: CreateDTO) -> DomainModel:
        log.debug(
            "Creating record for %s with data: %s", self._domain_model.__name__, obj
        )
        stmt = (
            insert(self._table_name)
            .values(**obj.model_dump())
            .returning(self._table_name)
        )
        result = await self._session.execute(stmt)

        return self._construct(result.scalars().first())

    async def update(self, target: ORMModel, obj_update: UpdateDTO) -> DomainModel:
        """
        Update an existing record in the database
        Return updated ORMModel object
        """
        obj_update_data = obj_update.model_dump(exclude_unset=True)

        pk_values, target_ids = {}, []

        for col in self._id_cols:
            pk_values[col] = getattr(target, col)
            target_ids.append(getattr(self._table_name, col) == getattr(target, col))

        log.debug(
            "Updating %s record with Primary Key(s): %s with data: %s",
            self._table_name.__name__,
            pk_values,
            obj_update_data,
        )

        stmt = (
            update(self._table_name)
            .filter(*target_ids)
            .values(**obj_update_data)
            .returning(self._table_name)
        )
        result = await self._session.execute(stmt)

        return self._construct(result.scalars().first())

    async def get_by_id(self, target_id: tuple) -> DomainModel:
        log.debug(
            "Getting record from %s with Primary Key(s): %s",
            self._table_name.__name__,
            target_id,
        )
        target_ids = []

        for col, target_val in zip(self._id_cols, target_id):
            target_ids.append(getattr(self._table_name, col) == target_val)

        stmt = select(self._table_name).filter(*target_ids)
        result = await self._session.execute(stmt)
        obj = self._construct(result.scalars().first())
        log.debug("Result for get_by_id: %s", obj)
        return obj

    async def get_by_idempotency_key(self, idempotency_key: str) -> DomainModel:
        log.debug(
            "Getting record from %s with idempotency key: %s",
            self._table_name.__name__,
            idempotency_key,
        )
        stmt = select(self._table_name).filter(
            self._table_name.idempotency_key == idempotency_key
        )
        result = await self._session.execute(stmt)
        obj = self._construct(result.scalars().first())
        log.debug("Result for get_by_idempotency_key: %s", obj)
        return obj


class OrderRepository(BaseRepository):
    class CreateDTO(BaseModel):
        user_id: str
        quantity: int
        item_id: UUID
        idempotency_key: str | UUID | None = None
        status: OrderStatusEnum

        @field_validator("idempotency_key", mode="before")
        @classmethod
        def normalize_idempotency_key(cls, v: UUID | str | None) -> str | None:
            if isinstance(v, UUID):
                return str(v)
            return v

    class UpdateDTO(BaseModel):
        status: OrderStatusEnum

    def _get_table_name(self) -> ORMModel:
        return OrderTable


class PaymentRepository(BaseRepository):
    class CreateDTO(BaseModel):
        id: UUID
        user_id: UUID
        order_id: UUID
        amount: str
        status: PaymentStatusEnum
        idempotency_key: UUID | str | None
        created_at: datetime

        @field_validator("status", mode="before")
        @classmethod
        def normalize_status(cls, v) -> str:
            if isinstance(v, str):
                return v.upper()
            return v

        @field_validator("idempotency_key", mode="before")
        @classmethod
        def normalize_idempotency_key(cls, v: UUID | str | None) -> str | None:
            if isinstance(v, UUID):
                return str(v)
            return v

    class UpdateDTO(BaseModel):
        status: PaymentStatusEnum

        @field_validator("status", mode="before")
        @classmethod
        def normalize_status(cls, v) -> str:
            if isinstance(v, str):
                return v.upper()
            return v

    def _get_table_name(self) -> ORMModel:
        return PaymentTable


class OutboxRepository(BaseRepository):
    class CreateDTO(BaseModel):
        event_type: EventTypeEnum
        order_id: UUID
        item_id: UUID
        quantity: int
        status: OutboxStatusEnum
        retry_count: int

    class UpdateDTO(BaseModel):
        status: OutboxStatusEnum

    def _get_table_name(self) -> ORMModel:
        return OutboxTable

    async def get_pending(self, limit: int = 50) -> Sequence[ScalarResult]:
        stmt = (
            select(self._table_name)
            .filter(OutboxTable.status == OutboxStatusEnum.PENDING)
            .order_by(OutboxTable.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        pending = tuple(self._construct(row) for row in result.scalars().all())
        return pending
