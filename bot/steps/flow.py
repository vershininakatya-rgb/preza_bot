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

# Сценарии, ведущие к аналитике (контекст + данные + дерево)
ANALYTICS_SCENARIOS = {"Помощь с аналитикой", "Полный цикл"}


def get_step_message(step: str) -> str:
    """Текст сообщения для шага."""
    texts = {
        "1": (
            "Привет! 👋 Я помогаю готовить презентации для C-level: "
            "от анализа проблемы до готовой презентации в вашем шаблоне.\n\n"
            "С чем помочь?"
        ),
        "2_1": "Кто вы по роли?",
        "2_2": "Для кого готовите презентацию?",
        "2_3": "Какой тип задачи?",
        "2_4": "Какова цель встречи?",
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
            "Агент изменений", "Другое",
        ])
    if step == "2_2":
        return keyboard_simple([
            "C-level", "Директора направлений", "Миддл-менеджмент", "Смешанная аудитория",
        ])
    if step == "2_3":
        return keyboard_simple([
            "Полный цикл (анализ + презентация)",
            "Анализ уже есть, нужна только презентация",
            "Быстрая проверка анализа и истории",
        ])
    if step == "2_4":
        return keyboard_choice([
            ["Одобрение решения", "Старт пилота", "Масштабирование"],
            ["Защита результатов", "Разбор проблемной команды", "Подготовка к стратегсессии"],
        ])
    if step == "2_5":
        return keyboard_choice([
            ["C-level", "Руководитель", "Тимлид"],
            ["Команда", "Аналитики", "Стейкхолдеры"],
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
    if step in ("3_2", "3_3", "5_1", "5_2", "5_3", "5_4", "2_7", "0H_1"):
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
        scenarios = {"Помощь с аналитикой", "Вопросы для интервью", "Подготовить презентацию", "Полный цикл"}
        if text in scenarios:
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
        state["onboarding"]["task_type"] = text
        return _next("2_4")
    if step == "2_4":
        state["onboarding"]["meeting_goal"] = text
        return _next("2_5")
    if step == "2_5":
        state["onboarding"]["interview_roles"] = text
        return _next("2_6")
    if step == "2_6":
        state["onboarding"]["questions_per_role"] = text
        return _next("2_7")
    if step == "2_7":
        state["onboarding"]["problem_and_result"] = text
        if state["scenario"] in ANALYTICS_SCENARIOS:
            return _next("3_1")
        return _next("5_1")  # Вопросы/Презентация — упрощённо к данным

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


def build_analytics_tree(state: dict) -> str:
    """Сформировать дерево анализа и паттерны из собранных данных."""
    o = state.get("onboarding", {})
    c = state.get("context", {})
    d = state.get("data", {})

    lines = [
        "📊 Дерево анализа",
        "",
        "Роль и контекст:",
        f"• Роль: {o.get('role', '—')}",
        f"• Аудитория: {o.get('audience', '—')}",
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
