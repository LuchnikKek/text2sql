import uuid

import jwt

from tests.conftest import TEST_SECRET


async def test_no_token_returns_401(client, chat_id):
    resp = await client.post("/api/v1/chat", json={"chat_id": chat_id, "query": "hi"})
    assert resp.status_code == 401


async def test_wrong_signature_returns_401(client, chat_id):
    token = jwt.encode(
        {"person_id": str(uuid.uuid4())},
        "another-secret-0123456789abcdef-0123456789",
        algorithm="HS256",
    )
    resp = await client.post(
        "/api/v1/chat",
        json={"chat_id": chat_id, "query": "hi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_token_without_person_id_claim_returns_401(client, chat_id):
    token = jwt.encode({"sub": "someone"}, TEST_SECRET, algorithm="HS256")
    resp = await client.post(
        "/api/v1/chat",
        json={"chat_id": chat_id, "query": "hi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_malformed_authorization_header_returns_401(client, chat_id):
    resp = await client.post(
        "/api/v1/chat",
        json={"chat_id": chat_id, "query": "hi"},
        headers={"Authorization": "Basic abc"},
    )
    assert resp.status_code == 401


async def test_all_api_endpoints_are_protected(client, chat_id):
    protected = [
        ("POST", "/api/v1/chat"),
        ("POST", "/api/v1/chat/sse"),
        ("POST", "/api/v1/history"),
        ("POST", "/api/v1/feedback"),
        ("GET", f"/api/v1/feedback?chat_id={chat_id}"),
    ]
    for method, url in protected:
        resp = await client.request(method, url, json={"chat_id": chat_id})
        assert resp.status_code == 401, f"{method} {url} is not protected"


async def test_health_is_open(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
