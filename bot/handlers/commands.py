"""Обработчики команд бота."""
from telegram import Update
from telegram.ext import ContextTypes

from bot.storage import get_state, clear_state
from bot.steps.flow import get_step_message, get_step_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start — сброс сессии и показ шага 1."""
    user_id = update.effective_user.id
    state = get_state(user_id)
    # Если пользователь в процессе сценария — не сбрасывать (Telegram может слать /start при открытии чата)
    step = state.get("step", "1")
    in_flow = step != "1" or bool(state.get("data"))
    if in_flow:
        msg = get_step_message(step, state)
        kb = get_step_keyboard(step)
        await update.message.reply_text(msg, reply_markup=kb)
        return
    clear_state(user_id)
    state = get_state(user_id)
    msg = get_step_message("1")
    kb = get_step_keyboard("1")
    await update.message.reply_text(msg, reply_markup=kb)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help — справка и переход в меню."""
    help_text = (
        "📋 Доступные команды:\n\n"
        "/start — Начать работу с ботом (сброс и главное меню)\n"
        "/help — Показать это сообщение\n\n"
        "Бот анализирует проблемы: загрузите схему процесса и результаты интервью → получите анализ и варианты решений."
    )
    await update.message.reply_text(help_text)
    # Переход в меню как при /start
    user_id = update.effective_user.id
    clear_state(user_id)
    state = get_state(user_id)
    msg = get_step_message("1")
    kb = get_step_keyboard("1")
    await update.message.reply_text(msg, reply_markup=kb)


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
