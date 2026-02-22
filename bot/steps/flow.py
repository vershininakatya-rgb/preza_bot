"""Определение шагов, текстов и переходов."""
from typing import Optional
from telegram import ReplyKeyboardMarkup
from bot.keyboards import (
    keyboard_step1,
    keyboard_simple,
    keyboard_choice,
    keyboard_two,
    keyboard_help_only,
)

def get_step_message(step: str, state: Optional[dict] = None) -> str:
    """Текст сообщения для шага."""
    # Динамическое сообщение для шага 2_5 при множественном выборе ролей
    if step == "2_5" and state:
        hint = state.get("_hint_2_5")
        if hint:
            return hint
        roles = state.get("onboarding", {}).get("interview_roles")
        if isinstance(roles, list) and roles:
            return f"Выбрано: {', '.join(roles)}.\nВыберите ещё или нажмите «Готово»."

    texts = {
        "1": (
            "Привет! 👋 Я бот. Я помогаю проанализировать проблемы в процессах "
            "и подготовить презентацию для руководителей.\n\n"
            "С помощью меня ты сможешь:\n"
            "• подготовить интервью для аналитики\n"
            "• проанализировать метрики\n"
            "• получить дерево решений\n"
            "• выявить повторяющиеся паттерны\n"
            "• получить рекомендации по решению проблем\n\n"
            'Нажми кнопку «Помощь с аналитикой», чтобы начать.'
        ),
        "2_1": "Кто вы по роли?",
        "2_2": "Для кого готовите презентацию?",
        "2_3": "Какая у вас проблема?",
        "2_3_other": "Опишите проблему своими словами:",
        "2_5": "С кем будет проводиться интервью? (роли: C-level, руководитель, тимлид, команда, аналитики)",
        "2_6": "Нужно ли составить отдельные вопросы для каждой роли?",
        "2_7": (
            "Что именно хотите выяснить / какую проблему разобрать? "
            "И какой итоговый результат нужен?"
        ),
        "3_1": "В какой области проблема?",
        "3_2": "Кто спонсор / кто попросил разобраться?",
        "3_3": "Какие основные боли/симптомы уже озвучены?",
        "5_1": (
            "Загрузите или вставьте данные: скрины дашбордов, выгрузки, описание метрик. "
            "Или просто опишите текстом."
        ),
        "5_2": "Какие метрики ключевые? (lead time, cycle time, WIP, блокировки, конверсия)",
        "5_3": "Текущие значения и тренды? Есть ли аномалии?",
        "5_4": "С кем уже проводились интервью? Ключевые ответы и цитаты?",
        "5_5": "Дополнительные разрезы (по командам, статусам, блокировкам)? «Уже посмотрел» / «Добавлю позже»",
        "6_1": "",  # Заполняется build_analytics_tree
        "0H_1": "Опишите, какая вам нужна помощь (в свободной форме).",
        "0H_3": "Ваш запрос передан. С вами свяжутся.\n\nВернуться в диалог или в главное меню?",
    }
    return texts.get(step, "Продолжаем.")


