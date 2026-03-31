"""
Application configuration management.
Loads environment variables and provides centralized access to settings.
"""
import os
from dotenv import load_dotenv


load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        self.telegram_token: str | None = os.environ.get("TELEGRAM_TOKEN")
        self.db_url: str | None = os.environ.get("DB_URL")
        self.ai_endpoint: str = os.environ.get(
            "AI_ENDPOINT", "http://127.0.0.1:8080/v1/"
        )
        self.ai_model: str = os.environ.get("AI_MODEL", "qwen/qwen3-coder-next")
        self.ai_api_key: str = os.environ.get("AI_API_KEY", "dummy-key")
        self.log_level: str = os.environ.get("LOG_LEVEL", "INFO")
        self.log_level_telegram: str = os.environ.get("LOG_LEVEL_TELEGRAM", "INFO")
        self.log_level_httpx: str = os.environ.get("LOG_LEVEL_HTTPX", "WARNING")


settings = Settings()
