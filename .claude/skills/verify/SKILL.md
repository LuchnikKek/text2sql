---
name: verify
description: Полная проверка проекта text2sql-api — тесты, OpenAPI-контракт, живой smoke-тест. Use when the user asks to verify, check, or validate changes, or after any code modification.
allowed-tools: Bash(uv sync), Bash(uv run:*), Bash(rm -f text2sql.db), Bash(curl:*), Bash(pkill -f uvicorn:*)
---

Выполни полную проверку проекта по шагам:

1. `uv run pytest -q` — все тесты. Если есть красные: покажи упавшие,
   объясни причину, НЕ чини без запроса пользователя.
2. Убедись, что OpenAPI-контракт цел: тесты в `tests/test_openapi.py`
   зелёные (bearer-схема объявлена на всех /api/v1 операциях).
3. Smoke-тест живого сервера: подними `uv run uvicorn app.main:app`
   на свободном порту, проверь `/health`, один вызов `/api/v1/chat`
   с валидным JWT (секрет из app/config.py по умолчанию) и 401 без
   токена. Останови сервер, удали временный text2sql.db.
4. Итог одной таблицей: тесты (кол-во passed/failed), OpenAPI, smoke.
   Если всё зелёное — одна строка «всё зелёное», без пересказа шагов.
