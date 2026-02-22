"""Главный файл запуска Telegram бота."""
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.config.settings import BOT_TOKEN
from bot.handlers import commands, messages
from bot.utils.logger import get_logger

# Настройка логирования
logger = get_logger(__name__)


def main() -> None:
    """Запуск бота."""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", commands.start_command))
    application.add_handler(CommandHandler("help", commands.help_command))

    # Регистрируем обработчик текстовых сообщений
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, messages.handle_message)
    )

    # Регистрируем обработчик ошибок
    application.add_error_handler(commands.error_handler)

    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
