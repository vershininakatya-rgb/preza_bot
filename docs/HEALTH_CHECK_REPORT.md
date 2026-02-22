# Health Check Report — preza_bot

**Дата:** 2026-02-22

---

## 1. Архитектура

### 1.1 Несоответствие документации и кода

**ARCHITECTURE.md** и **README.md** описывают старую структуру. В коде есть модули, которых нет в документации:

| В коде | В ARCHITECTURE.md |
|--------|-------------------|
| `bot/storage/` (session.py) | ❌ Нет |
| `bot/steps/` (flow.py) | ❌ Нет |
| `bot/keyboards.py` | ❌ Нет |
| `bot/services/` (llm.py) | ❌ Нет |

**Рекомендация:** Обновить ARCHITECTURE.md и README.md под текущую структуру.

### 1.2 Поток данных

Реальный поток:
```
Telegram API → main.py → handlers → storage (state) + steps (flow) + keyboards
                                    ↓
                              services/llm (при шаге 6)
                                    ↓
                              Response → Telegram API
```

---

## 2. Баги и потенциальные ошибки

### 2.1 error_handler: update может быть None

**Файл:** `bot/handlers/commands.py`

```python
logger.error(f"Update {update} caused error {context.error}")
```

При ошибках во время polling (например, сетевой сбой) `update` может быть `None`. Обращение к `update` в f-string безопасно, но при попытке `update.effective_user` будет AttributeError. Сейчас такого обращения нет — риск низкий, но лучше явно обработать `update is None`.

### 2.2 Шаг 0H_1: двойное сообщение

**Файл:** `bot/handlers/messages.py` (строки 37–39)

Бот отправляет два сообщения подряд:
1. `get_step_message("0H_3")` — «Ваш запрос передан...»
2. «Выберите:» + клавиатура

Можно объединить в одно сообщение.

### 2.3 Широкий except в build_analytics_tree_with_llm

**Файл:** `bot/steps/flow.py`

```python
except Exception:
    pass
```

Все исключения проглатываются без логирования. При сбое LLM сложно понять причину.

### 2.4 ADMIN_CHAT_ID: избыточный except

**Файл:** `bot/handlers/messages.py`

```python
except (ValueError, Exception):
    pass
```

`Exception` уже включает `ValueError`. Достаточно `except Exception`.

---

## 3. Ненужный код и конфигурации

### 3.1 Неиспользуемый импорт

**Файл:** `bot/main.py`
- `import asyncio` — не используется.

### 3.2 Неиспользуемая функция

**Файл:** `bot/utils/helpers.py`
- `format_user_info(user)` — нигде не вызывается.

### 3.3 Устаревшие документы-заглушки

- **docs/API.md** — шаблон с placeholder'ами, не соответствует реальному боту.
- **docs/FEATURES.md** — все пункты `[ ]`, не отражает текущую функциональность.

### 3.4 README.md

- Строка `cd 111` — вероятно, скопировано из другого проекта. Для preza_bot корректнее `cd preza_bot` или путь к репозиторию.
- Структура проекта в README не включает `storage/`, `steps/`, `keyboards.py`, `services/`.

---

## 4. Конфигурация

### 4.1 LLM ключ

**Файл:** `bot/services/llm.py`

Проверка: `LLM_API_KEY == "your_llm_api_key_here"`. В `.env.example` теперь `sk-your_openai_api_key_here`. Стоит добавить проверку на оба варианта или на пустое/placeholder-значение.

### 4.2 Makefile: build пересоздаёт venv

При каждом `make build` venv создаётся заново. Для разработки удобнее `make install` при уже существующем venv. Текущее поведение приемлемо для CI, но можно добавить в README пояснение.

### 4.3 .gitignore

Актуален. `.env` в списке — секреты не попадут в репозиторий.

---

## 5. Рекомендуемые правки (по приоритету)

| # | Правка | Файл | Риск |
|---|--------|------|------|
| 1 | Удалить `import asyncio` | main.py | Нет |
| 2 | Упростить `except (ValueError, Exception)` → `except Exception` | messages.py | Нет |
| 3 | Добавить логирование в `except Exception` в build_analytics_tree_with_llm | flow.py | Нет |
| 4 | Объединить два сообщения в шаге 0H_1 | messages.py | Низкий |
| 5 | Добавить проверку placeholder для LLM (sk-your...) | llm.py | Нет |
| 6 | Обновить ARCHITECTURE.md | docs/ | Нет |
| 7 | Удалить или пометить format_user_info как deprecated | helpers.py | Нет |
| 8 | Обновить README (структура, cd) | README.md | Нет |

---

## 6. Что работает корректно

- Загрузка настроек из `.env`
- Хранение сессий в памяти
- Маршрутизация по шагам
- Интеграция с OpenAI (с fallback)
- Обработка «Нужна помощь» и уведомление админу
- Makefile (build, run, clean)
- .gitignore
- GitHub Actions release workflow
