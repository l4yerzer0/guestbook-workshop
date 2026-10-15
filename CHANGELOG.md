# Changelog

Все заметные изменения в проекте **guestbook** фиксируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
и проект придерживается [Семантического Версионирования (SemVer)](https://semver.org/lang/ru/).

---

## [Unreleased]

---

## [1.0.0] - 2026-10-15

### Added
- **Production Packaging**: упаковка сервиса в Docker с использованием официального multi-stage `uv`.
- **Docker Compose**: оркестрация FastAPI + PostgreSQL 16 Alpine с `healthcheck`, `depends_on: service_healthy` и персистентным томом `postgres_data`.
- **Config & Secrets**: вынос конфигурации в `pydantic-settings` с загрузкой из переменных окружения и `.env`, шаблон `.env.example`.
- **CI Pipeline**: автоматический запуск линтера и форматтера `ruff`, а также тестов `pytest` на GitHub Actions при каждом push и PR.
- **CD Pipeline**: автоматическая сборка и публикация multi-tag образов в GitHub Container Registry (`ghcr.io`) при пуше в `main` и релизных тегах `vX.Y.Z`.
- **Documentation**: составлен `README.md` с архитектурой сервиса и `RUNBOOK.md` с регламентом эксплуатации и процедурой отката (Rollback).

### Security
- Удалены захардкоженные пароли из исходного кода.
- Файлы секретов `.env` исключены из системы контроля версий и сборки контейнеров (`.gitignore`, `.dockerignore`).
- Порт базы данных закрыт от внешней сети хоста и доступен только внутри Docker-сети приложения.
