# text2sql-api

Backend API для text2sql-агента на LangGraph. Реализация агента вынесена
за границу `app/agent/service.py::TextToSqlAgentService` (сейчас — заглушка).

## Запуск

```bash
uv sync                       # установка зависимостей
uv run uvicorn app.main:app --reload
```

Документация API: http://localhost:8000/docs

## Тесты

```bash
uv run pytest
```

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| POST | /api/v1/chat | Чат с агентом (ошибки агента → 200 + заглушка, техника в `decision.error_message`) |
| POST | /api/v1/chat/sse | То же, но `decision.message` стримится по токенам (SSE) |
| POST | /api/v1/history | История чата по `chat_id` (`message_id` + `message` + `type`) |
| POST | /api/v1/feedback | Оценка ответа агента (1–5) по `message_id` |
| GET | /api/v1/feedback | Все оценённые ответы чата (`message_id` + `rating`) |
| GET | /api/v1/enrich/{source}/{entity_id} | Данные сущности из источника обогащения |
| GET | /health | Health-check (без авторизации) |

## Обогащение: источники и клиенты

Два слоя с разной ответственностью:

- **Клиент** (`app/clients`) — тонкая обёртка над одним внешним API: base URL,
  таймаут, разбор ответа. Ошибки поднимает свои: `RestClientNotFound` (404
  от внешней системы) и `RestClientError` (всё остальное). Про обогащение
  клиент не знает — его можно использовать где угодно ещё.
- **Источник** (`app/enrichment`) — собирает ответ нашего контракта, дёргая
  один или несколько клиентов, и переводит их ошибки в `EntityNotFound`
  (→ 404) и `EnrichmentError` (→ 502).

Модули из `app/enrichment` импортируются автоматически, поэтому новый
источник = новый файл с `register(...)` внизу; ручной список импортов не
ведётся. Плата за это: модуль источника не должен импортировать сам пакет
`app.enrichment` (только `.base` / `.registry`), а вспомогательные модули
внутри пакета называются с префиксом `_`. Забытый `register(...)` ловит
тест `test_every_source_module_registers_a_source`.

Новый клиент = подкласс `RestClient` + подкласс `RestClientSettings`
с `env_prefix` и дефолтами `url` / `timeout`. Настройки клиента живут рядом
с ним, а не в `app/config.py`.

| Источник | Данные | Пример `entity_id` |
|---|---|---|
| `courses` | мок-словарь в модуле источника | `c-101`, `c-202` |
| `events` | корпоративные мероприятия: `title`, `date`, `location`, `format`, `participants`; мок-словарь в модуле источника | `e-101`, `e-202` |

Живого API ни для курсов, ни для мероприятий нет, поэтому `courses` и
`events` пока отдают данные из словарей в `app/enrichment/courses.py` и
`app/enrichment/events.py`, а не через клиента. Слой клиентов готов и
покрыт тестами; эталонная обвязка — `app/clients/courses.py::CoursesClient`
(настройки `COURSES_CLIENT_URL`, `COURSES_CLIENT_TIMEOUT`). Как только
появится адрес живого API, источник переезжает на клиента: ловит
`RestClientNotFound` / `RestClientError` и переводит в `EntityNotFound` /
`EnrichmentError`. В тестах внешний API подменяется `httpx.MockTransport`.

`httpx.AsyncClient` внутри клиента создаётся лениво (при первом запросе),
а закрывается в lifespan приложения через `app.clients.aclose_all()`.

## Авторизация

Все `/api/v1/*` эндпоинты закрыты JWT Bearer (HS256, секрет — `JWT_SECRET`).
Из клейма `person_id` мидлварь кладёт UUID пользователя в ContextVar
(`app/context.py`).

## Решения и допущения

- **SSE — `sse-starlette`**: де-факто стандарт для FastAPI; корректный
  протокол `text/event-stream`, обработка disconnect, ping — вместо ручного
  `StreamingResponse`.
- **Мидлварь — чистый ASGI**, не `BaseHTTPMiddleware`: тот оборачивает запрос
  в отдельную задачу и плохо дружит с SSE и ContextVar.
- **БД — SQLite/aiosqlite** через SQLAlchemy 2.0 async; переезд на Postgres —
  смена `DATABASE_URL` (+ alembic-миграции вместо `create_all`).
- **Feedback привязан к `message_id`** — публичному UUID сообщения
  (внутренний автоинкрементный id наружу не отдаётся). `/chat` возвращает
  `message_id` ответа агента; оценивать можно только ответы агента.
- **Swagger-авторизация**: реальную проверку делает ASGI-мидлварь, а
  `HTTPBearer(auto_error=False)` как router-dependency лишь объявляет схему
  в OpenAPI — за счёт этого в `/docs` есть кнопка Authorize.
- В интерфейс агента добавлен `stream()` — из `run()` поток токенов не
  получить; у реального LangGraph-агента это будет `astream_events`.
