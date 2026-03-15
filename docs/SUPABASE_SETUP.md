# Настройка Supabase для хранения данных бота

Бот может сохранять в БД: пользователей, аналитику проблем, диаграммы решений, обратную связь «Нужна помощь». Используется один `DATABASE_URL` (Supabase или любой PostgreSQL с расширением pgvector для RAG).

## Шаг 1. Создать проект в Supabase

1. [supabase.com](https://supabase.com) → New Project.
2. Укажите организацию, имя проекта, пароль БД (сохраните пароль).
3. Дождитесь создания проекта.

## Шаг 2. Включить pgvector

Project Settings → Database → Extensions → найдите **vector** → Enable.  
Нужно для RAG (база знаний) и для будущего использования эмбеддингов.

## Шаг 3. Получить connection string

Project Settings → Database → Connection string → **URI**.  
Подставьте пароль вместо `[YOUR-PASSWORD]`.  
Формат: `postgresql://postgres.[ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres`  
(для Session mode замените в URI `?pgbouncer=true` на `?pgbouncer=false` если нужен прямой доступ к pgvector).

## Шаг 4. Инициализировать схему один раз

Локально (с `DATABASE_URL` в `.env`):

```bash
python -m scripts.init_supabase_schema
```

Или в Railway: одноразовый run (если доступен) или локально с `DATABASE_URL` из переменных Railway.

Скрипт создаёт таблицы: `telegram_users`, `analyses`, `diagrams`, `feedback_requests`, включает расширение `vector`.

## Шаг 5. Переменные окружения

- **DATABASE_URL** — URI из шага 3 (обязательно для сохранения данных и RAG).
- **PERSIST_TO_DB** — `true` чтобы бот писал в эти таблицы; `false` или не задано — только память (по умолчанию `true` при наличии DATABASE_URL).

В Railway добавьте `DATABASE_URL` в Variables сервиса бота. Секреты не коммитить.

## RAG (база знаний)

Если используете RAG с Supabase, после инициализации схемы выполните индексацию документов:

```bash
python -m scripts.build_index
```

См. также [RAG_SETUP.md](RAG_SETUP.md).
