"""
Application configuration using pydantic-settings.
Loads values from environment variables and .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://localhost:5432/water_access_mapper"

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # OSRM routing
    osrm_base_url: str = "http://router.project-osrm.org"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Development
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def get_cors_origins() -> list[str]:
    """Parse CORS origins from comma-separated string."""
    return [origin.strip() for origin in settings.cors_origins.split(",")]
