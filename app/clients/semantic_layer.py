"""MCP-клиент семантического слоя.

В отличие от REST-клиентов этого слоя, ходит не по HTTP, а по MCP:
на каждый вызов поднимает servers/semantic_layer.py отдельным процессом
(stdio) и закрывает его по выходе из контекста. Постоянной сессии нет
намеренно: не нужно управлять жизненным циклом дочернего процесса
(lifespan, реконнекты), а цена — лишь старт процесса на вызов, что для
debug-сценария приемлемо.
"""

from pathlib import Path
from typing import Any

from fastmcp import Client
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Корень репозитория — чтобы относительный server_path работал
#: независимо от текущей директории процесса.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class McpClientError(Exception):
    """MCP-сервер недоступен или вызов тулзы завершился ошибкой."""


class SemanticLayerClientSettings(BaseSettings):
    """Настройки: SEMANTIC_LAYER_CLIENT_SERVER_PATH / _TIMEOUT."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_prefix="SEMANTIC_LAYER_CLIENT_"
    )

    #: путь к скрипту MCP-сервера — абсолютный или от корня репозитория
    server_path: str = "servers/semantic_layer.py"
    #: таймаут одного вызова, секунды
    timeout: float = 10.0


class SemanticLayerClient:
    """Клиент MCP-сервера semantic-layer."""

    name = "semantic-layer"
    settings_class = SemanticLayerClientSettings

    def __init__(
        self,
        settings: SemanticLayerClientSettings | None = None,
        *,
        target: Any | None = None,
    ) -> None:
        # target нужен тестам (in-process инстанс FastMCP); в проде клиент
        # поднимает сервер по stdio из settings.server_path.
        self.settings = settings or self.settings_class()
        self._target = target

    def _connection_target(self) -> Any:
        if self._target is not None:
            return self._target
        path = Path(self.settings.server_path)
        if not path.is_absolute():
            path = _PROJECT_ROOT / path
        return str(path)

    def _connect(self) -> Client:
        return Client(self._connection_target(), timeout=self.settings.timeout)

    async def call_tool(self, tool: str, args: dict[str, Any] | None = None) -> Any:
        """Вызвать тулзу по имени; возвращает распакованный результат."""
        try:
            async with self._connect() as client:
                result = await client.call_tool(tool, args or {})
        except Exception as exc:
            raise McpClientError(f"{self.name}: {tool}: {exc}") from exc
        return result.data

    async def list_tools(self) -> list[dict[str, str | None]]:
        """Имена и описания тулз сервера."""
        try:
            async with self._connect() as client:
                tools = await client.list_tools()
        except Exception as exc:
            raise McpClientError(f"{self.name}: list_tools: {exc}") from exc
        return [{"name": t.name, "description": t.description} for t in tools]

    async def lookup_term(self, term: str) -> dict[str, Any]:
        return await self.call_tool("lookup_term", {"term": term})

    async def list_terms(self) -> str:
        return await self.call_tool("list_terms")
