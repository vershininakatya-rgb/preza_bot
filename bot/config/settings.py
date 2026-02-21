"""Настройки приложения."""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# LLM API Key (опционально; нужен, если бот вызывает LLM для генерации текста/анализа)
# Загружается из .env: LLM_API_KEY
LLM_API_KEY = os.getenv('LLM_API_KEY')

# Настройки логирования
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Проверка наличия обязательных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен! Проверьте файл .env")
