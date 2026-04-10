from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderStatusEnum(StrEnum):
    NEW = "NEW"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"

    @classmethod
    def from_payment_status(cls, payment_status: str) -> OrderStatusEnum:
        mapping = {
            "succeeded": cls.PAID,
            "failed": cls.CANCELLED,
        }
        return mapping.get(payment_status)

    @classmethod
    def from_event_type(cls, payment_status: str) -> OrderStatusEnum:
        mapping = {
            "ORDER.CREATED": cls.NEW,
            "ORDER.PAID": cls.PAID,
            "ORDER.SHIPPED": cls.SHIPPED,
            "ORDER.CANCELLED": cls.CANCELLED,
        }
        return mapping.get(payment_status)


class PaymentStatusEnum(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class EventTypeEnum(StrEnum):
    CREATED = "ORDER.CREATED"
    PAID = "ORDER.PAID"
    SHIPPED = "ORDER.SHIPPED"
    CANCELLED = "ORDER.CANCELLED"

    @classmethod
    def from_payment_status(cls, payment_status: str) -> EventTypeEnum:
        mapping = {
            "succeeded": cls.PAID,
            "failed": cls.CANCELLED,
        }
        return mapping.get(payment_status)


class OutboxStatusEnum(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"


class InboxStatusEnum(StrEnum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"


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


class Outbox(BaseModel):
    idempotency_key: UUID
    event_type: EventTypeEnum
    order_id: UUID
    item_id: UUID
    quantity: int
    status: OutboxStatusEnum
    retry_count: int
    created_at: datetime
    update_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Inbox(BaseModel):
    event_type: EventTypeEnum
    order_id: UUID
    item_id: UUID
    quantity: int
    payload: dict
    status: InboxStatusEnum
    retry_count: int
    created_at: datetime
    update_at: datetime

    model_config = ConfigDict(from_attributes=True)
