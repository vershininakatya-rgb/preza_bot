"""Вспомогательные функции для отправки сообщений с изображениями."""
from telegram import Update

from bot.utils.images import get_step_image_path


def _get_message(update: Update):
    """Получить сообщение из Update (MessageHandler или CallbackQueryHandler)."""
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


async def reply_with_photo(update: Update, msg: str, step: str, kb=None, parse_mode: str = "Markdown"):
    """Отправить сообщение с фото (если есть) и клавиатурой. Работает с Message и CallbackQuery."""
    message = _get_message(update)
    if not message:
        return
    # На шагах с результатами анализа картинку не показываем
    photo_path = None if step in ("2_result", "2_extra_result") else get_step_image_path(step)
    if photo_path and msg and len(msg) <= 1024:
        with open(photo_path, "rb") as f:
            await message.reply_photo(photo=f, caption=msg, reply_markup=kb, parse_mode=parse_mode)
    elif photo_path and msg:
        with open(photo_path, "rb") as f:
            await message.reply_photo(photo=f)
        await message.reply_text(msg, reply_markup=kb, parse_mode=parse_mode)
    elif photo_path:
        with open(photo_path, "rb") as f:
            await message.reply_photo(photo=f, reply_markup=kb)
    else:
        await message.reply_text(msg or "Продолжаем.", reply_markup=kb, parse_mode=parse_mode)
