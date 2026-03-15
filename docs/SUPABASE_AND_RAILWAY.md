# Настройка Supabase в связке с Railway

Одна пошаговая цепочка: Supabase как база данных, Railway как среда запуска бота. Бот может подключаться к Supabase **через REST API** (рекомендуется) или напрямую к PostgreSQL по `DATABASE_URL`.

---

## Схема связки

**Вариант A — REST API (рекомендуется):**
```
GitHub  →  Railway (бот)
               ↓
         SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
               ↓
         Supabase (REST API → PostgreSQL)
```

**Вариант B — прямое подключение к БД:**
```
GitHub  →  Railway (бот)
               ↓
         DATABASE_URL (connection string)
               ↓
         Supabase (PostgreSQL)
```

- **Railway** только запускает бота и читает переменные.
- **Supabase** — отдельный сервис; база не разворачивается на Railway.
- При заданных **SUPABASE_URL** и **SUPABASE_SERVICE_ROLE_KEY** бот пишет в таблицы через REST API (библиотека supabase-py). Иначе используется **DATABASE_URL** и прямое подключение (asyncpg).

---

## Порядок действий

### 1. Supabase: проект и БД

1. Зайдите на [supabase.com](https://supabase.com), войдите или зарегистрируйтесь.
2. **New Project** → выберите организацию, имя (например `preza_bot`), задайте **Database Password** и сохраните его. Выберите регион → **Create new project**.
3. Дождитесь создания (1–2 минуты).
4. **Settings** (шестерёнка внизу слева) → **Database** → блок **Extensions** → включите **vector**.
5. На той же странице **Database** найдите **Connection string** → вкладка **URI**. Скопируйте строку и подставьте вместо `[YOUR-PASSWORD]` свой пароль БД. Для RAG при использовании pooler можно заменить в конце `?pgbouncer=true` на `?pgbouncer=false`.  
   Итоговая строка — это ваш **DATABASE_URL** (её нигде не коммитить).

Подробнее: [SUPABASE_SETUP.md](SUPABASE_SETUP.md).

---

### 2. Инициализация схемы БД (один раз)

Таблицы для бота нужно создать в Supabase один раз.

**Вариант А — с вашего компьютера:**

1. Клонируйте репозиторий (если ещё не клонирован), откройте терминал в корне проекта.
2. Создайте файл `.env` в корне и добавьте строку (подставьте свою строку из шага 1.5):
   ```env
   DATABASE_URL=postgresql://postgres.xxxx:ПАРОЛЬ@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?pgbouncer=false
   ```
3. Установите зависимости и выполните:
   ```bash
   pip install -r requirements.txt
   python -m scripts.init_supabase_schema
   ```
   В консоли должно появиться: «Схема успешно применена…».

**Вариант Б — через Supabase SQL Editor:**

1. В дашборде Supabase откройте **SQL Editor**.
2. Скопируйте содержимое файла [scripts/schema.sql](../scripts/schema.sql) из репозитория.
3. Вставьте в редактор и нажмите **Run**. Таблицы и расширение `vector` создадутся.

После этого в **Table Editor** в Supabase должны быть таблицы: `telegram_users`, `analyses`, `diagrams`, `feedback_requests`.

---

### 3. Supabase API keys (для варианта REST API)

Если хотите, чтобы бот писал в Supabase **через REST API** (рекомендуется для связки с Railway):

1. В дашборде Supabase откройте **Settings** (шестерёнка) → **API**.
2. Скопируйте **Project URL** (например `https://xxxx.supabase.co`) → это **SUPABASE_URL**.
3. В блоке **Project API keys** скопируйте **service_role** (secret) → это **SUPABASE_SERVICE_ROLE_KEY**. Не используйте anon key для серверного бота: service_role обходит RLS и подходит для backend.
4. Эти два значения добавьте в Railway (шаг 4). Если заданы оба — бот будет сохранять данные через REST; иначе будет использоваться **DATABASE_URL** (прямое подключение к Postgres).

---

### 4. Railway: проект и переменные

1. Зайдите на [railway.app](https://railway.app), войдите через GitHub.
2. **New Project** → **Deploy from GitHub repo** → выберите репозиторий бота (например `preza_bot`). Дождитесь первого деплоя.
3. Откройте **сервис** (карточка с названием репо) → вкладка **Variables**.
4. Добавьте переменные:

| Переменная | Откуда взять |
|------------|--------------|
| `BOT_TOKEN` | @BotFather в Telegram → ваш бот → Copy Token |
| `SUPABASE_URL` | Supabase → **Settings** → **API** → Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → **Settings** → **API** → service_role (secret) |
| `LLM_API_KEY` | OpenAI API keys (если нужны анализ и диаграммы) |
| `ADMIN_CHAT_ID` | Ваш Telegram chat_id (например через @userinfobot) |

**Для REST API** достаточно **SUPABASE_URL** и **SUPABASE_SERVICE_ROLE_KEY** — тогда **DATABASE_URL** можно не задавать (кроме случая, когда нужен RAG или скрипт `init_supabase_schema`; схему по-прежнему создают один раз по шагу 2, для этого локально нужен DATABASE_URL или выполнение SQL в Supabase).

**Если используете только прямое подключение к БД** (без REST): задайте **DATABASE_URL** (Connection string из шага 1.5) и не задавайте SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY.

Опционально: `LOG_CHAT_ID`, `RAG_ENABLED` = `true`, `PERSIST_TO_DB` = `true`, `DATABASE_URL` (для RAG или init схемы).

5. Сохраните переменные. Railway перезапустит сервис сам.

Подробнее по Railway: [DEPLOY_RAILWAY.md](DEPLOY_RAILWAY.md).

---

### 5. Проверка

1. В Railway откройте вкладку **Deployments** — последний деплой должен быть в статусе **Success**.
2. Вкладка **Logs** — в логах не должно быть ошибок подключения к БД (типа «connection refused» или «password authentication failed»). Обычно видно сообщение о старте бота.
3. В Telegram напишите боту `/start` и пройдите сценарий (анализ, диаграмма, «Нужна помощь»).
4. В Supabase откройте **Table Editor** → таблицы `telegram_users`, `analyses`, `diagrams`, `feedback_requests` — в них должны появиться новые строки после действий в боте.

---

## Важно

- **SUPABASE_SERVICE_ROLE_KEY** и **DATABASE_URL** — секреты. Храните только в `.env` (локально, не коммитить) и в **Railway → Variables**. Не публикуйте в репозитории и не светите в логах.
- Схему БД создают **один раз** (шаг 2). Повторный запуск `scripts.init_supabase_schema` безопасен (таблицы с `IF NOT EXISTS`).
- При использовании REST API бот не подключается к Postgres напрямую; RAG по-прежнему требует **DATABASE_URL** (и скрипт индексации — локально с DATABASE_URL).

---

## Краткий чек-лист

- [ ] Проект в Supabase создан, расширение **vector** включено.
- [ ] Схема применена один раз (`python -m scripts.init_supabase_schema` или SQL в Supabase).
- [ ] В Railway добавлены **BOT_TOKEN**, **SUPABASE_URL**, **SUPABASE_SERVICE_ROLE_KEY** (для REST) или **DATABASE_URL** (для прямого Postgres).
- [ ] Деплой успешен, в логах нет ошибок, в боте есть ответ на `/start`.
- [ ] После теста в боте в Supabase в таблицах появились данные.
