"""Настройки приложения."""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# LLM API Key (опционально; нужен для анализа). Поддерживаются LLM_API_KEY и OPENAI_API_KEY
LLM_API_KEY = os.getenv('LLM_API_KEY') or os.getenv('OPENAI_API_KEY')

# Chat ID администратора для уведомлений «Нужна помощь» (опционально)
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# RAG (PostgreSQL + pgvector)
DATABASE_URL = os.getenv('DATABASE_URL')
RAG_ENABLED = os.getenv('RAG_ENABLED', 'false').lower() == 'true'
RAG_TOP_K = int(os.getenv('RAG_TOP_K', '5'))
RAG_EMBEDDING_MODEL = os.getenv('RAG_EMBEDDING_MODEL', 'text-embedding-3-small')
RAG_EMBEDDING_DIM = 1536  # для text-embedding-3-small

# Настройки логирования
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Проверка наличия обязательных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен! Проверьте файл .env")
