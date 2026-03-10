"""Клавиатуры бота."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# === Callback data keys для inline-меню (до 64 байт) ===
CB_STEP1_ANALYSIS = "s1:analysis"
CB_STEP2_RESULT_EXTRA = "s2r:extra"
CB_STEP2_RESULT_DIAGRAM = "s2r:diagram"
CB_STEP2_RESULT_RESTART = "s2r:restart"
CB_STEP2_EXTRA_RESTART = "s2e:restart"
CB_STEP2_EXTRA_MENU = "s2e:menu"
CB_HELP = "help"
CB_0H3_BACK = "0h3:back"
CB_0H3_MENU = "0h3:menu"

# Кнопка сценария (Шаг 1) — один сценарий: анализ проблемы
SCENARIO_BUTTONS = [[KeyboardButton("Анализ проблемы")]]

# Кнопка «Нужна помощь» (добавляется к клавиатурам)
HELP_BUTTON = [[KeyboardButton("Нужна помощь")]]


def keyboard_step1() -> ReplyKeyboardMarkup:
    """Шаг 1: выбор сценария (без дублирующей кнопки «Нужна помощь» — она только под постами, inline)."""
    return ReplyKeyboardMarkup(
        SCENARIO_BUTTONS,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def keyboard_choice(buttons: list[list[str]], add_help: bool = False) -> ReplyKeyboardMarkup:
    """Клавиатура с кнопками выбора. buttons = [[row1_btn1, row1_btn2], [row2_btn1]]"""
    kb = [[KeyboardButton(b) for b in row] for row in buttons]
    if add_help:
        kb += HELP_BUTTON
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)


def keyboard_simple(buttons: list[str], add_help: bool = False) -> ReplyKeyboardMarkup:
    """Простая клавиатура: список кнопок по одной в ряд."""
    kb = [[KeyboardButton(b)] for b in buttons]
    if add_help:
        kb += HELP_BUTTON
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)


def keyboard_two(btn1: str, btn2: str, add_help: bool = False) -> ReplyKeyboardMarkup:
    """Две кнопки в ряд."""
    kb = [[KeyboardButton(btn1), KeyboardButton(btn2)]]
    if add_help:
        kb += HELP_BUTTON
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)


def keyboard_help_only() -> ReplyKeyboardMarkup:
    """Только кнопка «Нужна помощь» (для шагов с вводом текста)."""
    return ReplyKeyboardMarkup(HELP_BUTTON, resize_keyboard=True, one_time_keyboard=False)


# === Inline-клавиатуры ===


def inline_step1() -> InlineKeyboardMarkup:
    """Шаг 1: выбор сценария (inline)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Анализ проблемы", callback_data=CB_STEP1_ANALYSIS)],
        [InlineKeyboardButton("Нужна помощь", callback_data=CB_HELP)],
    ])


def inline_step2_result() -> InlineKeyboardMarkup:
    """Шаг 2_result: кнопки после анализа (inline)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Нужна дополнительная аналитика", callback_data=CB_STEP2_RESULT_EXTRA)],
        [InlineKeyboardButton("Сделать диаграмму решений", callback_data=CB_STEP2_RESULT_DIAGRAM)],
        [InlineKeyboardButton("Начать сначала", callback_data=CB_STEP2_RESULT_RESTART)],
        [InlineKeyboardButton("Нужна помощь", callback_data=CB_HELP)],
    ])


def inline_step2_extra_result() -> InlineKeyboardMarkup:
    """Шаг 2_extra_result (inline)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Начать сначала", callback_data=CB_STEP2_EXTRA_RESTART),
            InlineKeyboardButton("В главное меню", callback_data=CB_STEP2_EXTRA_MENU),
        ],
        [InlineKeyboardButton("Нужна помощь", callback_data=CB_HELP)],
    ])


def inline_step0H_3() -> InlineKeyboardMarkup:
    """Шаг 0H_3: после «Нужна помощь» (inline)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Вернуться в диалог", callback_data=CB_0H3_BACK),
            InlineKeyboardButton("В главное меню", callback_data=CB_0H3_MENU),
        ],
    ])
