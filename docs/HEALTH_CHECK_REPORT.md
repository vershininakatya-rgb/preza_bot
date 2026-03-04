# Health-check report: preza_bot

## Summary

| Area | Status | Notes |
|------|--------|--------|
| **Architecture** | Docs out of date | ARCHITECTURE.md и BOT_FLOW.md не совпадают с текущим сценарием (1 → 2_upload → 2_result → 2_extra_*). Код: storage, steps, keyboards, services — согласованы. |
| **Bugs / risks** | Средний риск | Race при параллельных апдейтах; reply.py — нет проверки файла перед open(); LLM — нет проверки response.choices; callback — возможен краш при пустом query.data. |
| **Dead code** | Есть | llm_generate_analysis_diagram (DALL-E) не используется; format_user_info в helpers не используется. |
| **Config & env** | Ок | Конфиг из env; при ошибке int(ADMIN_CHAT_ID) — тихий pass. |
| **Inconsistencies** | Есть | Дублирование логики в handle_message и handle_callback; смешение parse_mode (Markdown/HTML) — осознанное. |
| **Tests / README** | Пробелы | Тестов нет; README устарел. |

---

## 1. Architecture

- **Точки входа:** main.py, run.py — оба вызывают bot.main.main(). Railway: railpack.json → main.py, Procfile → run.py (расхождение).
- **Поток:** Handlers → get_state/set_state → flow → LLM/diagram. Клавиатуры в keyboards.py, шаги в flow.py.
- **Документация:** ARCHITECTURE.md не упоминает diagram.py, rag.py, keyboards, reply; описан шаг «6 — дерево», в коде шаги 2_upload/2_result/2_extra_*.

---

## 2. Bugs & risks

1. **storage:** один словарь _user_states — при параллельных апдейтах одного user_id возможна потеря данных (last write wins). Рекомендация: блокировка по user_id или копирование при записи.
2. **reply.py:** open(photo_path) без проверки существования файла → FileNotFoundError. Рекомендация: os.path.isfile() или try/except.
3. **llm.py:** response.choices[0] без проверки пустого choices → IndexError. Рекомендация: if not response.choices: return None.
4. **handle_callback:** query.data может быть None → краш. Рекомендация: if not query.data: return.
5. **ADMIN_CHAT_ID:** int(ADMIN_CHAT_ID) при пустой/нечисловой строке → ValueError перехватывается except: pass без лога. Рекомендация: логировать предупреждение.
6. Callback_data все < 64 байт — ок.

---

## 3. Dead code

- **llm_generate_analysis_diagram** (llm.py) — не вызывается; диаграммы в diagram.py (Kroki+Mermaid).
- **format_user_info** (helpers.py) — не используется.
- Для 2_result задаётся и Reply, и Inline — приоритет у inline, Reply по сути не показывается.

---

## 4. Config & env

- Секреты только в env. Проверяется только BOT_TOKEN. ADMIN_CHAT_ID без валидации.
- CI: только BOT_TOKEN. .env.example полный; RAG_EMBEDDING_MODEL в примере нет (в коде дефолт).
- Запуск: railpack.json — main.py, Procfile — run.py; лучше один способ.

---

## 5. Inconsistencies

- **Дублирование:** handle_message и handle_callback повторяют переходы (0H, сброс, 2_result, 2_extra_result, 1, 2_upload, 2_extra_ask). Рекомендация: общая функция send_step_response(update, next_step, new_state, …).
- Reply vs Inline — осознанное: выбор сценария и действия после анализа — inline; ввод текста — Reply. parse_mode: Markdown по умолчанию, HTML для результатов — согласовано.

---

## 6. Recommendations (кратко)

1. Обновить ARCHITECTURE.md и README под текущую структуру.
2. Устранить дублирование в handle_message/handle_callback (общая функция по next_step).
3. reply.py: проверка файла или try/except перед open().
4. llm.py: проверка response.choices перед [0].
5. handle_callback: if not query.data: return.
6. ADMIN_CHAT_ID: логировать при ошибке int().
7. Удалить/пометить: llm_generate_analysis_diagram, format_user_info.
8. Единая точка входа (main.py или run.py) в Procfile/railpack.
9. Минимальные тесты; README — актуальная структура и «cd preza_bot».

---

## 7. Конкретные правки (список)

**Уже внесённые правки (код):**
- **reply.py** — проверка `os.path.isfile(photo_path)` и `try/except OSError` при открытии файла фото.
- **llm.py** — проверка `if not response.choices` в `llm_generate` и `llm_describe_image` перед доступом к `[0]`.
- **llm.py** — комментарий, что `llm_generate_analysis_diagram` не используется (диаграммы в diagram.py).
- **messages.py** — в `handle_callback` проверка `if not getattr(query, "data", None): return`.
- **messages.py** — при ошибке отправки админу логирование `logging.getLogger(__name__).warning(...)` вместо `pass`.
- **helpers.py** — комментарий, что `format_user_info` зарезервирована для будущего использования.

| # | Файл | Изменение |
|---|------|-----------|
| 1 | bot/utils/reply.py | Проверка os.path.isfile(photo_path) или try/except FileNotFoundError |
| 2 | bot/services/llm.py | if not response.choices: return None в llm_generate и llm_describe_image |
| 3 | bot/handlers/messages.py | if not query.data: return в handle_callback |
| 4 | bot/handlers/messages.py | except Exception: log warning при ошибке отправки админу |
| 5 | bot/services/llm.py | Удалить или пометить llm_generate_analysis_diagram |
| 6 | bot/utils/helpers.py | Удалить или пометить format_user_info |
| 7 | docs/ARCHITECTURE.md | Обновить дерево и поток под текущий код |
| 8 | README.md | cd preza_bot, структура, возможности |
| 9 | Procfile / railpack.json | Один способ запуска |
| 10 | .env.example | Опционально RAG_EMBEDDING_MODEL |
