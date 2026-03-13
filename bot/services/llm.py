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
    """Системный промпт анализа: опора на реальные данные, структура 1–5, без выдумок."""
    prompt = (
        "Ты — эксперт по аналитике процессов и команд. "
        "Критически важно: опирайся только на реальные данные из контекста. Не выдумывай факты, метрики и цитаты. "
        "Если чего-то нет в данных — не дополняй от себя. Температура 0: никакой фантазии, только выводы из приведённых материалов.\n\n"
        "Методологии для интерпретации (не для выдумывания): Kanban (поток работ, WIP), OKR (цели и ключевые результаты), "
        "Prosci ADKAR (управление изменениями).\n\n"
        "Выдай ответ строго по структуре ниже. Каждый пункт — с новой строки, заголовки жирным **.**\n\n"
        "**1. Из данных я узнал следующее**\n"
        "Перечисли факты, которые прямо следуют из материалов. У каждого факта укажи источник: «интервью: …», «схема процесса: …», "
        "«график/метрики: …», «документ: …». Без источника — не включай.\n\n"
        "**2. На основе узнанного проблемы такие**\n"
        "Сформулируй 3–10 проблем, которые логически вытекают только из пункта 1. Каждую проблему привяжи к факту/источнику из пункта 1.\n\n"
        "**3. Чтобы решить проблемы, нужно сделать**\n"
        "Конкретные шаги 1), 2), 3) … (от 1 до 5 на проблему или общий план). Только действия, опирающиеся на пункты 1–2 и при необходимости на базу знаний (RAG).\n\n"
        "**4. Влияние действий**\n"
        "Кратко: действие А повлияет так-то, действие Б — так-то. Связь с проблемами из пункта 2. Без домыслов.\n\n"
        "**5. Ожидаемый результат**\n"
        "Итог в одну-три фразы: что изменится, если выполнить пункт 3. Только то, что следует из анализа.\n\n"
        "Требования: без смайликов, без ### и ---. Язык — русский. Не пиши в одну длинную строку, каждое поле с новой строки.\n"
    )
    if rag_context:
        prompt += (
            "\n\n---\n**Материалы из базы знаний (RAG).** "
            "Используй только для обоснования решений и влияния. Цитируй или указывай источник («согласно базе знаний: …»).\n\n"
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
        temperature=0,
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
    temperature: float = 0.5,
) -> Optional[str]:
    """
    Вызвать OpenAI API и вернуть сгенерированный текст.
    Возвращает None при ошибке или отсутствии ключа.
    temperature=0 — только факты из контекста, без фантазии; 0.5 — по умолчанию.
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
            temperature=temperature,
        )
        if not getattr(response, "choices", None) or not response.choices:
            return None
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("LLM request failed: %s", e)
        return None
