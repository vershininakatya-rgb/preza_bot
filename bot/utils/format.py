"""Форматирование текста для отображения в Telegram."""
import re
import html


def _is_header_line(line: str) -> bool:
    """Строка — заголовок, если целиком **текст** или начинается с поля анализа (**Проблема:**, **Доказательства**, **Решения:**)."""
    stripped = line.strip()
    if re.match(r"^\s*\*\*[^*]+\*\*\s*$", line):
        return True
    # Поля блока анализа не нумеруем — у них уже есть подпись
    if stripped.startswith("**Проблема:**") or "**Доказательства" in stripped[:25] or stripped.startswith("**Решения:**"):
        return True
    return False


def format_analysis_text(text: str) -> str:
    """
    Очищает текст анализа: убирает ###, ---, звёздочки.
    Разбивает склеенные блоки (Проблема | Доказательства | Решения) на отдельные строки для читаемости.
    Заголовки выделяет жирным через HTML <b>.
    Пункты (кроме заголовков) нумерует: 1., 2., 3. (сброс при новом заголовке).
    Результат готов для parse_mode='HTML'.
    """
    if not text:
        return text

    # Разбить склеенные поля: " ... | **Доказательства" -> " ...\n\n**Доказательства"
    text = re.sub(r"\s*\|\s*(?=\*\*)", "\n\n", text)
    # Решения с новой строки: "1) ... 2) ... 3) ..." -> каждая строка отдельно
    text = re.sub(r" 2\) ", "\n2) ", text)
    text = re.sub(r" 3\) ", "\n3) ", text)

    # Убираем ### в начале строк
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # Убираем строки из одних дефисов/подчёркиваний
    text = re.sub(r"^[-_]{2,}\s*$", "", text, flags=re.MULTILINE)
    # Убираем --- между блоками (заменяем на перенос)
    text = re.sub(r"\n[-_]{2,}\n", "\n\n", text)

    # Нумеруем пункты в каждом блоке (кроме заголовков и пустых строк)
    lines = text.split("\n")
    result_lines = []
    num = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or _is_header_line(line):
            result_lines.append(line)
            if _is_header_line(line):
                num = 0
        else:
            # Убираем уже имеющуюся нумерацию (1. 2) и т.п.)
            content = re.sub(r"^\d+[\.\)]\s*", "", stripped)
            num += 1
            result_lines.append(f"{num}. {content}")
    text = "\n".join(result_lines)

    # Сначала заменяем **X** на placeholder, потом экранируем, потом вставляем <b>
    placeholders: list[str] = []

    def save_bold(m: re.Match) -> str:
        placeholders.append(html.escape(m.group(1).strip()))
        return f"\x00B{len(placeholders)-1}\x00"

    text = re.sub(r"\*\*([^*]+)\*\*", save_bold, text)

    # Убираем оставшиеся одиночные *
    text = re.sub(r"(?<!\w)\*+(?!\w)", "", text)

    # Экранируем HTML в оставшемся тексте
    text = html.escape(text)

    # Восстанавливаем жирные заголовки
    for i, ph in enumerate(placeholders):
        text = text.replace(f"\x00B{i}\x00", f"<b>{ph}</b>")

    # Схлопываем лишние пустые строки
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
