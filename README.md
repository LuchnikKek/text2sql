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
| GET | /health | Health-check (без авторизации) |

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