def get_step_keyboard(step: str) -> Optional[ReplyKeyboardMarkup]:
    """Клавиатура для шага."""
    if step == "1":
        return keyboard_step1()
    if step == "2_1":
        return keyboard_simple([
            "Деливери-менеджер", "Скрам-мастер", "Change-менеджер",
            "Team Lead / руководитель команды", "Product Manager",
            "Агент изменений", "Другое",
        ])
    if step == "2_2":
        return keyboard_simple([
            "C-level", "Команда", "Миддл-менеджмент", "Смешанная аудитория",
        ])
    if step == "2_3":
        return keyboard_simple([
            "Долго разрабатываем",
            "Много задач в работе",
            "Задержки при задачах на несколько команд",
            "Проблемы с приоритизацией",
            "Не работает Discovery",
            "Другое",
        ])
    if step == "2_3_other":
        return keyboard_help_only()
    if step == "2_5":
        return keyboard_choice([
            ["C-level", "Руководитель", "Тимлид"],
            ["Команда", "Аналитики", "Стейкхолдеры"],
            ["Готово"],
        ])
    if step == "2_6":
        return keyboard_two("Да", "Нет")
    if step == "3_1":
        return keyboard_simple([
            "Процессы", "Delivery", "Discovery", "Эксперименты/пилоты",
            "Оргструктура", "Качество", "Сроки", "Другое",
        ])
    if step == "5_5":
        return keyboard_two("Уже посмотрел", "Добавлю позже")
    if step == "6_1":
        return keyboard_two("Начать сначала", "В главное меню")
    if step == "0H_3":
        return keyboard_two("Вернуться в диалог", "В главное меню")
    # Шаги с вводом текста — только «Нужна помощь»
    if step in ("3_2", "3_3", "5_1", "5_2", "5_3", "5_4", "2_7", "2_3_other", "0H_1"):
        return keyboard_help_only()
    return keyboard_help_only()


def process_step_answer(step: str, text: str, state: dict) -> tuple[str, dict]:
    """
    Обработать ответ пользователя. Возвращает (next_step, updated_state).
    """
    state = state.copy()

    # Навигация: Начать сначала / В главное меню
    if text in ("Начать сначала", "В главное меню"):
        state["step"] = "1"
        state["scenario"] = None
        state["onboarding"] = {}
        state["context"] = {}
        state["data"] = {}
        state["return_after_help"] = None
        return "1", state

    # Вернуться в диалог после «Нужна помощь»
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
        if text == "Помощь с аналитикой":
            state["scenario"] = text
            state["step"] = "2_1"
            return "2_1", state

    def _next(s: str):
        state["step"] = s
        return s, state

    if step == "2_1":
        state["onboarding"]["role"] = text
        return _next("2_2")
    if step == "2_2":
        state["onboarding"]["audience"] = text
        return _next("2_3")
    if step == "2_3":
        if text == "Другое":
            return _next("2_3_other")
        state["onboarding"]["problem"] = text
        return _next("2_5")
    if step == "2_3_other":
        state["onboarding"]["problem"] = text
        return _next("2_5")
    if step == "2_5":
        ROLES_2_5 = {"C-level", "Руководитель", "Тимлид", "Команда", "Аналитики", "Стейкхолдеры"}
        if text == "Готово":
            roles = state["onboarding"].get("interview_roles")
            if isinstance(roles, list) and roles:
                state["onboarding"]["interview_roles"] = ", ".join(roles)
                if "_hint_2_5" in state:
                    del state["_hint_2_5"]
                return _next("2_6")
            state["_hint_2_5"] = "Выберите хотя бы одну роль и нажмите «Готово»."
            return "2_5", state
        if text in ROLES_2_5:
            roles = state["onboarding"].get("interview_roles")
            if not isinstance(roles, list):
                roles = []
            if text not in roles:
                roles = roles + [text]
            state["onboarding"]["interview_roles"] = roles
            if "_hint_2_5" in state:
                del state["_hint_2_5"]
            return "2_5", state
        # Неизвестный ввод — остаёмся на шаге
        return "2_5", state
    if step == "2_6":
        state["onboarding"]["questions_per_role"] = text
        return _next("2_7")
    if step == "2_7":
        state["onboarding"]["problem_and_result"] = text
        return _next("3_1")  # Единственный сценарий — анализ

    if step == "3_1":
        state["context"]["area"] = text
        return _next("3_2")
    if step == "3_2":
        state["context"]["sponsor"] = text
        return _next("3_3")
    if step == "3_3":
        state["context"]["pains"] = text
        return _next("5_1")

    if step == "5_1":
        state["data"]["uploads"] = text
        return _next("5_2")
    if step == "5_2":
        state["data"]["metrics"] = text
        return _next("5_3")
    if step == "5_3":
        state["data"]["trends"] = text
        return _next("5_4")
    if step == "5_4":
        state["data"]["interviews"] = text
        return _next("5_5")
    if step == "5_5":
        state["data"]["extra"] = text
        return _next("6_1")

    # Шаг 6_1: любое нажатие ведёт в меню (уже показали дерево)
    if step == "6_1":
        return _next("1")

    return step, state


