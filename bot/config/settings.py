"""Настройки приложения."""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# LLM API Key (опционально; нужен для анализа). Поддерживаются LLM_API_KEY и OPENAI_API_KEY
LLM_API_KEY = os.getenv('LLM_API_KEY') or os.getenv('OPENAI_API_KEY')

# Chat ID для личных сообщений: сюда приходят запросы «Нужна помощь» только в личку, не в чат пользователя
# Укажите свой числовой chat_id (например, для @over_chernova). Узнать: @userinfobot в Telegram
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# Chat ID для логов мониторинга (опционально). Если не задан — определяется при /start в группе/канале
LOG_CHAT_ID = os.getenv('LOG_CHAT_ID')
LOG_CHAT_ID_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'log_chat_id.txt')
# После миграции группы в супергруппу Telegram отдаёт новый chat_id; сохраняем его здесь и в файле
_resolved_log_chat_id: str | None = None

# RAG (PostgreSQL + pgvector)
DATABASE_URL = os.getenv('DATABASE_URL')
RAG_ENABLED = os.getenv('RAG_ENABLED', 'false').lower() == 'true'
# Сохранение данных бота в БД (пользователи, аналитика, диаграммы, обратная связь)
PERSIST_TO_DB = os.getenv('PERSIST_TO_DB', 'true').lower() == 'true'
RAG_TOP_K = int(os.getenv('RAG_TOP_K', '5'))
RAG_EMBEDDING_MODEL = os.getenv('RAG_EMBEDDING_MODEL', 'text-embedding-3-small')
RAG_EMBEDDING_DIM = 1536  # для text-embedding-3-small

# Настройки логирования
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Проверка наличия обязательных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен! Проверьте файл .env")


def get_log_chat_id() -> str | None:
    """Chat ID для отправки логов мониторинга: resolved (после миграции) > env > файл."""
    if _resolved_log_chat_id:
        return _resolved_log_chat_id
    if LOG_CHAT_ID and str(LOG_CHAT_ID).strip():
        return str(LOG_CHAT_ID).strip()
    if os.path.isfile(LOG_CHAT_ID_FILE):
        try:
            with open(LOG_CHAT_ID_FILE, 'r', encoding='utf-8') as f:
                value = f.read().strip()
            if value:
                return value
        except OSError:
            pass
    return None


def set_log_chat_id(chat_id: int | str) -> None:
    """Сохранить chat_id чата для логов в файл."""
    path = LOG_CHAT_ID_FILE
    dirpath = os.path.dirname(path)
    if dirpath and not os.path.isdir(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(str(chat_id))


def set_resolved_log_chat_id(chat_id: str | int) -> None:
    """Задать chat_id после миграции группы в супергруппу (используется и сохраняется в файл)."""
    global _resolved_log_chat_id
    _resolved_log_chat_id = str(chat_id)
    set_log_chat_id(chat_id)
