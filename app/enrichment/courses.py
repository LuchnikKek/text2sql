"""Источник: Курсы.

Данные пока лежат здесь же: живого API курсов нет. Когда появится —
источник переедет на клиента из app/clients (образец обвязки —
app/clients/courses.py::CoursesClient).
"""

from app.enrichment.base import EntityNotFound
from app.enrichment.registry import register

_COURSES: dict[str, dict] = {
    "c-101": {
        "title": "SQL для аналитиков",
        "hours": 16,
        "level": "beginner",
        "tags": ["sql", "analytics"],
    },
    "c-202": {
        "title": "Оконные функции на практике",
        "hours": 8,
        "level": "advanced",
        "tags": ["sql", "window-functions"],
    },
}


class CoursesSource:
    name = "courses"

    async def fetch(self, entity_id: str) -> dict:
        course = _COURSES.get(entity_id)
        if course is None:
            raise EntityNotFound(f"Course not found: {entity_id}")
        return dict(course)


register(CoursesSource())
