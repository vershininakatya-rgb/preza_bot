"""Главный файл запуска Telegram бота."""
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.config.settings import BOT_TOKEN, HELP_EMAIL, LLM_API_KEY, SMTP_HOST, SMTP_PASSWORD, SMTP_USER
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

    # Регистрируем обработчики
    application.add_handler(CallbackQueryHandler(messages.handle_callback))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, messages.handle_message)
    )
    application.add_handler(
        MessageHandler(filters.PHOTO, messages.handle_photo)
    )
    application.add_handler(
        MessageHandler(filters.Document.ALL, messages.handle_document)
    )

    # Регистрируем обработчик ошибок
    application.add_error_handler(commands.error_handler)

    # Запускаем бота
    logger.info("Бот запущен...")
    if not LLM_API_KEY or LLM_API_KEY.strip() in ("your_llm_api_key_here", "sk-your_openai_api_key_here"):
        logger.warning("LLM_API_KEY не задан — диаграммы и анализ через LLM недоступны")
    else:
        logger.info("LLM_API_KEY загружен (диаграммы и анализ доступны)")
    if all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        logger.info("Email для запросов помощи: настроен → %s", HELP_EMAIL)
    else:
        logger.warning(
            "Email для «Нужна помощь» не настроен. Добавьте в .env: SMTP_HOST, SMTP_USER, SMTP_PASSWORD"
        )
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
