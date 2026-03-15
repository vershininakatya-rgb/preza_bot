"""Обработчики команд бота."""
import time
from telegram import Update
from telegram.ext import ContextTypes

from bot.config.settings import get_log_chat_id, set_log_chat_id
from bot.storage import get_state, set_state, clear_state
from bot.storage.db import upsert_user
from bot.steps.flow import get_step_message, get_step_keyboard, get_step_inline_keyboard
from bot.utils.monitoring import log_activity, send_activity_to_telegram
from bot.utils.reply import reply_with_photo


def _duration_sec(state: dict) -> float | None:
    t = state.get("step_entered_at")
    if t is None:
        return None
    return time.time() - t


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start — сброс сессии и показ шага 1."""
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup", "channel") and get_log_chat_id() is None:
        set_log_chat_id(chat.id)
        await send_activity_to_telegram(
            context.bot,
            f"Этот чат выбран для логов мониторинга. Chat ID: {chat.id}",
        )
        return

    user_id = update.effective_user.id
    user = update.effective_user
    state = get_state(user_id)
    # Если пользователь в процессе сценария — не сбрасывать (Telegram может слать /start при открытии чата)
    step = state.get("step", "1")
    duration = _duration_sec(state)
    in_flow = step != "1" or bool(state.get("data"))
    if in_flow:
        log_activity(context.bot, user, "команда /start", step, step, duration, None)
        msg = get_step_message(step, state)
        parse_mode = "Markdown"
        if step == "2_result" and state.get("analysis_result"):
            msg = state["analysis_result"]
            parse_mode = "HTML"
        elif step == "2_extra_result" and state.get("extra_result"):
            msg = state["extra_result"]
            parse_mode = "HTML"
        kb = get_step_inline_keyboard(step) or get_step_keyboard(step)
        await reply_with_photo(update, msg, step, kb, parse_mode=parse_mode)
        return
    log_activity(context.bot, user, "команда /start", step, "1", duration, None)
    clear_state(user_id)
    state = get_state(user_id)
    state["step_entered_at"] = time.time()
    set_state(user_id, state)
    # Сохранение пользователя в БД (при включённой персистентности)
    first = (getattr(user, "first_name", None) or "").strip()
    last = (getattr(user, "last_name", None) or "").strip()
    full_name = (first + " " + last).strip() if last else first
    await upsert_user(user_id, getattr(user, "username", None), full_name or None)
    msg = get_step_message("1")
    kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
    await reply_with_photo(update, msg, "1", kb)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help — справка и переход в меню."""
    user_id = update.effective_user.id
    user = update.effective_user
    state = get_state(user_id)
    step = state.get("step", "1")
    duration = _duration_sec(state)
    log_activity(context.bot, user, "команда /help", step, "1", duration, None)

    help_text = (
        "📋 Команды:\n\n"
        "/start — начать с начала (главное меню)\n"
        "/help — эта справка\n\n"
        "Я помогу разобрать процессы и команду, подготовить анализ и варианты решений. Загрузи данные — и пойдём по шагам, спокойно и с результатом. 🦭"
    )
    await reply_with_photo(update, help_text, "1")
    # Переход в меню как при /start
    clear_state(user_id)
    state = get_state(user_id)
    state["step_entered_at"] = time.time()
    set_state(user_id, state)
    msg = get_step_message("1")
    kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
    await reply_with_photo(update, msg, "1", kb)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок."""
    import logging
    from telegram.error import Conflict

    logger = logging.getLogger(__name__)
    err = context.error

    if isinstance(err, Conflict):
        logger.error(
            "409 Conflict: уже запущен другой экземпляр бота. "
            "Остановите его: make stop или pkill -f 'python run.py'"
        )
        return

    logger.error("Update %s caused error %s", update, err)
