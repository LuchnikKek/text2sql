import uuid

from tests.conftest import EchoAgent


async def test_history_empty_chat_returns_empty_list(client, auth_headers):
    chat_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/history", json={"chat_id": chat_id}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json() == {"chat_id": chat_id, "chat_history": []}


async def test_history_messages_have_unique_message_ids(app, client, auth_headers):
    app.state.agent_service = EchoAgent()
    chat_id = str(uuid.uuid4())
    for query in ["раз", "два"]:
        await client.post(
            "/api/v1/chat",
            json={"chat_id": chat_id, "query": query},
            headers=auth_headers,
        )

    resp = await client.post(
        "/api/v1/history", json={"chat_id": chat_id}, headers=auth_headers
    )
    history = resp.json()["chat_history"]
    ids = [m["message_id"] for m in history]
    assert len(ids) == 4
    assert len(set(ids)) == 4, "message_id должны быть уникальны"
    for message_id in ids:
        uuid.UUID(message_id)


async def test_history_isolated_between_chats(app, client, auth_headers):
    app.state.agent_service = EchoAgent()
    chat_a, chat_b = str(uuid.uuid4()), str(uuid.uuid4())
    await client.post(
        "/api/v1/chat",
        json={"chat_id": chat_a, "query": "вопрос в чат A"},
        headers=auth_headers,
    )

    resp_a = await client.post(
        "/api/v1/history", json={"chat_id": chat_a}, headers=auth_headers
    )
    resp_b = await client.post(
        "/api/v1/history", json={"chat_id": chat_b}, headers=auth_headers
    )
    assert len(resp_a.json()["chat_history"]) == 2
    assert resp_b.json()["chat_history"] == []


async def test_history_validation_bad_chat_id_returns_422(client, auth_headers):
    resp = await client.post(
        "/api/v1/history", json={"chat_id": "nope"}, headers=auth_headers
    )
    assert resp.status_code == 422
