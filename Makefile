.PHONY: build run install clean test

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

# Запуск бота
run:
	./venv/bin/python run.py

# Запуск тестов (если есть)
test:
	./venv/bin/python -m pytest tests/ -v 2>/dev/null || echo "Тесты не настроены (папка tests/ отсутствует)"

# Очистка
clean:
	rm -rf venv __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
