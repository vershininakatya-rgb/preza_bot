# Настройка RAG (PostgreSQL + pgvector)

RAG обогащает аналитику бота релевантными фрагментами из базы знаний.

## 1. PostgreSQL с pgvector

Установите расширение pgvector в PostgreSQL:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Docker:

```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres ankane/pgvector
```

## 2. Переменные окружения

В `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/preza_bot
RAG_ENABLED=true
RAG_TOP_K=5
```

## 3. База знаний

Добавьте документы в `knowledge/` (TXT, MD, PDF, DOCX):

- методологии (Kanban, OKR, ADKAR и др.)
- кейсы и шаблоны анализа

## 4. Индексация

```bash
python -m scripts.build_index
```

Скрипт создаёт таблицу `rag_chunks`, разбивает документы на чанки и сохраняет эмбеддинги.

## 5. Использование

При `RAG_ENABLED=true` бот автоматически подтягивает релевантные фрагменты при:

- первичном анализе (`llm_analyze_problem`)
- дополнительной аналитике (`llm_supplement_analysis`)

При ошибках RAG бот продолжает работать без контекста из базы знаний.
