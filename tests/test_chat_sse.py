import json
import uuid

from app.routers.chat import BUSY_MESSAGE
from tests.conftest import EchoAgent, FailingAgent


def _parse_sse(text: str) -> list[dict]:
    """Разбирает SSE-поток на события: [{'event': str, 'data': str}, ...].

    Событие без строки 'event:' — безымянное (message), как в спецификации.
    """
    events = []
    for block in text.split("\r\n\r\n"):
        block = block.strip("\r\n")
        if not block:
            continue
        event_name = "message"
        data_lines = []
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data_lines.append(line.removeprefix("data: "))
        if data_lines:
            events.append({"event": event_name, "data": "\n".join(data_lines)})
    return events


def _tokens(events: list[dict]) -> list[str]:
    return [e["data"] for e in events if e["event"] == "message"]


def _decision_event(events: list[dict]) -> dict:
    decisions = [e for e in events if e["event"] == "decision"]
    assert len(decisions) == 1, "должен быть ровно один финальный decision-event"
    return json.loads(decisions[0]["data"])


async def _stream(client, auth_headers, chat_id, query) -> list[dict]:
    async with client.stream(
        "POST",
        "/api/v1/chat/sse",
        json={"chat_id": chat_id, "query": query},
        headers=auth_headers,
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        body = (await resp.aread()).decode()
    return _parse_sse(body)


async def test_sse_streams_message_by_tokens(app, client, auth_headers, chat_id):
    app.state.agent_service = EchoAgent()
    events = await _stream(client, auth_headers, chat_id, "стримь")

    tokens = _tokens(events)
    assert len(tokens) > 1, "ответ должен прийти несколькими токенами"
    assert "".join(tokens) == "SELECT * FROM employees -- for: стримь"


async def test_sse_final_decision_event(app, client, auth_headers, chat_id):
    app.state.agent_service = EchoAgent()
    events = await _stream(client, auth_headers, chat_id, "стримь")

    final = _decision_event(events)
    assert final["chat_id"] == chat_id
    uuid.UUID(final["message_id"])
    assert final["decision"]["type"] == "answer"
    assert final["decision"]["message"] == "".join(_tokens(events))
    assert final["decision"]["error_message"] is None


async def test_sse_decision_event_is_last(app, client, auth_headers, chat_id):
    app.state.agent_service = EchoAgent()
    events = await _stream(client, auth_headers, chat_id, "стримь")
    assert events[-1]["event"] == "decision"


async def test_sse_error_streams_busy_stub_and_error_decision(
    app, client, auth_headers, chat_id
):
    app.state.agent_service = FailingAgent()
    events = await _stream(client, auth_headers, chat_id, "boom")

    assert "".join(_tokens(events)) == BUSY_MESSAGE
    final = _decision_event(events)
    assert final["decision"]["type"] == "error"
    assert final["decision"]["message"] == BUSY_MESSAGE
    assert "LLM provider exploded" in final["decision"]["error_message"]


async def test_sse_persists_dialog(app, client, auth_headers, chat_id):
    app.state.agent_service = EchoAgent()
    events = await _stream(client, auth_headers, chat_id, "стримь")

    resp = await client.post(
        "/api/v1/history", json={"chat_id": chat_id}, headers=auth_headers
    )
    history = resp.json()["chat_history"]
    assert [m["type"] for m in history] == ["human", "agent"]
    assert history[0]["message"] == "стримь"
    assert history[1]["message"] == "SELECT * FROM employees -- for: стримь"
    # message_id из финального event указывает на сохранённый ответ агента
    assert _decision_event(events)["message_id"] == history[1]["message_id"]


async def test_sse_client_disconnect_stops_stream_and_persists_partial(
    app, client, auth_headers, chat_id, monkeypatch
):
    """Разрыв соединения клиентом: стрим останавливается досрочно,
    частичный диалог персистится, финальный decision-event не отправляется.

    Разрыв симулируем через Request.is_disconnected: с ASGITransport
    настоящий disconnect не воспроизвести (нет живого сокета).
    """
    app.state.agent_service = EchoAgent()

    calls = 0

    async def fake_is_disconnected(self) -> bool:
        nonlocal calls
        calls += 1
        return calls > 3  # первые 3 токена уходят, дальше «клиент отвалился»

    monkeypatch.setattr(
        "starlette.requests.Request.is_disconnected", fake_is_disconnected
    )

    events = await _stream(client, auth_headers, chat_id, "стримь")
    tokens = _tokens(events)

    full_message = "SELECT * FROM employees -- for: стримь"
    assert 0 < len(tokens) == 3, "стрим должен оборваться после 3 токенов"
    assert "".join(tokens) != full_message
    assert not [e for e in events if e["event"] == "decision"], (
        "отключившемуся клиенту decision-event не отправляется"
    )

    # Частичный ответ — в истории (то, что клиент успел увидеть)
    resp = await client.post(
        "/api/v1/history", json={"chat_id": chat_id}, headers=auth_headers
    )
    history = resp.json()["chat_history"]
    assert [m["type"] for m in history] == ["human", "agent"]
    assert history[1]["message"] == "".join(tokens)


async def test_sse_message_id_is_rateable(app, client, auth_headers, chat_id):
    """Интеграция: message_id из SSE можно оценить через /feedback."""
    app.state.agent_service = EchoAgent()
    events = await _stream(client, auth_headers, chat_id, "стримь")
    message_id = _decision_event(events)["message_id"]

    resp = await client.post(
        "/api/v1/feedback",
        json={"message_id": message_id, "rating": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
