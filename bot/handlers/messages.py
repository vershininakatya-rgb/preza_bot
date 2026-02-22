"""Обработчики сообщений бота."""
from telegram import Update
from telegram.ext import ContextTypes

from bot.config.settings import ADMIN_CHAT_ID
from bot.storage import get_state, set_state
from bot.steps.flow import (
    get_step_message,
    get_step_keyboard,
    process_step_answer,
    build_analytics_tree,
)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений — маршрутизация по шагам."""
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    state = get_state(user_id)
    step = state.get("step", "1")

    # «Нужна помощь» — переход в шаг 0H
    if text == "Нужна помощь":
        state["return_after_help"] = step
        state["step"] = "0H_1"
        set_state(user_id, state)
        msg = get_step_message("0H_1")
        kb = get_step_keyboard("0H_1")
        await update.message.reply_text(msg, reply_markup=kb)
        return

    # Шаг 0H_1: пользователь описал проблему — уведомление админу и переход в 0H_3
    if step == "0H_1":
        state["step"] = "0H_3"
        set_state(user_id, state)
        await update.message.reply_text(get_step_message("0H_3"))
        kb = get_step_keyboard("0H_3")
        await update.message.reply_text("Выберите:", reply_markup=kb)
        if ADMIN_CHAT_ID:
            try:
                admin_id = int(ADMIN_CHAT_ID)
                user = update.effective_user
                admin_msg = (
                    f"🆘 Пользователю нужна помощь\n\n"
                    f"User: {user.full_name} (@{user.username or '—'}), id={user_id}\n\n"
                    f"Текст: {text}"
                )
                await context.bot.send_message(chat_id=admin_id, text=admin_msg)
            except (ValueError, Exception):
                pass
        return

    # Шаг 0H_3 — обрабатывается в process_step_answer (Вернуться / В меню)

    # «Начать сначала», «Справка» — сброс в шаг 1
    if text in ("Начать сначала", "Справка"):
        state["step"] = "1"
        state["scenario"] = None
        state["onboarding"] = {}
        state["context"] = {}
        state["data"] = {}
        set_state(user_id, state)
        msg = get_step_message("1")
        kb = get_step_keyboard("1")
        await update.message.reply_text(msg, reply_markup=kb)
        return

    # Обработка ответа по текущему шагу
    next_step, new_state = process_step_answer(step, text, state)
    set_state(user_id, new_state)

    # Шаг 6_1: показываем дерево анализа
    if next_step == "6_1":
        tree_text = build_analytics_tree(new_state)
        kb = get_step_keyboard("6_1")
        await update.message.reply_text(tree_text, reply_markup=kb)
        return

    # Переход в шаг 1 (меню) — уже обработан в process_step_answer
    if next_step == "1":
        msg = get_step_message("1")
        kb = get_step_keyboard("1")
        await update.message.reply_text(msg, reply_markup=kb)
        return

    # Обычный переход на следующий шаг
    msg = get_step_message(next_step)
    kb = get_step_keyboard(next_step)
    if msg:
        await update.message.reply_text(msg, reply_markup=kb)
    else:
        await update.message.reply_text("Продолжаем.", reply_markup=kb)
