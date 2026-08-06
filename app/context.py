"""Request-scoped контекст.

person_id устанавливается авторизационным мидлварём (см. app.auth)
и доступен из любого места кода в рамках обработки запроса —
без протаскивания через сигнатуры функций.
"""

from contextvars import ContextVar
from uuid import UUID

person_id_var: ContextVar[UUID | None] = ContextVar("person_id", default=None)


def get_person_id() -> UUID:
    """Вернуть person-id текущего запроса.

    Бросает RuntimeError, если вызвано вне авторизованного запроса —
    это программная ошибка (эндпоинт не закрыт мидлварём), а не 401.
    """
    person_id = person_id_var.get()
    if person_id is None:
        raise RuntimeError(
            "person_id is not set: endpoint is not behind the auth middleware"
        )
    return person_id
