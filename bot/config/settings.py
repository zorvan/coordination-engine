"""
Application configuration management.
Loads environment variables and provides centralized access to settings.
"""
import os
from typing import Optional
from dotenv import load_dotenv


load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        self.telegram_token = self._get_env("TELEGRAM_TOKEN")
        self.db_url = self._get_env("DB_URL")
        self.ai_endpoint = self._get_env("AI_ENDPOINT", "http://127.0.0.1:8080/v1/chat/completions")
        self.ai_model = self._get_env("AI_MODEL", "qwen/qwen-2-7b-instruct")
        self.ai_api_key = self._get_env("AI_API_KEY", "dummy-key")
        self.log_level = self._get_env("LOG_LEVEL", "INFO")
        self.log_level_telegram = self._get_env("LOG_LEVEL_TELEGRAM", "INFO")
        self.log_level_httpx = self._get_env("LOG_LEVEL_HTTPX", "WARNING")
    
    @staticmethod
    def _get_env(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """Get environment variable with validation."""
        value = os.environ.get(name, default)
        if required and not value:
            raise ValueError(f"Required environment variable '{name}' is not set")
        return value


settings = Settings()
