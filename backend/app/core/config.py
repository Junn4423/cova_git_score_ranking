"""
Application configuration loaded from .env file.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Resolve config dir
CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
ENV_FILE = CONFIG_DIR / ".env"


class Settings(BaseSettings):
    # GitHub
    GITHUB_TOKEN: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_ORG: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Database
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "eng_analytics"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    # Backend
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    SECRET_KEY: str = "change_me_in_production"

    # Frontend
    VITE_API_URL: str = "http://localhost:8000"

    @property
    def DATABASE_URL(self) -> str:
        password_part = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else ""
        return (
            f"mysql+pymysql://{self.DB_USER}{password_part}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
