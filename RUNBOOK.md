# 🚨 RUNBOOK — Эксплуатация и аварийные инструкции: guestbook

Настоящий документ является операционным руководством для дежурного инженера по сопровождению сервиса **guestbook**.

---

## 1. Архитектура и компоненты

| Компонент | Образ / Стек | Порт (внутр.) | Порт (внешн.) | Назначение |
|---|---|---|---|---|
| **app** | `ghcr.io/l4yerzer0/guestbook-workshop:${IMAGE_TAG}` | 8000 | 8000 | FastAPI REST API |
| **db** | `postgres:16-alpine` | 5432 | *закрыт* | СУБД (PostgreSQL) |
| **prometheus** | `prom/prometheus:v2.54.1` | 9090 | 9090 | Сбор и хранение метрик, вычисление алертов |
| **alertmanager** | `prom/alertmanager:v0.27.0` | 9093 | 9093 | Маршрутизация и доставка алертов |
| **grafana** | `grafana/grafana:11.1.0` | 3000 | 3000 | Визуализация (RED-дашборд) |
| **volume** | `postgres_data` | — | — | Персистентное хранилище БД (`/var/lib/postgresql/data`) |
| **volume** | `grafana_data` | — | — | Персистентное хранилище Grafana |

---

## 2. Мониторинг, Healthcheck и алертинг

- **Liveness probe приложения (быстрая проверка процесса):**
  ```bash
  curl -fsS http://localhost:8000/health || echo "APP IS DOWN"
  ```
  *Ожидаемый ответ:* `{"status": "ok"}` с кодом `200`.

- **Readiness probe приложения (проверка подключения к БД):**
  ```bash
  curl -i http://localhost:8000/ready
  ```
  *При рабочей БД:* HTTP 200 `{"status": "ok"}`.
  *При отключенной БД:* HTTP 503 `{"status": "unavailable", "detail": "Database connection failed"}`.

- **RED-метрики приложения:**
  ```bash
  curl http://localhost:8000/metrics
  ```

- **Панели и UI мониторинга:**
  - Prometheus: `http://localhost:9090` (проверка состояния target в `Status -> Targets`, алертов в `Alerts`).
  - Alertmanager: `http://localhost:9093` (активные алерты).
  - Grafana: `http://localhost:3000` (логин/пароль: `admin` / `admin`, автонастроенный RED-дашборд).

- **Нагрузочное тестирование (k6) для проверки алертинга:**
  ```bash
  # Запуск локально через k6 или Docker-контейнер
  k6 run load-test.js
  # или через Docker:
  docker run --rm -i --network=host grafana/k6 run - < load-test.js
  ```
  Нагрузка вызывает срабатывание правила `HighRequestRate` (переход в `firing`), Alertmanager отправляет вебхук на `/alerts/webhook`, а сервис регистрирует событие `alert_received` в логах.

- **Проверка статуса контейнеров в Docker:**
  ```bash
  docker compose ps
  ```
  *Все 5 сервисов обязаны находиться в статусе `Up` (`healthy` для `db`).*

---

## 3. Регламент планового обновления (Deploy)

Для развертывания новой версии сервиса используется переменная `IMAGE_TAG`:

```bash
# 1. Скачать новый образ релиза
IMAGE_TAG=v1.1.0 docker compose pull app

# 2. Перезапустить контейнер приложения с новой версией
IMAGE_TAG=v1.1.0 docker compose up -d app

# 3. Убедиться, что сервис поднялся и здоров
docker compose ps
curl -fsS http://localhost:8000/health
```

---

## 4. Регламент экстренного отката (Rollback Procedure)

### Критерии инициации отката
- Резкий рост ошибок HTTP 5xx (> 1% запросов).
- Эндпоинт `/health` не отвечает или возвращает ошибку более 30 секунд.
- Приложение падает с циклом перезапусков (`CrashLoopBackOff` / `restarting`).

### Пошаговые действия для отката
При возникновении аварии немедленно переключаем сервис на предыдущий стабильный тег:

```bash
# Шаг 1. Перезапуск приложения на предыдущую проверенную версию (например, v1.0.0)
IMAGE_TAG=v1.0.0 docker compose up -d --no-deps app

# Шаг 2. Контроль логов старта приложения
docker compose logs --tail=50 -f app

# Шаг 3. Контрольная валидация работоспособности API
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/messages
```

---

## 5. Обратная совместимость схемы БД (Zero-Downtime Rollback)

### Почему откат приложения безопасен для данных?
В архитектуре сервиса применяется паттерн **Expand and Contract (Разделяй и властвуй)**:
1. **Любые изменения схемы аддитивны:** новые колонки создаются со значениями по умолчанию (`DEFAULT`) или допускают `NULL`.
2. **Колонки и таблицы никогда не удаляются и не переименовываются в один шаг.**
3. **Старый код игнорирует новые поля:** если версия `v1.1.0` добавила в таблицу `messages` колонку (например, `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`), то при откате на версию `v1.0.0` старый запрос `INSERT INTO messages (author, text) VALUES (%s, %s)` **не падает**, так как Postgres автоматически подставляет дефолтное значение для новой колонки. Запрос `SELECT author, text FROM messages` также выбирает только явно запрошенные поля и игнорирует добавленные.

---

## 6. Траблшутинг и частые инциденты

### Инцидент 1: Контейнер `app` не стартует (`waiting for db`)
- **Причина:** Postgres ещё не прошёл проверку `pg_isready` или база упала.
- **Диагностика:**
  ```bash
  docker compose logs db
  ```
- **Лечение:** Проверьте переменные авторизации `POSTGRES_USER` и `POSTGRES_PASSWORD` в `.env`.

### Инцидент 2: Сообщения пропали после перезапуска
- **Причина:** Был выполнен `docker compose down -v` (ключ `-v` удаляет тома).
- **Правило:** При плановых перезапусках и деплоях **запрещено** использовать флаг `-v`! Используйте обычный `docker compose down` или `docker compose restart`.
