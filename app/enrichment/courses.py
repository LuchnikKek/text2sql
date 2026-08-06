"""Источник: Курсы.

Данные пока лежат здесь же: живого API курсов нет. Когда появится —
источник переедет на клиента из app/clients (образец обвязки —
app/clients/courses.py::CoursesClient).
"""

from app.enrichment.base import EntityNotFound
from app.enrichment.registry import register

_COURSES: dict[int, dict] = {
    101: {
        "title": "SQL для аналитиков",
        "hours": 16,
        "level": "beginner",
        "tags": ["sql", "analytics"],
    },
    202: {
        "title": "Оконные функции на практике",
        "hours": 8,
        "level": "advanced",
        "tags": ["sql", "window-functions"],
    },
}


class CoursesSource:
    name = "courses"

    async def fetch(self, entity_id: str) -> dict:
        # entity_id приходит из пути строкой, а ключи курсов — числа
        try:
            course_id = int(entity_id)
        except ValueError:
            raise EntityNotFound(f"Course not found: {entity_id}") from None

        course = _COURSES.get(course_id)
        if course is None:
            raise EntityNotFound(f"Course not found: {entity_id}")
        return dict(course)


register(CoursesSource())
