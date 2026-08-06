import uuid

from tests.conftest import EchoAgent


async def _make_agent_message_id(app, client, auth_headers, chat_id) -> str:
    """Прогоняет один обмен через /chat и возвращает message_id ответа агента."""
    app.state.agent_service = EchoAgent()
    resp = await client.post(
        "/api/v1/chat",
        json={"chat_id": chat_id, "query": "сотрудники финансов"},
        headers=auth_headers,
    )
    return resp.json()["message_id"]


async def test_set_and_get_feedback(app, client, auth_headers, chat_id):
    message_id = await _make_agent_message_id(app, client, auth_headers, chat_id)

    resp = await client.post(
        "/api/v1/feedback",
        json={"message_id": message_id, "rating": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    resp = await client.get(
        "/api/v1/feedback", params={"chat_id": chat_id}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["chat_history"] == [{"message_id": message_id, "rating": 5}]


async def test_feedback_for_unknown_message_id_returns_404(client, auth_headers):
    resp = await client.post(
        "/api/v1/feedback",
        json={"message_id": str(uuid.uuid4()), "rating": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_feedback_for_human_message_returns_404(
    app, client, auth_headers, chat_id
):
    """Оценивать можно только ответы агента — сообщение человека не оценивается."""
    await _make_agent_message_id(app, client, auth_headers, chat_id)
    history = await client.post(
        "/api/v1/history", json={"chat_id": chat_id}, headers=auth_headers
    )
    human_id = next(
        m["message_id"] for m in history.json()["chat_history"] if m["type"] == "human"
    )
    resp = await client.post(
        "/api/v1/feedback",
        json={"message_id": human_id, "rating": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_repeated_feedback_overwrites_rating(app, client, auth_headers, chat_id):
    message_id = await _make_agent_message_id(app, client, auth_headers, chat_id)

    for rating in (2, 4):
        resp = await client.post(
            "/api/v1/feedback",
            json={"message_id": message_id, "rating": rating},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    resp = await client.get(
        "/api/v1/feedback", params={"chat_id": chat_id}, headers=auth_headers
    )
    assert resp.json()["chat_history"] == [{"message_id": message_id, "rating": 4}]


async def test_feedback_rating_out_of_range_returns_422(
    app, client, auth_headers, chat_id
):
    message_id = await _make_agent_message_id(app, client, auth_headers, chat_id)
    for bad_rating in (0, 6):
        resp = await client.post(
            "/api/v1/feedback",
            json={"message_id": message_id, "rating": bad_rating},
            headers=auth_headers,
        )
        assert resp.status_code == 422


async def test_feedback_validation_bad_message_id_returns_422(client, auth_headers):
    resp = await client.post(
        "/api/v1/feedback",
        json={"message_id": "not-a-uuid", "rating": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_get_feedback_empty_chat(client, auth_headers, chat_id):
    resp = await client.get(
        "/api/v1/feedback", params={"chat_id": chat_id}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["chat_history"] == []
