"""Обработчики команд бота."""
from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Добро пожаловать в бота!\n"
        "Используйте /help для получения списка доступных команд."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    help_text = """
📋 Доступные команды:

/start - Начать работу с ботом
/help - Показать это сообщение

Добавьте свои команды здесь!
    """
    await update.message.reply_text(help_text)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок."""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Update {update} caused error {context.error}")
