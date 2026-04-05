from uuid import UUID

import httpx

from app.config import settings
from app.domain.models import Item


class CatalogServiceClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=10, headers={"x-api-key": settings.LMS_API_KEY}
        )

    @staticmethod
    def _build_url(path_params: tuple) -> str:
        """Build and return Capashino Catalog Service API URL string"""
        if path_params:
            path_params = "/".join(map(str, path_params)) + "/"
        return f"{settings.CAPASHINO_URL.rstrip('/')}/api/catalog/{path_params}"

    async def get_item(self, item_id: UUID) -> Item:
        response = await self._client.get(self._build_url(("items", item_id)))
        if response.is_error:
            response.raise_for_status()
        return Item(**response.json())

    async def check_stock(self, item_id: UUID, quantity: int) -> bool:
        item = await self.get_item(item_id)
        return item.available_qty >= quantity
