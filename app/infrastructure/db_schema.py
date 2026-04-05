from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Integer,
    text,
    DateTime as saDateTime,
    func,
    String,
    Uuid,
    CheckConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.testing.schema import mapped_column

from app.domain.models import OrderStatusEnum


class Base(DeclarativeBase):
    pass


class OrderTable(Base):
    __tablename__ = "order"

    id: Mapped[UUID] = mapped_column(
        Uuid, server_default=text("gen_random_uuid()"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(String)
    quantity: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("quantity >= 1", name="quantity_ge_1"),
    )
    item_id: Mapped[UUID] = mapped_column(Uuid)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid)
    status: Mapped[OrderStatusEnum] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        saDateTime, server_default=func.timezone("UTC", func.now())
    )
    update_at: Mapped[datetime] = mapped_column(
        saDateTime,
        server_default=func.timezone("UTC", func.now()),
        server_onupdate=func.timezone("UTC", func.now()),
    )
