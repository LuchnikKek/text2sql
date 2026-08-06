"""Источник: TODO человекочитаемое имя (например «Курсы»).

TODO 1–2 строки: что за внешняя система и что именно отдаёт fetch().

Шаблон модуля источника обогащения. Копировать в app/enrichment/<name>.py,
переименовать класс, заполнить TODO, удалить неиспользованный вариант
fetch() внизу файла. Всё, что не помечено TODO, — инварианты слоя
(см. app/enrichment/base.py и registry.py), их менять не нужно.
"""

from app.enrichment.base import EntityNotFound
from app.enrichment.registry import register

# TODO: мок-данные на время разработки. Для реального клиента этот словарь
# удалить целиком и брать данные из внешней системы (см. вариант B ниже).
_ITEMS: dict[str, dict] = {
    "t-101": {
        "title": "TODO",
        "value": 0,
    },
}


class TemplateSource:
    #: TODO: имя в реестре. Оно же — сегмент пути
    #: /api/v1/enrich/<name>/{entity_id}, поэтому: latin, lowercase,
    #: без пробелов, обычно множественное число (courses, employees).
    name = "template"

    # --- Вариант A: данные лежат рядом (мок / статика / локальная БД) ------
    async def fetch(self, entity_id: str) -> dict:
        item = _ITEMS.get(entity_id)
        if item is None:
            # EntityNotFound → роутер отдаёт 404. Любая другая
            # EnrichmentError → 502 (проблема внешней системы, не клиента).
            raise EntityNotFound(f"TODO entity not found: {entity_id}")
        # Отдаём копию: вызывающий не должен мутировать наши данные.
        return dict(item)

    # --- Вариант B: данные из внешнего API ---------------------------------
    # Удалить вариант A вместе с _ITEMS и раскомментировать этот. HTTP тут
    # не пишется руками: сначала заводится клиент в app/clients — из
    # соседнего шаблона assets/client.py (живой ориентир —
    # app/clients/courses.py), источник только переводит его ошибки в свои.
    #
    # def __init__(self, client: TemplateClient | None = None) -> None:
    #     # Клиент параметром — чтобы тесты подсовывали httpx.MockTransport.
    #     self._client = client or TemplateClient()
    #
    # async def fetch(self, entity_id: str) -> dict:
    #     try:
    #         return await self._client.get_item(entity_id)
    #     except RestClientNotFound as exc:
    #         raise EntityNotFound(f"TODO entity not found: {entity_id}") from exc
    #     except RestClientError as exc:
    #         raise EnrichmentError(str(exc)) from exc
    #
    # Источнику можно вызывать несколько клиентов и склеивать их ответы —
    # тогда решить, что делать, если один из них ответил 404: это
    # EntityNotFound или частичные данные.


# Регистрация на импорте модуля — единственный способ попасть в реестр.
# Сам импорт делает автоимпорт пакета (app/enrichment/__init__.py),
# добавлять его руками не нужно; забытый register() ловит тест-сторож.
register(TemplateSource())
