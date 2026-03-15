"""
Сохранение данных бота в PostgreSQL (Supabase): пользователи, аналитика, диаграммы, обратная связь.
Используется только при заданных DATABASE_URL и PERSIST_TO_DB=true.
"""
import json
import logging
from typing import Optional

from bot.config.settings import DATABASE_URL, PERSIST_TO_DB

logger = logging.getLogger(__name__)


def _should_persist() -> bool:
    """Писать в БД только при наличии URL и включённом флаге."""
    return bool(DATABASE_URL and DATABASE_URL.strip() and PERSIST_TO_DB)


async def upsert_user(
    telegram_user_id: int,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
) -> Optional[int]:
    """
    Создать или обновить пользователя; обновить last_seen.
    Возвращает внутренний id (telegram_users.id) или None при ошибке/отключённой персистентности.
    """
    if not _should_persist():
        return None
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO telegram_users (telegram_user_id, username, full_name, first_seen, last_seen)
                VALUES ($1, $2, $3, NOW(), NOW())
                ON CONFLICT (telegram_user_id) DO UPDATE SET
                    username = COALESCE(EXCLUDED.username, telegram_users.username),
                    full_name = COALESCE(EXCLUDED.full_name, telegram_users.full_name),
                    last_seen = NOW()
                RETURNING id
                """,
                telegram_user_id,
                username or None,
                full_name or None,
            )
            return row["id"] if row else None
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("db upsert_user failed: %s", e)
        return None


async def insert_analysis(
    user_id: int,
    input_texts: list[str],
    file_descriptions: list[str],
    analysis_result: Optional[str] = None,
    extra_request: Optional[str] = None,
    extra_result: Optional[str] = None,
) -> Optional[int]:
    """
    Вставить запись анализа. user_id — внутренний id из telegram_users.
    Возвращает id созданной записи (analyses.id) или None.
    """
    if not _should_persist():
        return None
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO analyses (user_id, input_texts, file_descriptions, analysis_result, extra_request, extra_result, created_at, updated_at)
                VALUES ($1, $2::jsonb, $3::jsonb, $4, $5, $6, NOW(), NOW())
                RETURNING id
                """,
                user_id,
                json.dumps(input_texts),
                json.dumps(file_descriptions),
                analysis_result,
                extra_request,
                extra_result,
            )
            return row["id"] if row else None
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("db insert_analysis failed: %s", e)
        return None


async def update_analysis_extra(
    analysis_id: int,
    extra_request: str,
    extra_result: str,
) -> None:
    """Обновить запись анализа: доп. запрос и результат."""
    if not _should_persist():
        return
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                """
                UPDATE analyses SET extra_request = $1, extra_result = $2, updated_at = NOW()
                WHERE id = $3
                """,
                extra_request,
                extra_result,
                analysis_id,
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("db update_analysis_extra failed: %s", e)


async def insert_diagram(
    analysis_id: int,
    user_id: int,
    mermaid_code: Optional[str] = None,
    success: bool = False,
    error_message: Optional[str] = None,
) -> None:
    """Сохранить факт генерации диаграммы. user_id — внутренний id (telegram_users.id)."""
    if not _should_persist():
        return
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                """
                INSERT INTO diagrams (analysis_id, user_id, mermaid_code, success, error_message, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                analysis_id,
                user_id,
                mermaid_code,
                success,
                error_message,
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("db insert_diagram failed: %s", e)


async def insert_feedback(
    user_id: int,
    step: Optional[str],
    message_text: str,
) -> None:
    """Сохранить обратную связь «Нужна помощь». user_id — внутренний id (telegram_users.id)."""
    if not _should_persist():
        return
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                """
                INSERT INTO feedback_requests (user_id, step, message_text, created_at)
                VALUES ($1, $2, $3, NOW())
                """,
                user_id,
                step,
                message_text or "",
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("db insert_feedback failed: %s", e)


async def get_internal_user_id(telegram_user_id: int) -> Optional[int]:
    """
    Получить внутренний id пользователя по telegram_user_id.
    Если пользователя нет — вернёт None (нужно сначала вызвать upsert_user).
    """
    if not _should_persist():
        return None
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            row = await conn.fetchrow(
                "SELECT id FROM telegram_users WHERE telegram_user_id = $1",
                telegram_user_id,
            )
            return row["id"] if row else None
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("db get_internal_user_id failed: %s", e)
        return None
