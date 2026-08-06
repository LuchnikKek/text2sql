from fastapi import Request

from app.agent.service import TextToSqlAgentService


def get_agent_service(request: Request) -> TextToSqlAgentService:
    """FastAPI-зависимость: сервис агента из состояния приложения.

    В тестах подменяется через app.state.agent_service.
    """
    return request.app.state.agent_service
