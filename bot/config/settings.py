"""Настройки приложения."""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Настройки логирования
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Проверка наличия обязательных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен! Проверьте файл .env")
