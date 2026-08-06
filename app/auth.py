"""Авторизационный мидлварь.

Реализован как чистый ASGI-мидлварь (а не BaseHTTPMiddleware) сознательно:
BaseHTTPMiddleware оборачивает запрос в отдельную задачу и исторически
плохо дружит со стриминговыми ответами (SSE) и распространением ContextVar.
Чистый ASGI-вариант вызывает приложение в том же контексте, поэтому
person_id, установленный здесь, виден и в эндпоинтах, и внутри
SSE-генераторов.
"""

from uuid import UUID

import jwt
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.context import person_id_var

# Пути, доступные без токена (документация и health-check)
EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class AuthMiddleware:
    def __init__(self, app: ASGIApp, *, secret: str, algorithm: str = "HS256") -> None:
        self.app = app
        self.secret = secret
        self.algorithm = algorithm

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        authorization = headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")

        if scheme.lower() != "bearer" or not token:
            await self._unauthorized(scope, receive, send, "Missing bearer token")
            return

        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            person_id = UUID(str(payload["person_id"]))
        except (jwt.InvalidTokenError, KeyError, ValueError):
            await self._unauthorized(scope, receive, send, "Invalid token")
            return

        ctx_token = person_id_var.set(person_id)
        try:
            await self.app(scope, receive, send)
        finally:
            person_id_var.reset(ctx_token)

    @staticmethod
    async def _unauthorized(
        scope: Scope, receive: Receive, send: Send, detail: str
    ) -> None:
        response = JSONResponse({"detail": detail}, status_code=401)
        await response(scope, receive, send)
