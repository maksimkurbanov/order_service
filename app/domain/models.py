from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderStatusEnum(StrEnum):
    NEW = "NEW"
    PAYED = "PAYED"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"

    @classmethod
    def from_payment_status(cls, payment_status: str) -> OrderStatusEnum:
        mapping = {
            "succeeded": cls.PAYED,
            "failed": cls.CANCELLED,
        }
        return mapping.get(payment_status)


class PaymentStatusEnum(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class Order(BaseModel):
    id: UUID
    user_id: str
    quantity: int = Field(ge=1)
    item_id: UUID
    status: OrderStatusEnum
    created_at: datetime
    update_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Item(BaseModel):
    id: UUID
    name: str
    price: Decimal
    available_qty: int
    created_at: datetime


class Payment(BaseModel):
    id: UUID
    user_id: UUID
    order_id: UUID
    amount: str
    status: PaymentStatusEnum
    idempotency_key: str | UUID
    created_at: datetime
    update_at: datetime

    model_config = ConfigDict(from_attributes=True)
