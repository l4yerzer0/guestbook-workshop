# 📒 Guestbook Service

[![CI/CD Pipeline](https://github.com/l4yerzer0/guestbook-workshop/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/l4yerzer0/guestbook-workshop/actions/workflows/ci-cd.yml)
[![Docker Image](https://img.shields.io/badge/GHCR-guestbook--workshop-blue?logo=docker)](https://github.com/l4yerzer0/guestbook-workshop/pkgs/container/guestbook-workshop)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Надёжный production-ready сервис гостевой книги на **FastAPI** и **PostgreSQL**, упакованный в Docker с настроенным CI/CD конвейером, автоматическим версионированием, персистентным хранилищем и процедурой безаварийного отката (Zero-Downtime Rollback).

---

## 🛠 Технологический стек

- **Бэкенд:** Python 3.12, FastAPI, Psycopg 3, Pydantic Settings
- **Управление зависимостями:** [uv](https://github.com/astral-sh/uv) (`pyproject.toml` + `uv.lock`)
- **База данных:** PostgreSQL 16 Alpine
- **Контейнеризация:** Docker (Multi-stage layer caching), Docker Compose
- **Качество кода:** Ruff (Linter & Formatter), Pytest, HTTPX
- **CI/CD:** GitHub Actions (автоматический линтинг, тесты с сервисным контейнером БД, сборка и публикация в GitHub Container Registry `ghcr.io`)
- **Документация:** [RUNBOOK.md](RUNBOOK.md) (аварийные регламенты и откат), [CHANGELOG.md](CHANGELOG.md) (SemVer)

---

## 🚀 Быстрый запуск

### 1. Клонирование и настройка окружения
```bash
git clone https://github.com/l4yerzer0/guestbook-workshop.git
cd guestbook-workshop

# Создать локальный .env из шаблона
cp .env.example .env
```

### 2. Запуск через Docker Compose
```bash
# Собрать и запустить сервис и базу данных в фоновом режиме
docker compose up -d --build

# Проверить статус контейнеров
docker compose ps
```

Сервис будет доступен по адресу `http://localhost:8000`.

---

## 📡 API Эндпоинты

| Метод | Путь | Описание | Пример ответа / Тела |
|---|---|---|---|
| `GET` | `/` | Приветственное сообщение | `{"message": "Добро пожаловать в гостевую книгу!"}` |
| `GET` | `/health` | Проверка жизнеспособности сервиса | `{"status": "ok"}` |
| `GET` | `/messages` | Список сообщений (новые сверху) | `[{"author": "Alice", "text": "Привет!"}]` |
| `POST` | `/messages` | Добавить новое сообщение | `{"author": "Bob", "text": "Текст сообщения"}` |

### Примеры запросов:
```bash
# Проверить здоровье
curl http://localhost:8000/health

# Оставить запись
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d '{"author": "DevOps Lead", "text": "Production ready!"}'

# Посмотреть записи
curl http://localhost:8000/messages
```

---

## 🧪 Локальная разработка и тесты

Для управления локальным окружением используется утилита `uv`:

```bash
# Установить зависимости, включая dev-инструменты
uv sync

# Запуск линтера и проверка форматирования
uv run ruff check .
uv run ruff format --check .

# Запуск тестов
uv run pytest -v
```

---

## 🔄 CI/CD Конвейер и релизы

В проекте настроен автоматический пайплайн в [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml):

1. **CI (`check`)**: запускается на каждый `push` и `pull_request`:
   - Запускает сервис PostgreSQL 16.
   - Проверяет код с помощью `ruff check` и `ruff format --check`.
   - Прогоняет полный набор тестов `pytest`.
2. **CD (`build-and-push`)**: срабатывает **только после успешного CI** (`needs: check`):
   - При пуше в ветку `main` собирает Docker-образ и публикует в `ghcr.io` с тегом `:latest` и `:sha`.
   - При создании тега версии вида `vX.Y.Z` (SemVer) собирает релизный образ с тегом `vX.Y.Z`.

---

## 📖 Эксплуатация и регламенты

Подробные инструкции по диагностике, мониторингу, плановому выкату и экстренному откату версий (Rollback) описаны в **[RUNBOOK.md](RUNBOOK.md)**.
История изменений версий ведётся в **[CHANGELOG.md](CHANGELOG.md)**.
