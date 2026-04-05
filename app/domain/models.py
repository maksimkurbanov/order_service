from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderStatusEnum(StrEnum):
    NEW = "NEW"
    PAYED = "PAYED"
    SHIPPED = "SHIPPED"
    CANCELED = "CANCELED"


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
