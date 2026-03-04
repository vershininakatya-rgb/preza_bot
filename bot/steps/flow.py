"""Определение шагов, текстов и переходов. Сценарий: Анализ проблемы."""
from typing import Optional
from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup
from bot.keyboards import (
    keyboard_help_only,
    keyboard_step1,
    keyboard_two,
    keyboard_choice,
    inline_step1,
    inline_step2_result,
    inline_step2_extra_result,
    inline_step0H_3,
)


def get_step_message(step: str, state: Optional[dict] = None) -> str:
    """Текст сообщения для шага."""
    if step == "2_upload" and state:
        if state.get("_hint_2_upload"):
            return state["_hint_2_upload"]
    texts = {
        "1": (
            "Привет! 👋 Я бот для анализа проблем в процессах и командах.\n\n"
            "Я помогу:\n"
            "• разобрать схему процесса и результаты интервью\n"
            "• выявить проблемы с командой\n"
            "• предложить варианты решений\n\n"
            'Нажми «Анализ проблемы», чтобы начать.'
        ),
        "2_upload": (
            "Загрузите данные для анализа:\n\n"
            "• Графики производственных метрик\n"
            "• Схему процесса\n"
            "• Результаты интервью о проблеме\n\n"
            "Отправьте файл (фото, PDF, DOC, DOCX, XLS, XLSX, TXT) или напишите текст — анализ запустится сразу."
        ),
        "2_result": "",  # Заполняется LLM
        "2_extra_ask": (
            "Что именно вы хотите получить в дополнительной аналитике? Опишите в свободной форме.\n\n"
            "Ответы формируются с учётом материалов из базы знаний (Kanban, OKR, ADKAR, кейсы). "
            "Можно задать вопросы по методологиям, метрикам, управлению изменениями."
        ),
        "2_extra_result": "",  # Заполняется LLM
        "0H_1": "Опишите в свободной форме какая требуется помощь и укажите свой ник в телеграм.",
        "0H_3": "Ваш запрос передан. С вами свяжутся.\n\nВернуться в диалог или в главное меню?",
    }
    return texts.get(step, "Продолжаем.")


def get_step_keyboard(step: str) -> Optional[ReplyKeyboardMarkup]:
    """Клавиатура для шага."""
    if step == "1":
        return keyboard_step1()
    if step == "2_upload":
        return keyboard_help_only()
    if step == "2_result":
        return keyboard_choice([
            ["Нужна дополнительная аналитика"],
            ["Начать сначала"],
        ])
    if step == "2_extra_ask":
        return keyboard_help_only()
    if step == "2_extra_result":
        return keyboard_two("Начать сначала", "В главное меню")
    if step == "0H_1":
        return None  # без клавиатуры — только поле ввода и кнопка «Отправить»
    if step == "0H_3":
        return keyboard_two("Вернуться в диалог", "В главное меню")
    return keyboard_help_only()


def get_step_inline_keyboard(step: str) -> Optional[InlineKeyboardMarkup]:
    """Inline-клавиатура для шага (для сообщений с кнопками под текстом)."""
    if step == "1":
        return inline_step1()
    if step == "2_result":
        return inline_step2_result()
    if step == "2_extra_result":
        return inline_step2_extra_result()
    if step == "0H_3":
        return inline_step0H_3()
    return None


def process_step_answer(step: str, text: str, state: dict) -> tuple[str, dict]:
    """
    Обработать ответ пользователя. Возвращает (next_step, updated_state).
    """
    state = state.copy()

    # Навигация
    if text in ("Начать сначала", "В главное меню"):
        state["step"] = "1"
        state["scenario"] = None
        state["data"] = {}
        state["analysis_result"] = None
        state["extra_result"] = None
        state["extra_request"] = None
        state["return_after_help"] = None
        return "1", state

    if step == "0H_3" and text == "Вернуться в диалог":
        prev = state.get("return_after_help") or "1"
        state["return_after_help"] = None
        state["step"] = prev
        return prev, state
    if step == "0H_3" and text == "В главное меню":
        state["return_after_help"] = None
        state["step"] = "1"
        return "1", state

    if step == "1":
        if text == "Анализ проблемы":
            state["scenario"] = text
            state["step"] = "2_upload"
            state["data"] = {"texts": [], "file_descriptions": []}
            return "2_upload", state

    if step == "2_upload":
        if text and text != "Нужна помощь":
            if "data" not in state:
                state["data"] = {"texts": [], "file_descriptions": []}
            state["data"].setdefault("texts", []).append(text)
            if "_hint_2_upload" in state:
                del state["_hint_2_upload"]
            state["step"] = "2_result"
            return "2_result", state

    if step == "2_result":
        if text == "Нужна дополнительная аналитика":
            state["step"] = "2_extra_ask"
            return "2_extra_ask", state

    if step == "2_extra_ask":
        if text and text != "Нужна помощь":
            state["extra_request"] = text
            state["step"] = "2_extra_result"
            return "2_extra_result", state

    return step, state


async def analyze_problem_with_llm(state: dict) -> str:
    """
    Анализ данных с помощью OpenAI: проблемы с командой и варианты решений.
    """
    data = state.get("data", {})
    texts = data.get("texts", [])
    file_descriptions = data.get("file_descriptions", [])
    combined = "\n\n---\n\n".join(texts + file_descriptions)

    if not combined.strip():
        return "Не удалось извлечь данные для анализа. Загрузите текст или поддерживаемые файлы."

    try:
        from bot.services.llm import llm_analyze_problem
        from bot.utils.format import format_analysis_text

        result = await llm_analyze_problem(combined)
        if result:
            raw = "**Анализ проблемы**\n\n" + result
            return format_analysis_text(raw)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("LLM analysis failed: %s", e)

    from bot.utils.format import format_analysis_text
    fallback = (
        "Не удалось выполнить анализ (проверьте настройку OPENAI_API_KEY).\n\n"
        "Данные для ручного анализа:\n" + combined[:2000]
    )
    return format_analysis_text(fallback)
