"""
Application configuration using pydantic-settings.
Loads values from environment variables and .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database (Neon PostgreSQL + PostGIS)
    database_url: str = "postgresql://localhost:5432/water_access_mapper"

    # OSRM routing
    osrm_base_url: str = "http://router.project-osrm.org"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Development
    debug: bool = True


settings = Settings()


def get_cors_origins() -> list[str]:
    """Parse CORS origins from comma-separated string.
    Also allows any Vercel preview URL for the project."""
    origins = [origin.strip() for origin in settings.cors_origins.split(",")]
    # Allow Vercel preview deployments
    origins.append("https://water-access-mapper.vercel.app")
    return origins
