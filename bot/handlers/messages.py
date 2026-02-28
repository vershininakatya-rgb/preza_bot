"""Обработчики сообщений бота."""
import io
from telegram import Update
from telegram.ext import ContextTypes

from bot.config.settings import ADMIN_CHAT_ID
from bot.keyboards import (
    CB_STEP1_ANALYSIS,
    CB_STEP2_RESULT_DIAGRAM,
    CB_STEP2_RESULT_EXTRA,
    CB_STEP2_RESULT_RESTART,
    CB_STEP2_EXTRA_RESTART,
    CB_STEP2_EXTRA_MENU,
    CB_HELP,
    CB_0H3_BACK,
    CB_0H3_MENU,
)
from bot.storage import get_state, set_state
from bot.steps.flow import (
    get_step_message,
    get_step_keyboard,
    get_step_inline_keyboard,
    process_step_answer,
    analyze_problem_with_llm,
)
from bot.services.llm import llm_supplement_analysis
from bot.utils.file_extract import extract_text_from_bytes
from bot.utils.format import format_analysis_text
from bot.services.diagram import generate_decision_tree_diagram
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
        kb = get_step_inline_keyboard("0H_3") or get_step_keyboard("0H_3")
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

    # «Начать сначала», «В главное меню», «Справка» — сброс в шаг 1
    if text in ("Начать сначала", "В главное меню", "Справка"):
        state["step"] = "1"
        state["scenario"] = None
        state["data"] = {}
        state["analysis_result"] = None
        state["extra_result"] = None
        state["extra_request"] = None
        set_state(user_id, state)
        msg = get_step_message("1")
        kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
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
        kb = get_step_inline_keyboard("2_result") or get_step_keyboard("2_result")
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
        new_state["extra_result"] = msg
        set_state(user_id, new_state)
        kb = get_step_inline_keyboard("2_extra_result") or get_step_keyboard("2_extra_result")
        await reply_with_photo(update, msg, "2_extra_result", kb, parse_mode="HTML")
        return

    # Переход в шаг 1 (меню)
    if next_step == "1":
        msg = get_step_message("1")
        kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
        await reply_with_photo(update, msg, "1", kb)
        return

    # Обычный переход на следующий шаг
    msg = get_step_message(next_step, new_state)
    kb = get_step_keyboard(next_step)
    await reply_with_photo(update, msg or "Продолжаем.", next_step, kb)


# Маппинг callback_data -> текст (для переиспользования логики handle_message)
_CB_TO_TEXT = {
    CB_STEP1_ANALYSIS: "Анализ проблемы",
    CB_STEP2_RESULT_EXTRA: "Нужна дополнительная аналитика",
    CB_STEP2_RESULT_RESTART: "Начать сначала",
    CB_STEP2_EXTRA_RESTART: "Начать сначала",
    CB_STEP2_EXTRA_MENU: "В главное меню",
    CB_HELP: "Нужна помощь",
    CB_0H3_BACK: "Вернуться в диалог",
    CB_0H3_MENU: "В главное меню",
}


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий inline-кнопок."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    state = get_state(user_id)
    step = state.get("step", "1")

    # «Сделать диаграмму решений» — генерация через Kroki
    if data == CB_STEP2_RESULT_DIAGRAM and step == "2_result":
        analysis = state.get("analysis_result", "")
        img_bytes, err = await generate_decision_tree_diagram(analysis)
        message = query.message
        kb = get_step_inline_keyboard("2_result") or get_step_keyboard("2_result")
        if img_bytes:
            await message.reply_photo(
                photo=io.BytesIO(img_bytes),
                caption="Диаграмма дерева решений",
                reply_markup=kb,
            )
        else:
            await message.reply_text(
                err or "Не удалось сгенерировать диаграмму.",
                reply_markup=kb,
            )
        return

    if data not in _CB_TO_TEXT:
        return
    text = _CB_TO_TEXT[data]

    # «Нужна помощь» — переход в шаг 0H
    if text == "Нужна помощь":
        state["return_after_help"] = step
        state["step"] = "0H_1"
        set_state(user_id, state)
        msg = get_step_message("0H_1")
        kb = get_step_keyboard("0H_1")  # 0H_1 — текст, без inline
        await reply_with_photo(update, msg, "0H_1", kb)
        return

    # «Начать сначала», «В главное меню» — сброс в шаг 1
    if text in ("Начать сначала", "В главное меню"):
        state["step"] = "1"
        state["scenario"] = None
        state["data"] = {}
        state["analysis_result"] = None
        state["extra_result"] = None
        state["extra_request"] = None
        state["return_after_help"] = None
        set_state(user_id, state)
        msg = get_step_message("1")
        kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
        await reply_with_photo(update, msg, "1", kb)
        return

    # 0H_3: Вернуться в диалог / В главное меню
    if step == "0H_3":
        if text == "Вернуться в диалог":
            prev = state.get("return_after_help") or "1"
            state["return_after_help"] = None
            state["step"] = prev
            set_state(user_id, state)
            msg = get_step_message(prev)
            kb = get_step_inline_keyboard(prev) or get_step_keyboard(prev)
            await reply_with_photo(update, msg, prev, kb)
        else:
            state["return_after_help"] = None
            state["step"] = "1"
            set_state(user_id, state)
            msg = get_step_message("1")
            kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
            await reply_with_photo(update, msg, "1", kb)
        return

    # Обработка через process_step_answer
    next_step, new_state = process_step_answer(step, text, state)
    set_state(user_id, new_state)

    if next_step == "2_result":
        analysis_text = await analyze_problem_with_llm(new_state)
        new_state["analysis_result"] = analysis_text
        set_state(user_id, new_state)
        kb = get_step_inline_keyboard("2_result") or get_step_keyboard("2_result")
        await reply_with_photo(update, analysis_text, "2_result", kb, parse_mode="HTML")
        return

    if next_step == "2_extra_result":
        data_obj = new_state.get("data", {})
        texts = data_obj.get("texts", [])
        files = data_obj.get("file_descriptions", [])
        data_text = "\n\n---\n\n".join(texts + files)
        original = new_state.get("analysis_result", "")
        request = new_state.get("extra_request", "")
        supplement = await llm_supplement_analysis(data_text, original, request)
        if supplement:
            msg = format_analysis_text(f"**Дополнительная аналитика**\n\n{supplement}")
        else:
            msg = "Не удалось выполнить дополнительный анализ (проверьте OPENAI_API_KEY)."
        new_state["extra_result"] = msg
        set_state(user_id, new_state)
        kb = get_step_inline_keyboard("2_extra_result") or get_step_keyboard("2_extra_result")
        await reply_with_photo(update, msg, "2_extra_result", kb, parse_mode="HTML")
        return

    if next_step == "1":
        msg = get_step_message("1")
        kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
        await reply_with_photo(update, msg, "1", kb)
        return

    if next_step == "2_upload":
        msg = get_step_message("2_upload")
        kb = get_step_keyboard("2_upload")
        await reply_with_photo(update, msg, "2_upload", kb)
        return

    if next_step == "2_extra_ask":
        msg = get_step_message("2_extra_ask")
        kb = get_step_keyboard("2_extra_ask")
        await reply_with_photo(update, msg, "2_extra_ask", kb)
        return


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
        kb = get_step_inline_keyboard("2_result") or get_step_keyboard("2_result")
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
            kb = get_step_inline_keyboard("2_result") or get_step_keyboard("2_result")
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
