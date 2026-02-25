.PHONY: build run install clean test stop restart status

# По умолчанию — build
all: build

# Build: venv + зависимости + проверка импорта
build:
	@echo "==> Создание venv..."
	python3 -m venv venv
	@echo "==> Установка зависимостей..."
	./venv/bin/pip install -q -r requirements.txt
	@echo "==> Проверка импорта бота..."
	./venv/bin/python -c "from bot.main import main; print('OK: build успешен')"
	@echo "==> Build завершён."

# Установка зависимостей (если venv уже есть)
install:
	./venv/bin/pip install -q -r requirements.txt

# Остановить бота (принудительно)
stop:
	@echo "==> Остановка бота..."
	@pkill -9 -f "python run.py" 2>/dev/null || true
	@pkill -9 -f "run.py" 2>/dev/null || true
	@sleep 2
	@echo "Бот остановлен."

# Статус: запущен ли бот
status:
	@pgrep -f "run.py" >/dev/null 2>&1 && echo "Бот запущен (PID: $$(pgrep -f 'run.py' | tr '\n' ' ')). Остановить: make stop" || echo "Бот не запущен"

# Перезапуск: остановить + запустить
restart: stop
	@sleep 3
	@$(MAKE) run

# Запуск бота (всегда один экземпляр: останавливает старые, запускает новый)
run:
	@pkill -9 -f "python run.py" 2>/dev/null || true
	@pkill -9 -f "run.py" 2>/dev/null || true
	@sleep 3
	@./venv/bin/python run.py

# Запуск тестов (если есть)
test:
	./venv/bin/python -m pytest tests/ -v 2>/dev/null || echo "Тесты не настроены (папка tests/ отсутствует)"

# Очистка
clean:
	rm -rf venv __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
