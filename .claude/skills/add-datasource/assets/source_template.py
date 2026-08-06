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

    # --- Вариант B: реальная внешняя система ------------------------------
    # Удалить вариант A и раскомментировать этот.
    #
    # async def fetch(self, entity_id: str) -> dict:
    #     try:
    #         response = await self._client.get(f"/items/{entity_id}")
    #     except Exception as exc:  # сеть/таймаут — внешняя система виновата
    #         raise EnrichmentError(f"TODO upstream failed: {exc}") from exc
    #     if response.status_code == 404:
    #         raise EntityNotFound(f"TODO entity not found: {entity_id}")
    #     if response.status_code >= 400:
    #         raise EnrichmentError(f"TODO upstream returned {response.status_code}")
    #     return response.json()


# Регистрация на импорте модуля — единственный способ попасть в реестр.
# Сам импорт нужно добавить в app/enrichment/__init__.py, иначе модуль
# никто не импортирует и источника в реестре не будет.
register(TemplateSource())
