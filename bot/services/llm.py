"""Интеграция с OpenAI для генерации ответов."""
import base64
import logging
from typing import Optional

from bot.config.settings import LLM_API_KEY, RAG_ENABLED

logger = logging.getLogger(__name__)


# Не используется: диаграммы генерируются в services/diagram.py через Kroki+Mermaid.
async def llm_generate_analysis_diagram(analysis_text: str) -> tuple[Optional[bytes], Optional[str]]:
    """
    Генерирует схему сопоставления проблем и решений через DALL-E 3.
    Возвращает (bytes изображения или None, сообщение об ошибке или None).
    """
    _placeholders = ("your_llm_api_key_here", "sk-your_openai_api_key_here")
    if not LLM_API_KEY or LLM_API_KEY.strip() in _placeholders:
        return None, (
            "В .env не задан OPENAI_API_KEY или LLM_API_KEY. "
            "Добавьте ключ: https://platform.openai.com/api-keys"
        )

    try:
        # Краткое описание для промпта DALL-E (до 1000 символов)
        dalle_prompt = (
            "Professional flowchart diagram, business infographic style. "
            "Left column: problem boxes. Right column: solution boxes. "
            "Arrows connecting each problem to its corresponding solution. "
            "Clean, minimal design, suitable for presentation. "
            "No text labels in the image."
        )
        if len(analysis_text) > 200:
            # Добавляем контекст из анализа (первые 300 символов для контекста)
            summary = analysis_text[:300].replace("*", "").replace("\n", " ")
            dalle_prompt = (
                "Professional flowchart diagram showing problem-solution mapping. "
                "Left side: problem areas. Right side: solution options. "
                "Arrows from each problem to its solution. "
                "Business infographic, clean minimal style. No text in image."
            )

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=LLM_API_KEY)
        response = await client.images.generate(
            model="dall-e-3",
            prompt=dalle_prompt[:1000],
            size="1024x1024",
            quality="standard",
            n=1,
            response_format="b64_json",
        )
        img = response.data[0]
        b64_data = getattr(img, "b64_json", None)
        if not b64_data:
            return None, "OpenAI не вернул данные изображения"

        return base64.standard_b64decode(b64_data), None
    except Exception as e:
        err = str(e).lower()
        logger.warning("Diagram generation failed: %s", e)
        if "invalid" in err or "authentication" in err or "api_key" in err:
            return None, "Неверный OPENAI_API_KEY. Проверьте ключ в .env"
        if "quota" in err or "insufficient" in err or "billing" in err:
            return None, "Исчерпан лимит или нет оплаты на аккаунте OpenAI"
        if "content" in err or "policy" in err:
            return None, "Контент отклонён политикой OpenAI"
        return None, f"Ошибка: {str(e)[:100]}"


def _analysis_system_prompt(rag_context: str) -> str:
    """Системный промпт анализа: таблица Проблема | Доказательства (источник) | Решения."""
    prompt = (
        "Ты — эксперт по аналитике процессов и команд. "
        "Используй данные в контексте методологий:\n"
        "• Kanban — визуализация потока работ, ограничение WIP, непрерывное улучшение\n"
        "• OKR (Objectives and Key Results) — цели и ключевые результаты для выравнивания и измерения\n"
        "• Prosci ADKAR — управление изменениями: Awareness, Desire, Knowledge, Ability, Reinforcement\n\n"
        "Проанализируй данные (схему процесса, результаты интервью, графики, метрики) и выдай результат по шаблону ниже.\n\n"
        "**Обязательный формат — для каждой проблемы три строки и пустая строка после блока:**\n\n"
        "**Проблема:** одна короткая фраза (суть проблемы).\n"
        "**Доказательства (источник):** один источник в одну строку: например «интервью: цитата» или «график X, данные за май».\n"
        "**Решения:** каждое решение с новой строки:\n"
        "1) первое решение\n"
        "2) второе решение\n"
        "3) третье решение\n\n"
        "(пустая строка)\n\n"
        "**Проблема:** следующая проблема…\n"
        "**Доказательства (источник):** …\n"
        "**Решения:** …\n\n"
        "Требования:\n"
        "• Минимум 3 проблемы, максимум 10. Каждый блок: три строки (Проблема, Доказательства, Решения), затем пустая строка.\n"
        "• Не пиши всё в одну строку и не используй | между полями. Каждое поле — с новой строки. Формулировки короткие, по делу.\n"
        "• Без смайликов, без ### и без ---. Заголовки полей жирным: **Проблема:** **Доказательства (источник):** **Решения:**\n"
        "• Язык — русский.\n"
    )
    if rag_context:
        prompt += (
            "\n\n---\n**Релевантные материалы из базы знаний (RAG).** "
            "Используй их при анализе: опирайся на эти материалы в доказательствах и при формулировании решений. "
            "Указывай источник (например: «по методологии X из базы знаний», «согласно кейсу Y»).\n\n"
            f"{rag_context}"
        )
    return prompt


async def llm_analyze_problem(data_text: str) -> Optional[str]:
    """
    Анализ данных: таблица из 3 колонок — Проблема | Доказательства (источник) | Решения (1–3 на проблему).
    Минимум 3, максимум 10 проблем. RAG подставляется в промпт сразу.
    """
    rag_context = ""
    if RAG_ENABLED:
        try:
            from bot.services.rag import retrieve_relevant_chunks

            rag_context = await retrieve_relevant_chunks(data_text)
        except Exception as e:
            logger.debug("RAG retrieval skipped: %s", e)

    system = _analysis_system_prompt(rag_context)

    return await llm_generate(
        f"Данные для анализа:\n\n{data_text}",
        system_prompt=system,
        max_tokens=3500,
    )


async def llm_supplement_analysis(data_text: str, original_analysis: str, user_request: str) -> Optional[str]:
    """
    Дополнительная аналитика: углублённый разбор по запросу пользователя.
    """
    rag_context = ""
    if RAG_ENABLED:
        try:
            from bot.services.rag import retrieve_relevant_chunks

            query = f"{user_request}\n{original_analysis[:500]}"
            rag_context = await retrieve_relevant_chunks(query)
        except Exception as e:
            logger.debug("RAG retrieval skipped: %s", e)

    system = (
        "Ты — эксперт по аналитике процессов и команд. "
        "Используй методологии: Kanban (поток работ, WIP), OKR (цели и ключевые результаты), Prosci ADKAR (управление изменениями). "
        "Пользователь уже получил первичный анализ. Теперь он просит дополнительную аналитику. "
        "На основе исходных данных и имеющегося анализа дай углублённый разбор по запрошенному аспекту. "
        "Структурируй ответ: каждый пункт — на отдельной строке, один под другим. Без ###, без ---, без смайликов. "
        "Заголовки выделяй жирным: **Заголовок**. Язык — русский."
    )
    if rag_context:
        system += (
            "\n\n---\nРелевантные материалы из базы знаний (RAG). "
            "Приоритетно используй эти материалы при формулировании ответа. "
            "Опирайся на релевантные фрагменты, цитируй ключевые идеи.\n\n"
            f"{rag_context}"
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
        if not getattr(response, "choices", None) or not response.choices:
            return None
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
        if not getattr(response, "choices", None) or not response.choices:
            return None
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("LLM request failed: %s", e)
        return None
