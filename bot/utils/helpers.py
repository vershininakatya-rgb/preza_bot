"""Вспомогательные функции для бота."""


def format_user_info(user) -> str:
    """Форматирует информацию о пользователе."""
    info = f"ID: {user.id}\n"
    info += f"Имя: {user.first_name}"
    if user.last_name:
        info += f" {user.last_name}"
    if user.username:
        info += f"\nUsername: @{user.username}"
    return info
