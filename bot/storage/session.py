"""Хранение состояния диалога в памяти (словарь по user_id)."""
from typing import Any

# user_id -> state dict
_user_states: dict[int, dict[str, Any]] = {}


def get_state(user_id: int) -> dict[str, Any]:
    """Вернуть текущее состояние пользователя или дефолт."""
    if user_id not in _user_states:
        _user_states[user_id] = {
            "step": "1",
            "scenario": None,
            "onboarding": {},
            "context": {},
            "data": {},
            "return_after_help": None,
            "step_entered_at": None,
        }
    return _user_states[user_id]


def set_state(user_id: int, state: dict[str, Any]) -> None:
    """Сохранить состояние пользователя."""
    _user_states[user_id] = state


def clear_state(user_id: int) -> None:
    """Сбросить состояние (начать сначала)."""
    if user_id in _user_states:
        del _user_states[user_id]
