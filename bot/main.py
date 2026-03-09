"""Главный файл запуска Telegram бота."""
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.config.settings import BOT_TOKEN, LLM_API_KEY, get_log_chat_id
from bot.handlers import commands, messages
from bot.utils.logger import get_logger
from bot.utils.monitoring import send_activity_to_telegram

# Настройка логирования
logger = get_logger(__name__)


async def _post_init_send_log_test(application: Application) -> None:
    """При старте отправить в канал логов тестовое сообщение — проверка, что канал доступен."""
    if not get_log_chat_id():
        return
    try:
        await send_activity_to_telegram(
            application.bot,
            "✅ Логи мониторинга подключены. Через 5 мин неактивности пользователя сюда придёт сводка.",
        )
    except Exception as e:
        logger.warning("Не удалось отправить тест в канал логов: %s", e)


def main() -> None:
    """Запуск бота."""
    # Создаем приложение
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(_post_init_send_log_test)
        .build()
    )

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
    log_chat = get_log_chat_id()
    if log_chat:
        logger.info("Логи мониторинга будут отправляться в чат: %s", log_chat)
    else:
        logger.warning(
            "LOG_CHAT_ID не задан — логи мониторинга не отправляются. "
            "Задайте в .env или Variables (Railway) или отправьте /start боту в нужном канале."
        )
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
