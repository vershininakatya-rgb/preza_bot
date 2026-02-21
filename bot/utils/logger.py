"""Настройка логирования."""
import logging
import sys
from bot.config.settings import LOG_LEVEL, DEBUG

# Настройка формата логирования
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Настройка уровня логирования
log_level = logging.DEBUG if DEBUG else getattr(logging, LOG_LEVEL.upper(), logging.INFO)

# Настройка root logger
logging.basicConfig(
    level=log_level,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def get_logger(name: str) -> logging.Logger:
    """Возвращает настроенный logger."""
    return logging.getLogger(name)
