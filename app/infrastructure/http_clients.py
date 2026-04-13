from abc import abstractmethod, ABC
from urllib.parse import urljoin, urlsplit, urlunsplit
from datetime import datetime
from uuid import UUID, uuid4

import httpx
from httpx import Request
from pydantic import BaseModel, field_validator

from app.config import settings
from app.domain.models import Item
from app.utils import logging

log = logging.get_logger(__name__)


class PaymentCreateRequest(BaseModel):
    order_id: UUID
    amount: str
    callback_url: str
    idempotency_key: str = None

    @field_validator("idempotency_key", mode="before")
    @classmethod
    def idempotency_key_validator(cls, v):
        if not isinstance(v, str):
            return str(v)
        return v


class PaymentResponse(BaseModel):
    id: UUID
    user_id: UUID
    order_id: UUID
    amount: str
    status: str
    idempotency_key: str | UUID = None
    created_at: datetime


class NotificationCreateRequest(BaseModel):
    message: str
    reference_id: UUID
    idempotency_key: UUID


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    message: str
    reference_id: UUID
    created_at: datetime


class CapashinoServiceClient(ABC):
    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=10,
            headers={"x-api-key": settings.LMS_API_KEY},
            event_hooks={"request": [self._log_request]},
        )
        self._name = self._service_name()
        self._base_url = urljoin(settings.CAPASHINO_URL + "/", f"api/{self._name}")

    @abstractmethod
    def _service_name(self) -> str:
        pass

    def _build_url(self, path_params: tuple | str = "") -> str:
        """Build and return Capashino Service API URL string"""
        path_params_str = "/".join(map(str, path_params))
        return urljoin(self._base_url + "/", path_params_str).rstrip("/")

    async def _log_request(self, request: Request) -> None:
        """Log request to Capashino Service API"""
        log.debug(
            """Request URL: %s
            Request Headers: %s
            Request Body: %s""",
            request.url,
            request.headers,
            request.content.decode(),
        )


class CatalogServiceClient(CapashinoServiceClient):
    def _service_name(self) -> str:
        return "catalog"

    async def get_item(self, item_id: UUID) -> Item:
        response = await self._client.get(self._build_url(("items", item_id)))
        if response.is_error:
            response.raise_for_status()
        return Item(**response.json())

    async def check_stock(self, item_id: UUID, quantity: int) -> tuple[bool, Item]:
        item = await self.get_item(item_id)
        return item.available_qty >= quantity, item


class PaymentsServiceClient(CapashinoServiceClient):
    def _service_name(self) -> str:
        return "payments"

    def _gen_callback_url(self) -> str:
        callback_base_url = urlunsplit(
            urlsplit("//" + settings.CALLBACK_URL, scheme="http")
        )
        return urljoin(callback_base_url + "/", "api/orders/payment-callback")

    async def create_payment(self, order, amount: str) -> PaymentResponse:
        response = await self._client.post(
            self._build_url(),
            json=PaymentCreateRequest(
                order_id=order.id,
                amount=amount,
                callback_url=self._gen_callback_url(),
                idempotency_key=str(uuid4()),
            ).model_dump(mode="json"),
        )
        if response.is_error:
            response.raise_for_status()
        log.debug("Create Payment response: %s", response.json())
        return PaymentResponse(**response.json())


class NotificationsServiceClient(CapashinoServiceClient):
    def _service_name(self) -> str:
        return "notifications"

    def _build_message(self, status: str):
        msg_dict = {
            "NEW": "NEW: Ваш заказ создан и ожидает оплаты.",
            "PAID": "PAID: Ваш заказ успешно оплачен и готов к отправке.",
            "SHIPPED": "SHIPPED: Ваш заказ отправлен в доставку.",
            "CANCELLED": "CANCELLED: Ваш заказ отменен.",
        }
        return msg_dict[status]

    async def send_notification(
        self, status: str, order_id: UUID, idempotency_key: UUID
    ) -> NotificationResponse:
        response = await self._client.post(
            self._build_url(),
            json=NotificationCreateRequest(
                message=self._build_message(status),
                reference_id=order_id,
                idempotency_key=idempotency_key,
            ).model_dump(mode="json"),
        )
        if response.is_error:
            response.raise_for_status()
        log.debug("Send Notification response: %s", response.json())
        return NotificationResponse(**response.json())
