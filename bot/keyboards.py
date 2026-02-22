"""Клавиатуры бота."""
from telegram import ReplyKeyboardMarkup, KeyboardButton

# Кнопки сценариев (Шаг 1)
SCENARIO_BUTTONS = [
    [KeyboardButton("Помощь с аналитикой"), KeyboardButton("Вопросы для интервью")],
    [KeyboardButton("Подготовить презентацию"), KeyboardButton("Полный цикл")],
]

# Кнопка «Нужна помощь» (добавляется к клавиатурам)
HELP_BUTTON = [[KeyboardButton("Нужна помощь")]]


def keyboard_step1() -> ReplyKeyboardMarkup:
    """Шаг 1: выбор сценария."""
    return ReplyKeyboardMarkup(
        SCENARIO_BUTTONS + HELP_BUTTON,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def keyboard_choice(buttons: list[list[str]], add_help: bool = True) -> ReplyKeyboardMarkup:
    """Клавиатура с кнопками выбора. buttons = [[row1_btn1, row1_btn2], [row2_btn1]]"""
    kb = [[KeyboardButton(b) for b in row] for row in buttons]
    if add_help:
        kb += HELP_BUTTON
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)


def keyboard_simple(buttons: list[str], add_help: bool = True) -> ReplyKeyboardMarkup:
    """Простая клавиатура: список кнопок по одной в ряд."""
    kb = [[KeyboardButton(b)] for b in buttons]
    if add_help:
        kb += HELP_BUTTON
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)


def keyboard_two(btn1: str, btn2: str, add_help: bool = True) -> ReplyKeyboardMarkup:
    """Две кнопки в ряд."""
    kb = [[KeyboardButton(btn1), KeyboardButton(btn2)]]
    if add_help:
        kb += HELP_BUTTON
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)


def keyboard_help_only() -> ReplyKeyboardMarkup:
    """Только кнопка «Нужна помощь» (для шагов с вводом текста)."""
    return ReplyKeyboardMarkup(HELP_BUTTON, resize_keyboard=True, one_time_keyboard=False)
