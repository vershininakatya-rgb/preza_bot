#!/usr/bin/env python3
"""
Скрипт индексации документов для RAG.
Запуск: python -m scripts.build_index

Требует: DATABASE_URL, LLM_API_KEY (или OPENAI_API_KEY) в .env
"""
import os
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

import psycopg
from pgvector.psycopg import register_vector

from bot.config.settings import (
    DATABASE_URL,
    LLM_API_KEY,
    RAG_EMBEDDING_DIM,
    RAG_EMBEDDING_MODEL,
)
from bot.services.rag import RAG_TABLE

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Разбить текст на чанки с перекрытием."""
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Стараемся разбить по границе предложения/абзаца
        if end < len(text):
            for sep in ("\n\n", "\n", ". ", " "):
                idx = chunk.rfind(sep)
                if idx > chunk_size // 2:
                    chunk = chunk[: idx + len(sep)]
                    end = start + len(chunk)
                    break
        chunks.append(chunk.strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]


def load_documents() -> list[tuple[str, str]]:
    """Загрузить документы из knowledge/ (путь, текст)."""
    if not KNOWLEDGE_DIR.exists():
        return []

    from bot.utils.file_extract import extract_text_from_bytes

    docs = []
    for path in sorted(KNOWLEDGE_DIR.rglob("*")):
        if path.is_file():
            ext = path.suffix.lower()
            if ext in (".txt", ".md"):
                text = path.read_text(encoding="utf-8", errors="replace")
            elif ext in (".pdf", ".docx", ".doc"):
                data = path.read_bytes()
                text = extract_text_from_bytes(data, path.name)
            else:
                continue
            if text and text.strip():
                docs.append((str(path.relative_to(KNOWLEDGE_DIR)), text))
    return docs


def get_embedding(text: str):
    """Получить эмбеддинг через OpenAI."""
    if not LLM_API_KEY:
        return None
    from openai import OpenAI

    client = OpenAI(api_key=LLM_API_KEY)
    resp = client.embeddings.create(input=text[:8000], model=RAG_EMBEDDING_MODEL)
    return resp.data[0].embedding


def main() -> None:
    if not DATABASE_URL:
        print("Ошибка: DATABASE_URL не задан в .env")
        sys.exit(1)
    if not LLM_API_KEY:
        print("Ошибка: LLM_API_KEY или OPENAI_API_KEY не задан в .env")
        sys.exit(1)

    docs = load_documents()
    if not docs:
        print(f"Документы не найдены в {KNOWLEDGE_DIR}")
        print("Добавьте .txt, .md, .pdf или .docx файлы и запустите снова.")
        sys.exit(1)

    all_chunks: list[tuple[str, str]] = []
    for source, text in docs:
        for chunk in chunk_text(text):
            all_chunks.append((source, chunk))

    print(f"Загружено {len(docs)} документов, {len(all_chunks)} чанков")

    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    register_vector(conn)

    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RAG_TABLE} (
            id bigserial PRIMARY KEY,
            content text NOT NULL,
            source text,
            embedding vector({RAG_EMBEDDING_DIM})
        )
        """
    )
    conn.execute(f"TRUNCATE TABLE {RAG_TABLE}")

    for i, (source, content) in enumerate(all_chunks):
        emb = get_embedding(content)
        if emb:
            conn.execute(
                f"INSERT INTO {RAG_TABLE} (content, source, embedding) VALUES (%s, %s, %s)",
                (content, source, emb),
            )
        if (i + 1) % 10 == 0:
            print(f"  проиндексировано {i + 1}/{len(all_chunks)}")

    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{RAG_TABLE}_embedding "
        f"ON {RAG_TABLE} USING hnsw (embedding vector_cosine_ops)"
    )

    conn.close()
    print(f"Готово. Таблица {RAG_TABLE}: {len(all_chunks)} записей.")


if __name__ == "__main__":
    main()
