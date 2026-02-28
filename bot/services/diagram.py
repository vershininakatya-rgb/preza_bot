"""Генерация диаграмм дерева решений через Kroki API и LLM."""
import logging
import re
from typing import Optional

from bot.config.settings import LLM_API_KEY
from bot.services.llm import llm_generate

logger = logging.getLogger(__name__)

KROKI_URL = "https://kroki.io"

# Пример дерева решений (fallback, если LLM недоступен или вернул невалидный код)
EXAMPLE_MERMAID = """
flowchart TD
    root[Анализ проблемы] --> p1[Низкая прозрачность потока]
    root --> p2[Перегрузка команды]
    root --> p3[Размытые цели]
    p1 --> |Kanban-доска| r1[Визуализация WIP]
    p2 --> |Ограничение WIP| r2[Фокус на приоритетах]
    p3 --> |OKR| r3[Чёткие цели и метрики]
"""


async def llm_analysis_to_mermaid(analysis_text: str) -> Optional[str]:
    """
    Преобразует текст анализа в Mermaid flowchart (дерево решений).
    Формат: flowchart TD с узлами проблем и решений, связями.
    """
    system = (
        "Ты — эксперт по визуализации. Преобразуй текст анализа в диаграмму дерева решений.\n\n"
        "Выдай ТОЛЬКО валидный код Mermaid, без markdown, без пояснений.\n\n"
        "Формат:\n"
        "flowchart TD\n"
        "  root[Проблема] --> p1[Проблема 1]\n"
        "  root --> p2[Проблема 2]\n"
        "  p1 --> |Решение| r1[Результат 1]\n"
        "  p2 --> |Решение| r2[Результат 2]\n\n"
        "Правила:\n"
        "- Используй flowchart TD (сверху вниз)\n"
        "- Узлы: [текст] для прямоугольников, {текст} для ромбов (условия)\n"
        "- Связи: --> для стрелок, --> |метка| для подписанных\n"
        "- Текст в узлах — кратко, на русском, без переносов внутри узла\n"
        "- Максимум 15–20 узлов, иначе диаграмма нечитаема\n"
        "- Идентификаторы узлов: только латиница и цифры (a1, p1, r1)\n"
    )
    prompt = (
        "Преобразуй этот анализ в Mermaid flowchart (дерево решений). "
        "Выдай только код, без ```mermaid и без ```:\n\n"
        f"{analysis_text[:4000]}"
    )
    result = await llm_generate(prompt, system_prompt=system, max_tokens=1500)
    if not result:
        return None
    # Убираем обёртки ```mermaid ... ```
    code = result.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        if lines[0].startswith("```mermaid"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
    return code.strip() or None


async def kroki_render_mermaid(mermaid_code: str, output_format: str = "png") -> tuple[Optional[bytes], Optional[str]]:
    """
    Рендерит Mermaid-код в изображение через Kroki API.
    Возвращает (bytes изображения, None) или (None, сообщение об ошибке).
    """
    try:
        import httpx

        url = f"{KROKI_URL}/mermaid/{output_format}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                content=mermaid_code.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
        if resp.status_code != 200:
            return None, f"Kroki вернул {resp.status_code}: {resp.text[:200]}"
        return resp.content, None
    except Exception as e:
        logger.warning("Kroki render failed: %s", e)
        return None, str(e)[:150]


def _strip_html(text: str) -> str:
    """Удаляет HTML-теги из текста."""
    return re.sub(r"<[^>]+>", "", text).strip()


async def generate_decision_tree_diagram(analysis_text: str) -> tuple[Optional[bytes], Optional[str]]:
    """
    Генерирует PNG-диаграмму дерева решений из текста анализа.
    Использует LLM для преобразования в Mermaid и Kroki для рендеринга.
    При сбое LLM или отсутствии ключа возвращает пример диаграммы.
    Возвращает (bytes изображения, None) или (None, сообщение об ошибке).
    """
    plain = _strip_html(analysis_text or "")

    if LLM_API_KEY and LLM_API_KEY.strip() not in ("your_llm_api_key_here", "sk-your_openai_api_key_here"):
        if plain:
            mermaid = await llm_analysis_to_mermaid(plain)
            if mermaid:
                img_bytes, err = await kroki_render_mermaid(mermaid)
                if not err:
                    return img_bytes, None

    # Fallback: пример дерева решений (если LLM недоступен или вернул невалидный код)
    img_bytes, err = await kroki_render_mermaid(EXAMPLE_MERMAID.strip())
    if err:
        return None, err or "Не удалось сгенерировать диаграмму."
    return img_bytes, None
