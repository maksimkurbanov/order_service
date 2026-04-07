from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Integer,
    text,
    DateTime as saDateTime,
    func,
    String,
    Uuid,
    CheckConstraint,
    DECIMAL,
    TypeDecorator,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship
from sqlalchemy.testing.schema import mapped_column

from app.domain.models import OrderStatusEnum, PaymentStatusEnum


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
    idempotency_key: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    status: Mapped[OrderStatusEnum] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        saDateTime, server_default=func.timezone("UTC", func.now())
    )
    update_at: Mapped[datetime] = mapped_column(
        saDateTime,
        server_default=func.timezone("UTC", func.now()),
        server_onupdate=func.timezone("UTC", func.now()),
    )

    payment: Mapped["PaymentTable"] = relationship(
        back_populates="order", uselist=False
    )


class StrToDecimal(TypeDecorator):
    """Converts string to Decimal with 2‑digit precision for storage."""

    impl = DECIMAL(precision=10, scale=2)  # 10 total digits, 2 decimal places
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert Python string (or Decimal) to Decimal for the database."""
        if not isinstance(value, Decimal):
            return Decimal(str(value)).quantize(Decimal("0.01"))
        return value

    def process_result_value(self, value, dialect):
        """Convert database Decimal back to string."""
        if value is None:
            return None
        return f"{value:.2f}"


class PaymentTable(Base):
    __tablename__ = "payment"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid)
    order_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("order.id"))
    amount: Mapped[str] = mapped_column(StrToDecimal)
    status: Mapped[PaymentStatusEnum] = mapped_column(String)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid, nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(saDateTime(timezone=True))
    update_at: Mapped[datetime] = mapped_column(
        saDateTime,
        server_default=func.timezone("UTC", func.now()),
        server_onupdate=func.timezone("UTC", func.now()),
    )

    order: Mapped["OrderTable"] = relationship(back_populates="payment")
