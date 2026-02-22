"""Хранилище сессий и состояния диалога."""
from bot.storage.session import get_state, set_state, clear_state

__all__ = ["get_state", "set_state", "clear_state"]
