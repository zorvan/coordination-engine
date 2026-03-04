"""
Application logging configuration.
"""
import logging
from config.settings import settings


def setup_logging() -> None:
    """Set up structured logging for the application."""
    log_level_str = settings.log_level or "INFO"
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)