#!/usr/bin/env python3
"""
Инициализация схемы БД для хранения данных бота (Supabase/PostgreSQL).
Создаёт таблицы: telegram_users, analyses, diagrams, feedback_requests.
Включает расширение vector (для RAG).

Запуск один раз после создания проекта Supabase:
  python -m scripts.init_supabase_schema

Требует: DATABASE_URL в .env или в окружении.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

import psycopg
from bot.config.settings import DATABASE_URL


def main() -> None:
    if not DATABASE_URL or not DATABASE_URL.strip():
        print("Ошибка: DATABASE_URL не задан. Задайте в .env или переменной окружения.")
        sys.exit(1)

    schema_path = Path(__file__).resolve().parent / "schema.sql"
    if not schema_path.is_file():
        print(f"Ошибка: файл схемы не найден: {schema_path}")
        sys.exit(1)

    sql = schema_path.read_text(encoding="utf-8")
    # Разбиваем по ";" — каждая часть без ";" в конце; при выполнении добавляем ";"
    parts = [s.strip() for s in sql.split(";") if s.strip()]

    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    try:
        for part in parts:
            conn.execute(part + ";")
        print("Схема успешно применена: telegram_users, analyses, diagrams, feedback_requests, extension vector.")
    except Exception as e:
        print(f"Ошибка при применении схемы: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
