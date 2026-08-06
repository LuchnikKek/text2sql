"""Базовый REST-клиент.

Клиент — тонкая обёртка над одним внешним API: знает свой base_url,
таймаут, разбирает ответ и переводит сетевые/HTTP-проблемы в ошибки этого
слоя. Про обогащение клиент не знает ничего: импортов из app.enrichment
здесь нет и быть не должно — источник ловит наши ошибки и переводит их
в свои (EntityNotFound / EnrichmentError).
"""

from typing import Any
from weakref import WeakSet

import httpx

from app.clients.settings import RestClientSettings


class RestClientError(Exception):
    """Внешний API недоступен или ответил не тем, чего мы ждали."""


class RestClientNotFound(RestClientError):
    """Внешний API ответил 404: запрошенной сущности у него нет."""


#: Созданные клиенты — чтобы lifespan мог закрыть их все.
#: WeakSet: клиент, на который никто не ссылается, не удерживается здесь.
_INSTANCES: "WeakSet[RestClient]" = WeakSet()


class RestClient:
    """Базовый класс клиента. Наследник задаёт name и settings_class."""

    #: Имя клиента — попадает в сообщения об ошибках.
    name: str = "rest"
    #: Класс настроек; наследник подставляет свой с env_prefix и дефолтами.
    settings_class: type[RestClientSettings] = RestClientSettings

    def __init__(
        self,
        settings: RestClientSettings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # transport нужен тестам (httpx.MockTransport); в проде не передаётся.
        self.settings = settings or self.settings_class()
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        _INSTANCES.add(self)

    def _get_client(self) -> httpx.AsyncClient:
        """httpx-клиент, создаваемый лениво.

        Лениво — потому что источники создаются на импорте модуля, а импорт
        не должен открывать сокеты и требовать живого event loop.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.settings.url,
                timeout=self.settings.timeout,
                transport=self._transport,
            )
        return self._client

    async def get(self, path: str, *, params: dict | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def _request(
        self, method: str, path: str, *, params: dict | None = None
    ) -> Any:
        """Единственное место, где HTTP-проблемы становятся нашими ошибками."""
        client = self._get_client()
        try:
            response = await client.request(method, path, params=params)
        except httpx.HTTPError as exc:
            # Сеть, таймаут, DNS — виновата внешняя система, не вызывающий.
            raise RestClientError(f"{self.name}: request failed: {exc}") from exc

        if response.status_code == 404:
            raise RestClientNotFound(f"{self.name}: not found: {response.url}")
        if response.status_code >= 400:
            raise RestClientError(
                f"{self.name}: HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise RestClientError(f"{self.name}: invalid JSON in response") from exc

    async def aclose(self) -> None:
        """Закрыть соединения. Идемпотентно."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


async def aclose_all() -> None:
    """Закрыть все созданные клиенты (вызывается из lifespan в app/main.py).

    Нужно потому, что источники — модульные синглтоны, создаваемые на
    импорте: до app.state они не дотягиваются и закрыть их адресно неоткуда.
    """
    for client in list(_INSTANCES):
        await client.aclose()
