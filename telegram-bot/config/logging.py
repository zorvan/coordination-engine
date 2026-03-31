"""
Application logging configuration.
"""
import logging
from config.settings import Settings


def setup_logging(settings: Settings) -> logging.Logger:
    """Set up structured logging for the application."""
    log_level_str = settings.log_level or "INFO"
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,
    )
    
    telegram_level = getattr(
        logging,
        (settings.log_level_telegram or "INFO").upper(),
        logging.INFO,
    )
    httpx_level = getattr(
        logging,
        (settings.log_level_httpx or "WARNING").upper(),
        logging.WARNING,
    )

    logging.getLogger("telegram").setLevel(telegram_level)
    logging.getLogger("httpx").setLevel(httpx_level)
    logging.captureWarnings(True)

    logger = logging.getLogger("coord_bot")
    logger.info(
        "Logging configured root=%s telegram=%s httpx=%s",
        log_level_str.upper(),
        logging.getLevelName(telegram_level),
        logging.getLevelName(httpx_level),
    )
    return logger
