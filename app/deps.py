from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.service import TextToSqlAgentService
from app.db import get_session


def get_agent_service(request: Request) -> TextToSqlAgentService:
    """FastAPI-зависимость: сервис агента из состояния приложения.

    В тестах подменяется через app.state.agent_service.
    """
    return request.app.state.agent_service


#: Зависимости объявляются через Annotated, а не значением по умолчанию:
#: `Depends(...)` в дефолте аргумента — вызов на импорте модуля (ruff B008).
SessionDep = Annotated[AsyncSession, Depends(get_session)]
AgentDep = Annotated[TextToSqlAgentService, Depends(get_agent_service)]
