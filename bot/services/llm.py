"""Интеграция с OpenAI для генерации ответов."""
import logging
from typing import Optional

from bot.config.settings import LLM_API_KEY

logger = logging.getLogger(__name__)


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
