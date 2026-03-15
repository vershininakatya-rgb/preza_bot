"""Обработчики сообщений бота."""
import io
import time
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
from bot.storage.db import (
    upsert_user,
    insert_analysis,
    update_analysis_extra,
    insert_diagram,
    insert_feedback,
)
from bot.utils.monitoring import log_activity
from bot.utils.reply import reply_with_photo


def _duration_sec(state: dict) -> float | None:
    t = state.get("step_entered_at")
    if t is None:
        return None
    return time.time() - t


def _user_full_name(user) -> str:
    """Собрать полное имя из first_name и last_name (Telegram User)."""
    first = (getattr(user, "first_name", None) or "").strip()
    last = (getattr(user, "last_name", None) or "").strip()
    if last:
        return (first + " " + last).strip()
    return first


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений — маршрутизация по шагам."""
    user_id = update.effective_user.id
    user = update.effective_user
    text = (update.message.text or "").strip()

    state = get_state(user_id)
    step = state.get("step", "1")
    duration = _duration_sec(state)

    # «Нужна помощь» — переход в шаг 0H
    if text == "Нужна помощь":
        log_activity(context.bot, user, "текст", step, "0H_1", duration, text[:100] if text else None)
        state["return_after_help"] = step
        state["step"] = "0H_1"
        state["step_entered_at"] = time.time()
        set_state(user_id, state)
        msg = get_step_message("0H_1")
        kb = get_step_keyboard("0H_1")
        await reply_with_photo(update, msg, "0H_1", kb)
        return

    # Шаг 0H_1: пользователь написал, что ему нужна помощь — только в личку админу (ADMIN_CHAT_ID), в чате пользователя не показываем
    if step == "0H_1":
        log_activity(context.bot, user, "текст", step, "0H_3", duration, text[:100] if text else None)
        state["step"] = "0H_3"
        state["step_entered_at"] = time.time()
        set_state(user_id, state)
        msg = get_step_message("0H_3")
        kb = get_step_inline_keyboard("0H_3") or get_step_keyboard("0H_3")
        await reply_with_photo(update, msg, "0H_3", kb)
        user = update.effective_user
        if ADMIN_CHAT_ID:
            try:
                admin_id = int(ADMIN_CHAT_ID)
                admin_msg = (
                    f"🆘 Пользователю нужна помощь\n\n"
                    f"Кто: {user.full_name} (@{user.username or '—'}), id={user_id}\n\n"
                    f"Текст: {text}"
                )
                # Только в личные сообщения админа (chat_id пользователя), не в общий чат
                await context.bot.send_message(chat_id=admin_id, text=admin_msg)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("ADMIN_CHAT_ID invalid or send failed: %s", e)
        # Сохранение обратной связи в БД
        internal_id = await upsert_user(user_id, getattr(user, "username", None), _user_full_name(user))
        if internal_id is not None:
            await insert_feedback(internal_id, state.get("return_after_help"), text or "")
        return

    # «Начать сначала», «В главное меню», «Справка» — сброс в шаг 1
    if text in ("Начать сначала", "В главное меню", "Справка"):
        log_activity(context.bot, user, "текст", step, "1", duration, text[:100] if text else None)
        state["step"] = "1"
        state["scenario"] = None
        state["data"] = {}
        state["analysis_result"] = None
        state["extra_result"] = None
        state["extra_request"] = None
        state["analysis_db_id"] = None
        state["step_entered_at"] = time.time()
        set_state(user_id, state)
        msg = get_step_message("1")
        kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
        await reply_with_photo(update, msg, "1", kb)
        return

    # Обработка ответа по текущему шагу
    next_step, new_state = process_step_answer(step, text, state)
    log_activity(context.bot, user, "текст", step, next_step, duration, text[:100] if text else None)
    new_state["step_entered_at"] = time.time()
    set_state(user_id, new_state)

    # Шаг 2_result: показываем результат анализа (LLM)
    if next_step == "2_result":
        analysis_text = await analyze_problem_with_llm(new_state)
        new_state["analysis_result"] = analysis_text
        set_state(user_id, new_state)
        # Сохранение анализа в БД
        internal_id = await upsert_user(user_id, getattr(user, "username", None), _user_full_name(user))
        if internal_id is not None:
            data_obj = new_state.get("data", {})
            texts = data_obj.get("texts", [])
            files = data_obj.get("file_descriptions", [])
            analysis_db_id = await insert_analysis(
                internal_id, texts, files,
                analysis_result=analysis_text,
            )
            if analysis_db_id is not None:
                new_state["analysis_db_id"] = analysis_db_id
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
            msg = "Сейчас дополнительный анализ через сервис недоступен. Можно попробовать позже или начать сначала — я рядом. 🦭"
        new_state["extra_result"] = msg
        set_state(user_id, new_state)
        analysis_db_id = new_state.get("analysis_db_id")
        if analysis_db_id is not None:
            await update_analysis_extra(analysis_db_id, request or "", msg)
        kb = get_step_inline_keyboard("2_extra_result") or get_step_keyboard("2_extra_result")
        await reply_with_photo(update, msg, "2_extra_result", kb, parse_mode="HTML")
        return

    # Переход в шаг 1 (меню)
    if next_step == "1":
        msg = get_step_message("1")
        kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
        await reply_with_photo(update, msg, "1", kb)
        return

    # Обычный переход на следующий шаг (2_upload, 2_extra_ask и т.д. — step_entered_at уже установлен выше)
    msg = get_step_message(next_step, new_state)
    kb = get_step_keyboard(next_step)
    await reply_with_photo(update, msg or "Продолжаем. Я рядом. 🦭", next_step, kb)


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
    if not getattr(query, "data", None):
        return
    data = query.data
    user_id = update.effective_user.id
    user = update.effective_user
    state = get_state(user_id)
    step = state.get("step", "1")
    duration = _duration_sec(state)

    # «Сделать диаграмму решений» — генерация через Kroki
    if data == CB_STEP2_RESULT_DIAGRAM and step == "2_result":
        log_activity(context.bot, user, "кнопка", step, "2_result", duration, "Сделать диаграмму решений")
        analysis = state.get("analysis_result", "")
        img_bytes, err, mermaid_code = await generate_decision_tree_diagram(analysis)
        message = query.message
        kb = get_step_inline_keyboard("2_result") or get_step_keyboard("2_result")
        # Сохранение диаграммы в БД
        analysis_db_id = state.get("analysis_db_id")
        internal_id = await upsert_user(user_id, getattr(user, "username", None), _user_full_name(user))
        if analysis_db_id is not None and internal_id is not None:
            await insert_diagram(
                analysis_db_id, internal_id,
                mermaid_code=mermaid_code,
                success=bool(img_bytes),
                error_message=err,
            )
        if img_bytes:
            await message.reply_photo(
                photo=io.BytesIO(img_bytes),
                caption="Диаграмма дерева решений",
                reply_markup=kb,
            )
        else:
            await message.reply_text(
                err or "Диаграмму пока не получилось сгенерировать. Можно попробовать позже или опереться на текст анализа. 🦭",
                reply_markup=kb,
            )
        return

    if data not in _CB_TO_TEXT:
        return
    text = _CB_TO_TEXT[data]

    # «Нужна помощь» — переход в шаг 0H
    if text == "Нужна помощь":
        log_activity(context.bot, user, "кнопка", step, "0H_1", duration, text)
        state["return_after_help"] = step
        state["step"] = "0H_1"
        state["step_entered_at"] = time.time()
        set_state(user_id, state)
        msg = get_step_message("0H_1")
        kb = get_step_keyboard("0H_1")  # 0H_1 — текст, без inline
        await reply_with_photo(update, msg, "0H_1", kb)
        return

    # «Начать сначала», «В главное меню» — сброс в шаг 1
    if text in ("Начать сначала", "В главное меню"):
        log_activity(context.bot, user, "кнопка", step, "1", duration, text)
        state["step"] = "1"
        state["scenario"] = None
        state["data"] = {}
        state["analysis_result"] = None
        state["extra_result"] = None
        state["extra_request"] = None
        state["return_after_help"] = None
        state["analysis_db_id"] = None
        state["step_entered_at"] = time.time()
        set_state(user_id, state)
        msg = get_step_message("1")
        kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
        await reply_with_photo(update, msg, "1", kb)
        return

    # 0H_3: Вернуться в диалог / В главное меню
    if step == "0H_3":
        if text == "Вернуться в диалог":
            prev = state.get("return_after_help") or "1"
            log_activity(context.bot, user, "кнопка", step, prev, duration, text)
            state["return_after_help"] = None
            state["step"] = prev
            state["step_entered_at"] = time.time()
            set_state(user_id, state)
            msg = get_step_message(prev)
            kb = get_step_inline_keyboard(prev) or get_step_keyboard(prev)
            await reply_with_photo(update, msg, prev, kb)
        else:
            log_activity(context.bot, user, "кнопка", step, "1", duration, text)
            state["return_after_help"] = None
            state["step"] = "1"
            state["analysis_db_id"] = None
            state["step_entered_at"] = time.time()
            set_state(user_id, state)
            msg = get_step_message("1")
            kb = get_step_inline_keyboard("1") or get_step_keyboard("1")
            await reply_with_photo(update, msg, "1", kb)
        return

    # Обработка через process_step_answer
    next_step, new_state = process_step_answer(step, text, state)
    log_activity(context.bot, user, "кнопка", step, next_step, duration, text)
    new_state["step_entered_at"] = time.time()
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
            msg = "Сейчас дополнительный анализ через сервис недоступен. Можно попробовать позже или начать сначала — я рядом. 🦭"
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
    user = update.effective_user
    state = get_state(user_id)
    step = state.get("step", "1")
    duration = _duration_sec(state)

    if step != "2_upload":
        await reply_with_photo(
            update,
            "Загрузи файлы на шаге «Анализ проблемы».",
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
        await reply_with_photo(update, "Пока не получилось загрузить файл. Попробуй другой формат (TXT, PDF) — справимся. 🦭", "2_upload")
        return

    text = extract_text_from_bytes(data, doc.file_name)
    if text:
        if "data" not in state:
            state["data"] = {"texts": [], "file_descriptions": []}
        state["data"].setdefault("file_descriptions", []).append(
            f"[Файл: {doc.file_name}]\n{text[:8000]}"
        )
        log_activity(context.bot, user, "файл", step, "2_result", duration, f"Файл: {doc.file_name}")
        state["step"] = "2_result"
        state["step_entered_at"] = time.time()
        set_state(user_id, state)
        analysis_text = await analyze_problem_with_llm(state)
        state["analysis_result"] = analysis_text
        set_state(user_id, state)
        internal_id = await upsert_user(user_id, getattr(user, "username", None), _user_full_name(user))
        if internal_id is not None:
            data_obj = state.get("data", {})
            texts = data_obj.get("texts", [])
            files_desc = data_obj.get("file_descriptions", [])
            analysis_db_id = await insert_analysis(internal_id, texts, files_desc, analysis_result=analysis_text)
            if analysis_db_id is not None:
                state["analysis_db_id"] = analysis_db_id
                set_state(user_id, state)
        kb = get_step_inline_keyboard("2_result") or get_step_keyboard("2_result")
        await reply_with_photo(update, analysis_text, "2_result", kb, parse_mode="HTML")
    else:
        await reply_with_photo(
            update,
            "Текст из этого файла пока не извлёкся. Поддерживаются: TXT, MD, PDF, DOC, DOCX, XLS, XLSX — или вставь текст в сообщение. 🦭",
            "2_upload",
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик фото — описание через Vision API и добавление в данные."""
    user_id = update.effective_user.id
    user = update.effective_user
    state = get_state(user_id)
    step = state.get("step", "1")
    duration = _duration_sec(state)

    if step != "2_upload":
        await reply_with_photo(
            update,
            "Фото лучше отправить на шаге «Анализ проблемы» — тогда я смогу его разобрать. 🦭",
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
        await reply_with_photo(update, "Фото пока не загрузилось. Попробуй ещё раз или отправь текст/документ. 🦭", "2_upload")
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
            log_activity(context.bot, user, "фото", step, "2_result", duration, "Фото")
            state["step"] = "2_result"
            state["step_entered_at"] = time.time()
            set_state(user_id, state)
            analysis_text = await analyze_problem_with_llm(state)
            state["analysis_result"] = analysis_text
            set_state(user_id, state)
            internal_id = await upsert_user(user_id, getattr(user, "username", None), _user_full_name(user))
            if internal_id is not None:
                data_obj = state.get("data", {})
                texts = data_obj.get("texts", [])
                files_desc = data_obj.get("file_descriptions", [])
                analysis_db_id = await insert_analysis(internal_id, texts, files_desc, analysis_result=analysis_text)
                if analysis_db_id is not None:
                    state["analysis_db_id"] = analysis_db_id
                    set_state(user_id, state)
            kb = get_step_inline_keyboard("2_result") or get_step_keyboard("2_result")
            await reply_with_photo(update, analysis_text, "2_result", kb, parse_mode="HTML")
        else:
            await reply_with_photo(
                update,
                "Сейчас распознать изображение не получилось. Можно отправить текст или документ — разберёмся. 🦭",
                "2_upload",
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Photo analysis failed: %s", e)
        await reply_with_photo(update, "При обработке фото что-то пошло не так. Попробуй отправить текст или документ — я помогу. 🦭", "2_upload")
