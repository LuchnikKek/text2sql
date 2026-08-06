import uuid

from app.routers.chat import BUSY_MESSAGE
from tests.conftest import EchoAgent, FailingAgent


async def test_chat_returns_answer(app, client, auth_headers, chat_id):
    app.state.agent_service = EchoAgent()
    resp = await client.post(
        "/api/v1/chat",
        json={"chat_id": chat_id, "query": "верни всех сотрудников"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["chat_id"] == chat_id
    assert data["decision"]["type"] == "answer"
    assert "верни всех сотрудников" in data["decision"]["message"]
    assert data["decision"]["error_message"] is None
    # message_id — валидный UUID и указывает на ответ агента в истории
    uuid.UUID(data["message_id"])


async def test_chat_message_id_points_to_agent_message(
    app, client, auth_headers, chat_id
):
    app.state.agent_service = EchoAgent()
    chat_resp = await client.post(
        "/api/v1/chat",
        json={"chat_id": chat_id, "query": "вопрос"},
        headers=auth_headers,
    )
    message_id = chat_resp.json()["message_id"]

    history_resp = await client.post(
        "/api/v1/history", json={"chat_id": chat_id}, headers=auth_headers
    )
    by_id = {m["message_id"]: m for m in history_resp.json()["chat_history"]}
    assert message_id in by_id
    assert by_id[message_id]["type"] == "agent"


async def test_chat_swallows_agent_errors_as_200(app, client, auth_headers, chat_id):
    """Ошибки агента не должны превращаться в 5xx (см. ТЗ):
    пользователь получает 200 с бизнес-заглушкой, техника — в error_message."""
    app.state.agent_service = FailingAgent()
    resp = await client.post(
        "/api/v1/chat",
        json={"chat_id": chat_id, "query": "boom"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"]["type"] == "error"
    assert data["decision"]["message"] == BUSY_MESSAGE
    assert "LLM provider exploded" in data["decision"]["error_message"]


async def test_chat_persists_dialog(app, client, auth_headers, chat_id):
    app.state.agent_service = EchoAgent()
    for query in ["первый вопрос", "второй вопрос"]:
        await client.post(
            "/api/v1/chat",
            json={"chat_id": chat_id, "query": query},
            headers=auth_headers,
        )

    resp = await client.post(
        "/api/v1/history", json={"chat_id": chat_id}, headers=auth_headers
    )
    history = resp.json()["chat_history"]
    assert len(history) == 4
    assert [m["type"] for m in history] == ["human", "agent", "human", "agent"]
    assert history[0]["message"] == "первый вопрос"
    assert history[2]["message"] == "второй вопрос"


async def test_chat_validation_missing_query_returns_422(client, auth_headers, chat_id):
    resp = await client.post(
        "/api/v1/chat", json={"chat_id": chat_id}, headers=auth_headers
    )
    assert resp.status_code == 422


async def test_chat_validation_bad_chat_id_returns_422(client, auth_headers):
    resp = await client.post(
        "/api/v1/chat",
        json={"chat_id": "not-a-uuid", "query": "hi"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