def _format_state_for_llm(state: dict) -> str:
    """Форматирование данных сессии для промпта LLM."""
    o = state.get("onboarding", {})
    c = state.get("context", {})
    d = state.get("data", {})
    return f"""
Роль: {o.get('role', '—')}
Аудитория: {o.get('audience', '—')}
Проблема: {o.get('problem', '—')}
Цель встречи: {o.get('meeting_goal', '—')}
Роли для интервью: {o.get('interview_roles', '—')}
Проблема и желаемый результат: {o.get('problem_and_result', '—')}

Область проблемы: {c.get('area', '—')}
Спонсор: {c.get('sponsor', '—')}
Боли/симптомы: {c.get('pains', '—')}

Данные и метрики: {d.get('uploads', '—')} {d.get('metrics', '—')}
Тренды и аномалии: {d.get('trends', '—')}
Интервью и цитаты: {d.get('interviews', '—')}
Дополнительно: {d.get('extra', '—')}
""".strip()


def build_analytics_tree(state: dict) -> str:
    """Сформировать дерево анализа и паттерны из собранных данных (без LLM)."""
    o = state.get("onboarding", {})
    c = state.get("context", {})
    d = state.get("data", {})

    lines = [
        "📊 Дерево анализа",
        "",
        "Роль и контекст:",
        f"• Роль: {o.get('role', '—')}",
        f"• Аудитория: {o.get('audience', '—')}",
        f"• Проблема: {o.get('problem', '—')}",
        f"• Цель встречи: {o.get('meeting_goal', '—')}",
        f"• Проблема и результат: {o.get('problem_and_result', '—')}",
        "",
        "Область проблемы:",
        f"• Область: {c.get('area', '—')}",
        f"• Спонсор: {c.get('sponsor', '—')}",
        f"• Боли/симптомы: {c.get('pains', '—')}",
        "",
        "Данные:",
        f"• Метрики: {d.get('metrics', '—')}",
        f"• Тренды и аномалии: {d.get('trends', '—')}",
        f"• Интервью: {d.get('interviews', '—')}",
        "",
        "Непокрытые зоны:",
        "• Роли без интервью — проверьте, все ли стейкхолдеры опрошены",
        "• Метрики без данных — укажите, где есть пробелы",
        "",
        "Паттерны (для уточнения):",
        "• Сопоставьте слова стейкхолдеров с метриками — есть ли противоречия?",
        "• Повторяющиеся темы в интервью?",
        "",
        "Дальше: решения, план, риски → сторителлинг → презентация.",
    ]
    return "\n".join(lines)


async def build_analytics_tree_with_llm(state: dict) -> str:
    """
    Сформировать дерево анализа с помощью OpenAI.
    При отсутствии ключа или ошибке API — fallback на build_analytics_tree.
    """
    try:
        from bot.services.llm import llm_generate

        data = _format_state_for_llm(state)
        system = (
            "Ты — эксперт по аналитике для C-level презентаций. "
            "На основе данных пользователя сформируй структурированное «дерево анализа»: "
            "роль и контекст, область проблемы, данные, непокрытые зоны, паттерны и противоречия. "
            "Пиши кратко, по пунктам. Язык — русский. В конце добавь: «Дальше: решения, план, риски → сторителлинг → презентация.»"
        )
        prompt = f"Сформируй дерево анализа на основе этих данных:\n\n{data}"
        result = await llm_generate(prompt, system_prompt=system, max_tokens=1500)
        if result:
            return "📊 Дерево анализа\n\n" + result
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("LLM analytics tree failed: %s", e)
    return build_analytics_tree(state)
