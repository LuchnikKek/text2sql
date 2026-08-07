"""Источник: Корпоративные мероприятия.

Данные пока лежат здесь же: живого API мероприятий нет. Когда появится —
источник переедет на клиента из app/clients (образец обвязки —
app/clients/courses.py::CoursesClient).
"""

from app.enrichment.base import EntityNotFound
from app.enrichment.registry import register

_EVENTS: dict[int, dict] = {
    101: {
        "title": "Летний тимбилдинг",
        "date": "2026-07-18",
        "location": "Москва, Парк Горького",
        "format": "offline",
        "participants": 120,
    },
    202: {
        "title": "Внутренний митап по данным",
        "date": "2026-09-24",
        "location": "Zoom",
        "format": "online",
        "participants": 45,
    },
}


class EventsSource:
    name = "events"

    async def fetch(self, entity_id: str) -> dict:
        # entity_id приходит из пути строкой, а ключи мероприятий — числа
        try:
            event_id = int(entity_id)
        except ValueError:
            raise EntityNotFound(f"Event not found: {entity_id}") from None

        event = _EVENTS.get(event_id)
        if event is None:
            raise EntityNotFound(f"Event not found: {entity_id}")
        return dict(event)


register(EventsSource())
