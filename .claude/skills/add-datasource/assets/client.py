"""Клиент: TODO имя внешнего API (например «API курсов»).

Шаблон клиента. Копировать в app/clients/<name>.py, переименовать классы,
заполнить TODO. Всё, что не помечено TODO, — инварианты слоя
(см. app/clients/base.py), их менять не нужно.

Клиент = один внешний API. Про обогащение он не знает: поднимает свои
RestClientNotFound / RestClientError, а переводит их в EntityNotFound /
EnrichmentError уже источник в app/enrichment. Импортировать app.enrichment
отсюда нельзя — иначе слой перестанет быть переиспользуемым.
"""

from pydantic_settings import SettingsConfigDict

from app.clients.base import RestClient
from app.clients.settings import RestClientSettings


class TemplateClientSettings(RestClientSettings):
    # model_config подкласса мержится с родительским (pydantic v2), поэтому
    # env_file/extra наследуются и здесь достаточно префикса. Он же задаёт
    # имена переменных: TEMPLATE_CLIENT_URL, TEMPLATE_CLIENT_TIMEOUT.
    # TODO: префикс по имени клиента, UPPER_SNAKE с завершающим `_`.
    model_config = SettingsConfigDict(env_prefix="TEMPLATE_CLIENT_")

    # TODO: base_url внешнего API и разумный таймаут. Здесь только дефолты,
    # которые переопределяются окружением; секретам и токенам тут не место.
    url: str = "https://api.example.com/template"
    timeout: float = 5.0


class TemplateClient(RestClient):
    #: TODO: имя клиента — попадает в текст ошибок (RestClientError).
    name = "template"
    settings_class = TemplateClientSettings

    # TODO: по методу на ручку API. Возвращаем разобранный JSON: статусы и
    # сетевые сбои уже превращены в RestClientNotFound / RestClientError
    # в RestClient._request, ловить httpx здесь не нужно и не следует —
    # иначе маппинг ошибок расползётся по клиентам.
    async def get_item(self, item_id: str) -> dict:
        return await self.get(f"/{item_id}")


# Инстанс здесь НЕ создаётся: реестра клиентов нет, клиент создаёт источник
# (`self._client = client or TemplateClient()`). httpx.AsyncClient внутри
# поднимается лениво — при первом запросе, а не на импорте, — и закрывается
# в lifespan приложения через app.clients.aclose_all().
#
# В тестах клиент собирается со своим транспортом, ходить в сеть не нужно:
#     TemplateClient(transport=httpx.MockTransport(handler))
# см. tests/test_clients.py::make_client.
