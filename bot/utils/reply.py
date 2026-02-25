"""Вспомогательные функции для отправки сообщений с изображениями."""
from telegram import Update

from bot.utils.images import get_step_image_path


async def reply_with_photo(update: Update, msg: str, step: str, kb=None, parse_mode: str = "Markdown"):
    """Отправить сообщение с фото (если есть) и клавиатурой."""
    photo_path = get_step_image_path(step)
    if photo_path and len(msg) <= 1024:
        with open(photo_path, "rb") as f:
            await update.message.reply_photo(photo=f, caption=msg, reply_markup=kb, parse_mode=parse_mode)
    elif photo_path:
        with open(photo_path, "rb") as f:
            await update.message.reply_photo(photo=f)
        await update.message.reply_text(msg, reply_markup=kb, parse_mode=parse_mode)
    else:
        await update.message.reply_text(msg, reply_markup=kb, parse_mode=parse_mode)
