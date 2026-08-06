"""Проверки OpenAPI-спеки: авторизация должна быть видна в /docs.

Swagger UI рисует кнопку Authorize и поле для токена только если
у операций объявлена security-схема — проверяем это через /openapi.json.
"""


async def test_openapi_declares_bearer_security_scheme(client):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schemes = resp.json()["components"]["securitySchemes"]
    assert "HTTPBearer" in schemes
    assert schemes["HTTPBearer"]["type"] == "http"
    assert schemes["HTTPBearer"]["scheme"] == "bearer"


async def test_all_api_operations_require_bearer(client):
    spec = (await client.get("/openapi.json")).json()
    for path, operations in spec["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for method, operation in operations.items():
            security = operation.get("security", [])
            assert {"HTTPBearer": []} in security, (
                f"{method.upper()} {path} не объявляет bearer-авторизацию в OpenAPI"
            )


async def test_health_does_not_require_auth_in_spec(client):
    spec = (await client.get("/openapi.json")).json()
    assert "security" not in spec["paths"]["/health"]["get"]
