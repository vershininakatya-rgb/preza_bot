"""Логирование активности пользователей в Telegram-чат для мониторинга."""
import asyncio
import logging
import re
from datetime import datetime
from typing import Any

import os

from bot.config.settings import get_log_chat_id, set_resolved_log_chat_id

logger = logging.getLogger(__name__)

# Таймаут неактивности перед отправкой лога (секунды). По умолчанию 5 мин; для проверки можно задать LOG_SESSION_TIMEOUT_SEC=60
try:
    SESSION_TIMEOUT_SEC = int(os.environ.get("LOG_SESSION_TIMEOUT_SEC", "300"))
except (TypeError, ValueError):
    SESSION_TIMEOUT_SEC = 300

_buffers: dict[int, dict[str, Any]] = {}  # user_id -> {"lines": [...], "username": str, "full_name": str, "user_id": int}
_timers: dict[int, asyncio.Task[None]] = {}


def _format_line(
    action_type: str,
    step_before: str,
    step_after: str,
    duration_sec: float | None,
    details: str | None,
) -> str:
    now = datetime.now().strftime("%H:%M:%S")
    if step_before == step_after:
        step_str = f"шаг {step_before}"
    else:
        step_str = f"шаг {step_before} → {step_after}"
    if duration_sec is None:
        duration_str = "на шаге — с"
    else:
        duration_str = f"на шаге {int(round(duration_sec))} с"
    parts = [now, action_type, step_str, duration_str]
    if details:
        parts.insert(3, details)
    return " | ".join(parts)


def _format_user_label(username: str | None, full_name: str | None, user_id: int) -> str:
    """Собирает подпись пользователя: имя из Telegram, @username при наличии, id."""
    parts = []
    if full_name and full_name.strip():
        parts.append(full_name.strip())
    uname = (username or "").strip()
    if uname and uname != "без ника":
        parts.append(f"@{uname}")
    parts.append(f"id {user_id}")
    return " | ".join(parts)


def _build_message(username: str, full_name: str, user_id: int, lines: list[str]) -> str:
    label = _format_user_label(username or None, full_name or None, user_id)
    header = f"——— {label} ———"
    return header + "\n\n" + "\n".join(lines)


def _parse_migrated_chat_id(error_message: str) -> str | None:
    """Если Telegram вернул 'Group migrated to supergroup. New chat id: -100...' — извлечь новый id."""
    match = re.search(r"New chat id:\s*(-?\d+)", str(error_message), re.IGNORECASE)
    return match.group(1) if match else None


async def _send_to_telegram(bot: Any, text: str) -> None:
    chat_id = get_log_chat_id()
    if not chat_id:
        return
    if len(text) > 4096:
        text = text[:4093] + "..."
    try:
        await bot.send_message(chat_id=int(chat_id), text=text)
        logger.info("Лог мониторинга отправлен в чат %s", chat_id)
    except Exception as e:
        err_str = str(e)
        new_id = _parse_migrated_chat_id(err_str)
        if new_id:
            set_resolved_log_chat_id(new_id)
            logger.info("Чат логов мигрировал в супергруппу, использован новый id: %s", new_id)
            try:
                await bot.send_message(chat_id=int(new_id), text=text)
                logger.info("Лог мониторинга отправлен в чат %s", new_id)
            except Exception as e2:
                logger.warning("Повторная отправка в новый чат не удалась: %s", e2)
        else:
            logger.warning(
                "Не удалось отправить лог в Telegram (чат %s). Проверьте: бот добавлен в канал как админ с правом публикации? Ошибка: %s",
                chat_id,
                e,
            )


async def _delayed_flush(user_id: int, bot: Any) -> None:
    await asyncio.sleep(SESSION_TIMEOUT_SEC)
    data = _buffers.pop(user_id, None)
    _timers.pop(user_id, None)
    if not data or not data.get("lines"):
        return
    username = data.get("username") or "без ника"
    full_name = data.get("full_name") or ""
    lines = data["lines"]
    user_id_val = data.get("user_id", user_id)
    text = _build_message(
        username if username != "без ника" else None,
        full_name,
        user_id_val,
        lines,
    )
    await _send_to_telegram(bot, text)


def log_activity(
    bot: Any,
    user: Any,
    action_type: str,
    step_before: str,
    step_after: str,
    duration_sec: float | None,
    details: str | None = None,
) -> None:
    """
    Добавить строку в буфер пользователя и перезапустить таймер отправки (5 мин).
    Не отправляет сообщение сразу — буфер отправится одним сообщением после 5 мин бездействия.
    """
    chat_id = get_log_chat_id()
    if chat_id is None:
        logger.debug("LOG_CHAT_ID не задан — лог мониторинга не отправляется")
        return
    user_id = user.id if hasattr(user, "id") else int(user)
    username = (getattr(user, "username", None) or "").strip() or None
    full_name = (getattr(user, "first_name", "") or "").strip()
    if getattr(user, "last_name", None):
        full_name = (full_name + " " + (user.last_name or "").strip()).strip()
    line = _format_line(action_type, step_before, step_after, duration_sec, details)

    if user_id not in _buffers:
        _buffers[user_id] = {"lines": [], "username": username or "без ника", "full_name": full_name, "user_id": user_id}
    _buffers[user_id]["lines"].append(line)
    _buffers[user_id]["username"] = username or "без ника"
    _buffers[user_id]["full_name"] = full_name
    _buffers[user_id]["user_id"] = user_id

    if user_id in _timers:
        _timers[user_id].cancel()
    task = asyncio.create_task(_delayed_flush(user_id, bot))
    _timers[user_id] = task


async def send_activity_to_telegram(bot: Any, text: str) -> None:
    """Отправить произвольный текст в чат логов (для подтверждения выбора чата и т.п.)."""
    await _send_to_telegram(bot, text)
