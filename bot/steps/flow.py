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
            "Привет! 🦭 Я здесь, чтобы спокойно разобраться вместе с тобой.\n\n"
            "Посмотрим на процессы и команду, найдём опоры для решений — по шагам, без спешки. "
            "Результат будет понятным и полезным.\n\n"
            "Нажми «Анализ проблемы», когда будешь готов начать."
        ),
        "2_upload": (
            "Пришли, пожалуйста, то, что уже есть под рукой:\n\n"
            "• графики метрик или схему процесса\n"
            "• заметки по интервью о проблеме\n\n"
            "Можно файлом (фото, PDF, DOC, XLS, TXT) или текстом в чате — я посмотрю и подготовлю анализ."
        ),
        "2_result": "",  # Заполняется LLM
        "2_extra_ask": (
            "Напиши, что именно хочешь уточнить или углубить в аналитике — в свободной форме.\n\n"
            "Я опираюсь на базу знаний (Kanban, OKR, ADKAR, кейсы) и подготовлю ответ спокойно и по делу. "
            "Можно задать вопросы по методологиям, метрикам или управлению изменениями."
        ),
        "2_extra_result": "",  # Заполняется LLM
        "0H_1": "Опиши, пожалуйста, какая помощь тебе нужна, и укажи свой ник в Telegram — с тобой свяжутся.",
        "0H_3": "Твой запрос уже передан. С тобой обязательно свяжутся.\n\nВернуться в диалог или в главное меню?",
    }
    return texts.get(step, "Продолжаем. Я рядом. 🦭")


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
        return "Пока не получилось извлечь данные. Пришли, пожалуйста, текст или файл (TXT, PDF, DOC, XLS) — разберёмся."

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
        "Сейчас анализ через сервис недоступен. Ниже твои данные — ты можешь опираться на них или попробовать позже.\n\n"
        "Данные:\n" + combined[:2000]
    )
    return format_analysis_text(fallback)
