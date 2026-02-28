"""Обработчики сообщений бота."""
import io
from telegram import Update
from telegram.ext import ContextTypes

from bot.config.settings import ADMIN_CHAT_ID
from bot.storage import get_state, set_state
from bot.steps.flow import (
    get_step_message,
    get_step_keyboard,
    process_step_answer,
    analyze_problem_with_llm,
)
from bot.services.llm import llm_supplement_analysis
from bot.utils.file_extract import extract_text_from_bytes
from bot.utils.format import format_analysis_text
from bot.utils.reply import reply_with_photo


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
        await reply_with_photo(update, msg, "0H_1", kb)
        return

    # Шаг 0H_1: пользователь описал проблему — уведомление админу и переход в 0H_3
    if step == "0H_1":
        state["step"] = "0H_3"
        set_state(user_id, state)
        msg = get_step_message("0H_3")
        kb = get_step_keyboard("0H_3")
        await reply_with_photo(update, msg, "0H_3", kb)
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
            except Exception:
                pass
        return

    # Шаг 2_result: устаревшая кнопка «Сделать диаграмму решений» — отправить обновлённую клавиатуру
    if step == "2_result" and text == "Сделать диаграмму решений":
        kb = get_step_keyboard("2_result")
        await reply_with_photo(
            update,
            "Генерация диаграммы временно отключена. Выберите другую опцию.",
            "2_result",
            kb,
        )
        return

    # «Начать сначала», «В главное меню», «Справка» — сброс в шаг 1
    if text in ("Начать сначала", "В главное меню", "Справка"):
        state["step"] = "1"
        state["scenario"] = None
        state["data"] = {}
        state["analysis_result"] = None
        state["extra_request"] = None
        set_state(user_id, state)
        msg = get_step_message("1")
        kb = get_step_keyboard("1")
        await reply_with_photo(update, msg, "1", kb)
        return

    # Обработка ответа по текущему шагу
    next_step, new_state = process_step_answer(step, text, state)
    set_state(user_id, new_state)

    # Шаг 2_result: показываем результат анализа (LLM)
    if next_step == "2_result":
        analysis_text = await analyze_problem_with_llm(new_state)
        new_state["analysis_result"] = analysis_text
        set_state(user_id, new_state)
        kb = get_step_keyboard("2_result")
        await reply_with_photo(update, analysis_text, "2_result", kb, parse_mode="HTML")
        return

    # Шаг 2_extra_result: дополнительная аналитика по запросу пользователя
    if next_step == "2_extra_result":
        data = new_state.get("data", {})
        texts = data.get("texts", [])
        files = data.get("file_descriptions", [])
        data_text = "\n\n---\n\n".join(texts + files)
        original = new_state.get("analysis_result", "")
        request = new_state.get("extra_request", "")
        supplement = await llm_supplement_analysis(data_text, original, request)
        if supplement:
            msg = format_analysis_text(f"**Дополнительная аналитика**\n\n{supplement}")
        else:
            msg = "Не удалось выполнить дополнительный анализ (проверьте OPENAI_API_KEY)."
        kb = get_step_keyboard("2_extra_result")
        await reply_with_photo(update, msg, "2_extra_result", kb, parse_mode="HTML")
        return

    # Переход в шаг 1 (меню)
    if next_step == "1":
        msg = get_step_message("1")
        kb = get_step_keyboard("1")
        await reply_with_photo(update, msg, "1", kb)
        return

    # Обычный переход на следующий шаг
    msg = get_step_message(next_step, new_state)
    kb = get_step_keyboard(next_step)
    await reply_with_photo(update, msg or "Продолжаем.", next_step, kb)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик документов — извлечение текста и добавление в данные."""
    user_id = update.effective_user.id
    state = get_state(user_id)
    step = state.get("step", "1")

    if step != "2_upload":
        await reply_with_photo(
            update,
            "Загрузите файлы на шаге «Анализ проблемы».",
            "2_upload",
        )
        return

    doc = update.message.document
    if not doc or not doc.file_id:
        return

    try:
        file = await context.bot.get_file(doc.file_id)
        buf = io.BytesIO()
        await file.download_to_memory(buf)
        buf.seek(0)
        data = buf.read()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to download document: %s", e)
        await reply_with_photo(update, "Не удалось загрузить файл. Попробуйте другой формат (TXT, PDF).", "2_upload")
        return

    text = extract_text_from_bytes(data, doc.file_name)
    if text:
        if "data" not in state:
            state["data"] = {"texts": [], "file_descriptions": []}
        state["data"].setdefault("file_descriptions", []).append(
            f"[Файл: {doc.file_name}]\n{text[:8000]}"
        )
        state["step"] = "2_result"
        set_state(user_id, state)
        analysis_text = await analyze_problem_with_llm(state)
        state["analysis_result"] = analysis_text
        set_state(user_id, state)
        kb = get_step_keyboard("2_result")
        await reply_with_photo(update, analysis_text, "2_result", kb, parse_mode="HTML")
    else:
        await reply_with_photo(
            update,
            "Не удалось извлечь текст из файла. Поддерживаются: TXT, MD, PDF, DOC, DOCX, XLS, XLSX. "
            "Или вставьте текст в сообщение.",
            "2_upload",
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик фото — описание через Vision API и добавление в данные."""
    user_id = update.effective_user.id
    state = get_state(user_id)
    step = state.get("step", "1")

    if step != "2_upload":
        await reply_with_photo(
            update,
            "Загрузите фото на шаге «Анализ проблемы».",
            "2_upload",
        )
        return

    photo = update.message.photo[-1] if update.message.photo else None
    if not photo or not photo.file_id:
        return

    try:
        file = await context.bot.get_file(photo.file_id)
        buf = io.BytesIO()
        await file.download_to_memory(buf)
        buf.seek(0)
        data = buf.read()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to download photo: %s", e)
        await reply_with_photo(update, "Не удалось загрузить фото.", "2_upload")
        return

    try:
        from bot.services.llm import llm_describe_image

        description = await llm_describe_image(bytes(data))
        if description:
            if "data" not in state:
                state["data"] = {"texts": [], "file_descriptions": []}
            state["data"].setdefault("file_descriptions", []).append(
                f"[Описание схемы/диаграммы]\n{description}"
            )
            state["step"] = "2_result"
            set_state(user_id, state)
            analysis_text = await analyze_problem_with_llm(state)
            state["analysis_result"] = analysis_text
            set_state(user_id, state)
            kb = get_step_keyboard("2_result")
            await reply_with_photo(update, analysis_text, "2_result", kb, parse_mode="HTML")
        else:
            await reply_with_photo(
                update,
                "Не удалось распознать изображение (проверьте OPENAI_API_KEY). "
                "Попробуйте отправить текст или документ.",
                "2_upload",
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Photo analysis failed: %s", e)
        await reply_with_photo(update, "Ошибка при обработке фото. Попробуйте текст или документ.", "2_upload")
