"""
Сохранение данных бота: Supabase REST API или PostgreSQL (asyncpg).
При заданных SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY используется REST API;
иначе — DATABASE_URL и asyncpg. Включение записи: PERSIST_TO_DB=true.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from bot.config.settings import (
    DATABASE_URL,
    PERSIST_TO_DB,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
)

logger = logging.getLogger(__name__)

_supabase_client: Any = None


def _use_supabase_rest() -> bool:
    """Использовать Supabase REST API для записи (нужны URL и service_role key)."""
    return bool(
        SUPABASE_URL and SUPABASE_URL.strip()
        and SUPABASE_SERVICE_ROLE_KEY and SUPABASE_SERVICE_ROLE_KEY.strip()
    )


def _should_persist() -> bool:
    """Писать в БД: включён флаг и есть либо Supabase REST, либо DATABASE_URL."""
    if not PERSIST_TO_DB:
        return False
    if _use_supabase_rest():
        return True
    return bool(DATABASE_URL and DATABASE_URL.strip())


def _get_supabase_client():
    """Ленивое создание клиента Supabase (синхронный)."""
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_client


# --- Supabase REST (синхронные вызовы, запускаем в to_thread) ---


def _supabase_upsert_user(
    telegram_user_id: int,
    username: Optional[str],
    full_name: Optional[str],
) -> Optional[int]:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    row = {
        "telegram_user_id": telegram_user_id,
        "username": username,
        "full_name": full_name,
        "last_seen": now,
    }
    resp = _get_supabase_client().table("telegram_users").upsert(
        row, on_conflict="telegram_user_id"
    ).execute()
    if resp.data and len(resp.data) > 0:
        return resp.data[0].get("id")
    return None


def _supabase_insert_analysis(
    user_id: int,
    input_texts: list,
    file_descriptions: list,
    analysis_result: Optional[str],
    extra_request: Optional[str],
    extra_result: Optional[str],
) -> Optional[int]:
    row = {
        "user_id": user_id,
        "input_texts": input_texts,
        "file_descriptions": file_descriptions,
        "analysis_result": analysis_result,
        "extra_request": extra_request,
        "extra_result": extra_result,
    }
    resp = _get_supabase_client().table("analyses").insert(row).execute()
    if resp.data and len(resp.data) > 0:
        return resp.data[0].get("id")
    return None


def _supabase_update_analysis_extra(
    analysis_id: int, extra_request: str, extra_result: str
) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _get_supabase_client().table("analyses").update({
        "extra_request": extra_request,
        "extra_result": extra_result,
        "updated_at": now,
    }).eq("id", analysis_id).execute()


def _supabase_insert_diagram(
    analysis_id: int,
    user_id: int,
    mermaid_code: Optional[str],
    success: bool,
    error_message: Optional[str],
) -> None:
    _get_supabase_client().table("diagrams").insert({
        "analysis_id": analysis_id,
        "user_id": user_id,
        "mermaid_code": mermaid_code,
        "success": success,
        "error_message": error_message,
    }).execute()


def _supabase_insert_feedback(
    user_id: int, step: Optional[str], message_text: str
) -> None:
    _get_supabase_client().table("feedback_requests").insert({
        "user_id": user_id,
        "step": step,
        "message_text": message_text or "",
    }).execute()


def _supabase_get_internal_user_id(telegram_user_id: int) -> Optional[int]:
    resp = (
        _get_supabase_client()
        .table("telegram_users")
        .select("id")
        .eq("telegram_user_id", telegram_user_id)
        .execute()
    )
    if resp.data and len(resp.data) > 0:
        return resp.data[0].get("id")
    return None


# --- Публичные async-функции ---


async def upsert_user(
    telegram_user_id: int,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
) -> Optional[int]:
    """
    Создать или обновить пользователя; обновить last_seen.
    Возвращает внутренний id (telegram_users.id) или None.
    """
    if not _should_persist():
        return None
    if _use_supabase_rest():
        try:
            return await asyncio.to_thread(
                _supabase_upsert_user,
                telegram_user_id,
                username or None,
                full_name or None,
            )
        except Exception as e:
            logger.warning("db upsert_user (Supabase REST) failed: %s", e)
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
    """Вставить запись анализа. user_id — внутренний id из telegram_users. Возвращает analyses.id или None."""
    if not _should_persist():
        return None
    if _use_supabase_rest():
        try:
            return await asyncio.to_thread(
                _supabase_insert_analysis,
                user_id,
                input_texts,
                file_descriptions,
                analysis_result,
                extra_request,
                extra_result,
            )
        except Exception as e:
            logger.warning("db insert_analysis (Supabase REST) failed: %s", e)
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
    if _use_supabase_rest():
        try:
            await asyncio.to_thread(
                _supabase_update_analysis_extra,
                analysis_id,
                extra_request,
                extra_result,
            )
        except Exception as e:
            logger.warning("db update_analysis_extra (Supabase REST) failed: %s", e)
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
    if _use_supabase_rest():
        try:
            await asyncio.to_thread(
                _supabase_insert_diagram,
                analysis_id,
                user_id,
                mermaid_code,
                success,
                error_message,
            )
        except Exception as e:
            logger.warning("db insert_diagram (Supabase REST) failed: %s", e)
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
    if _use_supabase_rest():
        try:
            await asyncio.to_thread(
                _supabase_insert_feedback,
                user_id,
                step,
                message_text or "",
            )
        except Exception as e:
            logger.warning("db insert_feedback (Supabase REST) failed: %s", e)
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
    """Получить внутренний id по telegram_user_id. Если нет — None (сначала upsert_user)."""
    if not _should_persist():
        return None
    if _use_supabase_rest():
        try:
            return await asyncio.to_thread(
                _supabase_get_internal_user_id,
                telegram_user_id,
            )
        except Exception as e:
            logger.warning("db get_internal_user_id (Supabase REST) failed: %s", e)
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
