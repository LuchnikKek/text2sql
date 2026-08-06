"""Клиент API курсов."""

from pydantic_settings import SettingsConfigDict

from app.clients.base import RestClient
from app.clients.settings import RestClientSettings


class CoursesClientSettings(RestClientSettings):
    # model_config подкласса мержится с родительским (pydantic v2),
    # поэтому env_file/extra наследуются, а здесь достаточно префикса:
    # COURSES_CLIENT_URL, COURSES_CLIENT_TIMEOUT.
    model_config = SettingsConfigDict(env_prefix="COURSES_CLIENT_")

    url: str = "https://api.example.com/courses"
    timeout: float = 5.0


class CoursesClient(RestClient):
    name = "courses"
    settings_class = CoursesClientSettings

    async def get_course(self, course_id: str) -> dict:
        return await self.get(f"/{course_id}")
