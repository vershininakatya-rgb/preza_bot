-- Схема для хранения данных бота (пользователи, аналитика, диаграммы, обратная связь).
-- Запуск: через scripts/init_supabase_schema.py (читает этот файл и выполняет).

-- Расширение для RAG (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Пользователи Telegram
CREATE TABLE IF NOT EXISTS telegram_users (
    id BIGSERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL UNIQUE,
    username TEXT,
    full_name TEXT,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telegram_users_telegram_user_id ON telegram_users(telegram_user_id);

-- Аналитика проблем (один проход сценария: загрузка данных + результат LLM + опционально доп. аналитика)
CREATE TABLE IF NOT EXISTS analyses (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES telegram_users(id) ON DELETE CASCADE,
    input_texts JSONB NOT NULL DEFAULT '[]',
    file_descriptions JSONB NOT NULL DEFAULT '[]',
    analysis_result TEXT,
    extra_request TEXT,
    extra_result TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at);

-- Диаграммы решений (по нажатию «Сделать диаграмму решений»)
CREATE TABLE IF NOT EXISTS diagrams (
    id BIGSERIAL PRIMARY KEY,
    analysis_id BIGINT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES telegram_users(id) ON DELETE CASCADE,
    mermaid_code TEXT,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_diagrams_analysis_id ON diagrams(analysis_id);
CREATE INDEX IF NOT EXISTS idx_diagrams_user_id ON diagrams(user_id);

-- Обратная связь «Нужна помощь»
CREATE TABLE IF NOT EXISTS feedback_requests (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES telegram_users(id) ON DELETE CASCADE,
    step TEXT,
    message_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_requests_user_id ON feedback_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_requests_created_at ON feedback_requests(created_at);
