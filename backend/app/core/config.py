from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "校园课程智能助手"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "campus_course_assistant"

    SECRET_KEY: str = "change-me-to-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    DEEPSEEK_API_KEY: str = "sk-your-deepseek-key"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    CHROMA_PATH: str = str(BASE_DIR / "chroma_data")
    CHROMA_COLLECTION: str = "course_materials"

    @property
    def deepseek_ready(self) -> bool:
        key = (self.DEEPSEEK_API_KEY or "").strip()
        return bool(key) and key not in ("sk-your-deepseek-key", "sk-xxxxxx") and "your-deepseek-key" not in key

    @property
    def deepseek_key_masked(self) -> str:
        key = (self.DEEPSEEK_API_KEY or "").strip()
        return f"{key[:6]}...{key[-4:]}" if len(key) > 12 else key

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )

    @property
    def server_database_url(self) -> str:
        """无库名的连接串，用于首次自动建库。"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
