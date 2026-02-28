"""RAG: поиск релевантных фрагментов в PostgreSQL (pgvector) для аналитики."""
import logging
from typing import Optional

from bot.config.settings import (
    DATABASE_URL,
    LLM_API_KEY,
    RAG_EMBEDDING_DIM,
    RAG_EMBEDDING_MODEL,
    RAG_ENABLED,
    RAG_TOP_K,
)

logger = logging.getLogger(__name__)

# Имя таблицы для чанков
RAG_TABLE = "rag_chunks"


def _get_embedding(text: str) -> Optional[list[float]]:
    """Получить эмбеддинг текста через OpenAI API (синхронно)."""
    if not LLM_API_KEY or not text.strip():
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=LLM_API_KEY)
        response = client.embeddings.create(
            input=text[:8000],  # лимит токенов
            model=RAG_EMBEDDING_MODEL,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return None


async def retrieve_relevant_chunks(query: str, top_k: Optional[int] = None) -> str:
    """
    Найти релевантные фрагменты в базе знаний по запросу.
    Возвращает объединённый текст чанков или пустую строку при ошибке/отключении.
    """
    if not RAG_ENABLED or not DATABASE_URL:
        return ""

    top_k = top_k or RAG_TOP_K
    embedding = _get_embedding(query)
    if not embedding:
        return ""

    try:
        import asyncpg
        from pgvector.asyncpg import register_vector

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await register_vector(conn)
            # <=> — cosine distance (меньше = ближе)
            rows = await conn.fetch(
                f"SELECT content FROM {RAG_TABLE} ORDER BY embedding <=> $1 LIMIT $2",
                embedding,
                top_k,
            )
            if rows:
                return "\n\n---\n\n".join(r["content"] for r in rows)
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("RAG retrieval failed: %s", e)

    return ""
