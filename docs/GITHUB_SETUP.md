# Инструкция по подключению GitHub и настройке релизов

## Подключение проекта к GitHub

### Шаг 1: Создание репозитория на GitHub

1. Перейдите на [GitHub.com](https://github.com) и войдите в свой аккаунт
2. Нажмите на кнопку **"+"** в правом верхнем углу и выберите **"New repository"**
3. Заполните форму:
   - **Repository name**: `telegram-bot` (или другое название)
   - **Description**: Краткое описание вашего проекта
   - **Visibility**: Выберите Public или Private
   - **НЕ** ставьте галочки на "Add a README file", "Add .gitignore", "Choose a license" (у нас уже есть эти файлы)
4. Нажмите **"Create repository"**

### Шаг 2: Инициализация Git в локальном проекте

Откройте терминал в корне проекта и выполните:

```bash
# Инициализация Git репозитория (если еще не инициализирован)
git init

# Проверка статуса
git status
```

### Шаг 3: Добавление файлов в Git

```bash
# Добавление всех файлов
git add .

# Проверка что будет закоммичено
git status

# Создание первого коммита
git commit -m "Initial commit: Telegram bot project structure"
```

### Шаг 4: Подключение к удаленному репозиторию

```bash
# Добавление удаленного репозитория (замените YOUR_USERNAME и YOUR_REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Проверка подключения
git remote -v
```

**Альтернативный вариант через SSH:**
```bash
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git
```

### Шаг 5: Отправка кода на GitHub

```bash
# Переименование основной ветки в main (если нужно)
git branch -M main

# Отправка кода на GitHub
git push -u origin main
```

Если возникнет ошибка аутентификации, используйте Personal Access Token:
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. Выберите права: `repo`
4. Скопируйте токен и используйте его как пароль при `git push`

## Настройка релизов (Releases)

### Способ 1: Создание релиза через веб-интерфейс GitHub

1. Перейдите на страницу вашего репозитория на GitHub
2. Нажмите на **"Releases"** в правой части страницы (или перейдите по ссылке `https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/releases`)
3. Нажмите **"Create a new release"**
4. Заполните форму:
   - **Choose a tag**: Создайте новый тег, например `v1.0.0`
   - **Release title**: `Release v1.0.0` или другое название
   - **Describe this release**: Описание изменений в релизе
5. Нажмите **"Publish release"**

### Способ 2: Создание релиза через Git теги

```bash
# Создание аннотированного тега
git tag -a v1.0.0 -m "Release version 1.0.0"

# Отправка тега на GitHub
git push origin v1.0.0

# Или отправить все теги сразу
git push origin --tags
```

После этого на GitHub:
1. Перейдите в **Releases**
2. Нажмите **"Draft a new release"**
3. Выберите созданный тег из выпадающего списка
4. Заполните описание и опубликуйте

### Способ 3: Автоматизация через GitHub Actions

Создайте файл `.github/workflows/release.yml` для автоматического создания релизов:

```yaml
name: Create Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          body: |
            Автоматический релиз версии ${{ github.ref }}
            
            ## Изменения
            - [Добавьте описание изменений]
          draft: false
          prerelease: false
```

## Рекомендации по версионированию

Используйте [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Несовместимые изменения API
- **MINOR** (0.1.0): Новая функциональность с обратной совместимостью
- **PATCH** (0.0.1): Исправления ошибок с обратной совместимостью

Примеры тегов:
- `v1.0.0` - Первый стабильный релиз
- `v1.1.0` - Добавлена новая функция
- `v1.1.1` - Исправление бага
- `v2.0.0` - Крупное обновление с несовместимыми изменениями

## Шаблон описания релиза

```markdown
## 🎉 Release v1.0.0

### ✨ Новые возможности
- Добавлена команда /start
- Добавлена команда /help
- Обработка текстовых сообщений

### 🐛 Исправления
- Исправлена ошибка в обработке команд

### 📝 Изменения
- Обновлена структура проекта
- Добавлена документация

### 📦 Установка
```bash
pip install -r requirements.txt
python run.py
```
```

## Полезные команды Git

```bash
# Просмотр истории коммитов
git log --oneline

# Просмотр всех тегов
git tag

# Удаление тега (локально)
git tag -d v1.0.0

# Удаление тега (на GitHub)
git push origin --delete v1.0.0

# Просмотр информации о теге
git show v1.0.0

# Создание ветки для релиза
git checkout -b release/v1.0.0
```

## Настройка GitHub Actions для автоматических релизов

Для более продвинутой автоматизации создайте `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests (если есть)
        run: |
          # pytest или другие тесты
          echo "Tests passed"
      
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            requirements.txt
          body: |
            ## 🚀 Release ${{ github.ref_name }}
            
            Автоматически созданный релиз.
            
            ### 📦 Установка
            ```bash
            pip install -r requirements.txt
            python run.py
            ```
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Дополнительные настройки репозитория

### Добавление описания и тегов

1. Перейдите в **Settings** репозитория
2. В разделе **General** добавьте:
   - **Description**: Краткое описание проекта
   - **Topics**: Теги для поиска (например: `telegram`, `bot`, `python`, `telegram-bot`)

### Настройка веток по умолчанию

1. **Settings** → **Branches**
2. Установите `main` как ветку по умолчанию
3. Настройте правила защиты веток (опционально)

### Добавление файла LICENSE

Создайте файл `LICENSE` в корне проекта с выбранной лицензией (MIT, Apache 2.0, GPL и т.д.)

## Проверка подключения

После настройки проверьте:

```bash
# Проверка удаленного репозитория
git remote -v

# Проверка статуса
git status

# Просмотр веток
git branch -a

# Просмотр тегов
git tag -l
```

## Полезные ссылки

- [GitHub Docs](https://docs.github.com/)
- [Git Documentation](https://git-scm.com/doc)
- [Semantic Versioning](https://semver.org/)
- [GitHub Releases Guide](https://docs.github.com/en/repositories/releasing-projects-on-github)
