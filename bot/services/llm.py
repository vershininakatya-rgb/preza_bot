"""Интеграция с OpenAI для генерации ответов."""
import base64
import logging
from typing import Optional

from bot.config.settings import LLM_API_KEY

logger = logging.getLogger(__name__)


async def llm_analyze_problem(data_text: str) -> Optional[str]:
    """
    Анализ данных: выявить проблемы с командой и варианты решений.
    """
    system = (
        "Ты — эксперт по аналитике процессов и команд. "
        "Проанализируй предоставленные данные (схему процесса, результаты интервью) и структурируй ответ:\n\n"
        "1. **Проблемы с командой** — что не работает, какие симптомы, противоречия\n"
        "2. **Варианты решений** — конкретные рекомендации по улучшению\n\n"
        "Пиши кратко, по пунктам. Язык — русский."
    )
    return await llm_generate(
        f"Данные для анализа:\n\n{data_text}",
        system_prompt=system,
        max_tokens=2000,
    )


async def llm_supplement_analysis(data_text: str, original_analysis: str, user_request: str) -> Optional[str]:
    """
    Дополнительная аналитика: углублённый разбор по запросу пользователя.
    """
    system = (
        "Ты — эксперт по аналитике процессов и команд. "
        "Пользователь уже получил первичный анализ. Теперь он просит дополнительную аналитику. "
        "На основе исходных данных и имеющегося анализа дай углублённый разбор по запрошенному аспекту. "
        "Структурируй ответ кратко, по пунктам. Язык — русский."
    )
    prompt = (
        f"Исходные данные:\n\n{data_text[:6000]}\n\n"
        f"---\nПервичный анализ:\n\n{original_analysis[:3000]}\n\n"
        f"---\nЗапрос пользователя на дополнительную аналитику: {user_request}\n\n"
        "Дополни анализ по запрошенному аспекту."
    )
    return await llm_generate(prompt, system_prompt=system, max_tokens=2000)


async def llm_describe_image(image_bytes: bytes) -> Optional[str]:
    """
    Описать содержимое изображения (схема, диаграмма) для последующего анализа.
    """
    _placeholders = ("your_llm_api_key_here", "sk-your_openai_api_key_here")
    if not LLM_API_KEY or LLM_API_KEY.strip() in _placeholders:
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=LLM_API_KEY)
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Опиши подробно: что изображено на схеме/диаграмме? Какие процессы, роли, связи? Выдели ключевые элементы. Язык — русский.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("LLM image description failed: %s", e)
        return None


async def llm_generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 1500,
) -> Optional[str]:
    """
    Вызвать OpenAI API и вернуть сгенерированный текст.
    Возвращает None при ошибке или отсутствии ключа.
    """
    _placeholders = ("your_llm_api_key_here", "sk-your_openai_api_key_here")
    if not LLM_API_KEY or LLM_API_KEY.strip() in _placeholders:
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=LLM_API_KEY)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("LLM request failed: %s", e)
        return None
