from abc import abstractmethod, ABC
from typing import TypeVar, Sequence, Any
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import insert, ScalarResult, select, update, inspect, tuple_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    OrderStatusEnum,
    PaymentStatusEnum,
    OutboxStatusEnum,
    EventTypeEnum,
    InboxStatusEnum,
)
from app.infrastructure.db_schema import (
    OrderTable,
    PaymentTable,
    OutboxTable,
    InboxTable,
)
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

    def _construct(self, row: ScalarResult | None) -> DomainModel | None:
        if not row:
            return None
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
            self._domain_model.__name__,
            pk_values,
            obj_update_data,
        )

        stmt = (
            update(self._table_name)
            .filter(*target_ids)
            .values(**obj_update_data, update_at=func.timezone("UTC", func.now()))
            .returning(self._table_name)
        )
        result = await self._session.execute(stmt)

        return self._construct(result.scalars().first())

    async def get_by_id(self, target_id: tuple) -> DomainModel:
        log.debug(
            "Getting record from %s with Primary Key(s): %s",
            self._domain_model.__name__,
            target_id,
        )
        target_ids = []

        for col, target_val in zip(self._id_cols, target_id):
            target_ids.append(getattr(self._table_name, col) == target_val)

        stmt = select(self._table_name).filter(*target_ids)
        result = await self._session.execute(stmt)
        obj = self._construct(result.scalars().first())
        log.debug("Result for %s get_by_id: %s", self._domain_model.__name__, obj)
        return obj

    async def get_by_idempotency_key(self, idempotency_key: str) -> DomainModel:
        log.debug(
            "Getting record from %s with idempotency key: %s",
            self._domain_model.__name__,
            idempotency_key,
        )
        stmt = select(self._table_name).filter(
            self._table_name.idempotency_key == idempotency_key
        )
        result = await self._session.execute(stmt)
        obj = self._construct(result.scalars().first())
        log.debug("Result for get_by_idempotency_key: %s", obj)
        return obj

    async def get_many_with_lock(
        self,
        target_ids: list[tuple],
        order_by: str,
        limit: int = 50,
    ) -> dict[Any, DomainModel]:
        """
        Fetch all records satisfying provided args and kwargs filtering,
        with exclusive lock on selected rows, while skipping already
        locked rows, to ensure data integrity in concurrent environment.
        Respects given offset and limit.
        Return list of ORMModel objects or an empty list
        """
        pk_cols = list(inspect(self._table_name).primary_key)

        stmt = (
            select(self._table_name)
            .filter(tuple_(*pk_cols).in_(target_ids))
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        if order_by:
            order_col = getattr(self._table_name, order_by, None)
            if order_col is None:
                raise ValueError(f"Invalid order_by column: {order_by}")
            stmt = stmt.order_by(order_col)

        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        result_dict = {}
        for row in rows:
            obj = self._construct(row)
            if len(pk_cols) == 1:
                pk_key = getattr(obj, pk_cols[0].name)
            else:
                pk_key = tuple(getattr(obj, col.name) for col in pk_cols)
            result_dict[pk_key] = obj

        log.debug(
            "Result for %s get_many_with_lock: %s",
            self._domain_model.__name__,
            result_dict,
        )
        return result_dict


class OrderRepository(BaseRepository):
    class CreateDTO(BaseModel):
        user_id: str
        quantity: int
        item_id: UUID
        idempotency_key: str | UUID | None = None
        status: OrderStatusEnum = OrderStatusEnum.NEW

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
        status: PaymentStatusEnum = PaymentStatusEnum.PENDING
        idempotency_key: UUID | str | None

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
        status: OutboxStatusEnum = OutboxStatusEnum.PENDING
        retry_count: int = 0

    class UpdateDTO(BaseModel):
        event_type: EventTypeEnum = None
        status: OutboxStatusEnum = None

    def _get_table_name(self) -> ORMModel:
        return OutboxTable

    async def get_pending(self, limit: int = 50) -> Sequence[DomainModel]:
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


class InboxRepository(BaseRepository):
    class CreateDTO(BaseModel):
        event_type: EventTypeEnum
        order_id: UUID
        item_id: UUID
        quantity: int
        payload: dict
        status: InboxStatusEnum = InboxStatusEnum.PENDING
        retry_count: int = 0

        @model_validator(mode="before")
        @classmethod
        def extract_payload(cls, values: dict[str, Any]) -> dict[str, Any]:
            known_fields = {
                "event_type",
                "order_id",
                "item_id",
                "quantity",
                "status",
                "retry_count",
            }
            payload = {k: v for k, v in values.items() if k not in known_fields}
            values["payload"] = payload
            return values

        @field_validator("event_type", mode="before")
        @classmethod
        def normalize_event_type(cls, v: str) -> str:
            return v.upper()

    class UpdateDTO(BaseModel):
        event_type: EventTypeEnum = None
        status: InboxStatusEnum = None

    def _get_table_name(self) -> ORMModel:
        return InboxTable

    async def get_pending(self, limit: int = 50) -> Sequence[ScalarResult]:
        stmt = (
            select(self._table_name)
            .filter(InboxTable.status == InboxStatusEnum.PENDING)
            .order_by(InboxTable.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        pending = tuple(self._construct(row) for row in result.scalars().all())
        return pending
