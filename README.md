# Telegram Bot Application

## Описание проекта

Этот проект представляет собой Telegram-бот, разработанный с использованием Python и библиотеки `python-telegram-bot`.

## Возможности

- [ ] Базовая функциональность бота
- [ ] Обработка команд
- [ ] Обработка сообщений
- [ ] Интеграция с внешними API (при необходимости)

## Требования

- Python 3.8+
- Telegram Bot Token (получить у [@BotFather](https://t.me/BotFather))

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd 111
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Для Windows: venv\Scripts\activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env:
# - BOT_TOKEN — токен бота от @BotFather
# - LLM_API_KEY — API-ключ LLM (если бот использует генерацию текста/анализ через LLM)
```

**Где взять токены:**
- **BOT_TOKEN** — [@BotFather](https://t.me/BotFather) в Telegram (`/newbot` или `/token`).
- **LLM_API_KEY** — у провайдера LLM (например, [OpenAI API keys](https://platform.openai.com/api-keys)). Загружается в `.env` и читается в коде через `bot.config.settings.LLM_API_KEY`.

**Email для запросов «Нужна помощь»** — чтобы письма отправлялись на vershinina.katya@gmail.com, добавьте в `.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=vershinina.katya@gmail.com
SMTP_PASSWORD=пароль_приложения_google
```
Для Gmail нужен [пароль приложения](https://support.google.com/accounts/answer/185833), не обычный пароль.

## Запуск

```bash
python run.py
```

## Структура проекта

```
.
├── README.md              # Документация проекта
├── requirements.txt       # Зависимости Python
├── .env.example          # Пример файла с переменными окружения
├── .gitignore           # Игнорируемые файлы Git
├── run.py               # Точка входа для запуска бота
├── docs/                # Документация продукта
│   ├── README.md        # Описание документации
│   ├── PRODUCT_DESCRIPTION.md  # Описание продукта
│   ├── FEATURES.md      # Функциональность
│   ├── USER_GUIDE.md    # Руководство пользователя
│   ├── ARCHITECTURE.md  # Архитектура приложения
│   └── API.md           # API документация
└── bot/                 # Код разработки приложения
    ├── __init__.py
    ├── main.py          # Главный файл запуска бота
    ├── config/          # Конфигурационные файлы
    │   ├── __init__.py
    │   └── settings.py  # Настройки приложения
    ├── handlers/        # Обработчики команд и сообщений
    │   ├── __init__.py
    │   ├── commands.py  # Обработчики команд
    │   └── messages.py  # Обработчики сообщений
    └── utils/           # Вспомогательные функции
        ├── __init__.py
        ├── logger.py    # Настройка логирования
        └── helpers.py   # Вспомогательные функции
```

## Документация

Подробная документация проекта находится в папке `docs/`:
- **PRODUCT_DESCRIPTION.md** - Описание продукта и целевой аудитории
- **FEATURES.md** - Список функций и возможностей
- **USER_GUIDE.md** - Руководство пользователя
- **ARCHITECTURE.md** - Архитектура и структура кода
- **API.md** - Документация API

## Разработка

### Добавление новых команд

Команды добавляются в файл `bot/handlers/commands.py`.

### Добавление обработчиков сообщений

Обработчики сообщений добавляются в файл `bot/handlers/messages.py`.

### Структура разработки

Весь код разработки находится в папке `bot/`:
- `bot/main.py` - точка входа приложения
- `bot/config/` - конфигурация и настройки
- `bot/handlers/` - обработчики событий
- `bot/utils/` - утилиты и вспомогательные функции

## Лицензия

[Укажите лицензию]

## Контакты

[Ваши контакты]
#########