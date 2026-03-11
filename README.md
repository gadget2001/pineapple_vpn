# Pineapple VPN

Production-ready сервис защищенного удаленного доступа к российскому IP для пользователей за границей. Сервис не предназначен для обхода блокировок.

## Важно про x-ui
В текущем проекте интеграция реализована через Marzban API (контейнер `panel` или внешний Marzban).
Если у вас уже установлен x-ui, есть два пути:
1. Оставить x-ui как есть и реализовать адаптер API под x-ui (могу добавить по запросу).
2. Использовать Marzban (рекомендуется для этой реализации).

## Архитектура
- Backend API: FastAPI + SQLAlchemy + Alembic
- Telegram Bot: aiogram
- Telegram MiniApp: React + Telegram WebApp SDK
- VPN Panel API: Marzban (Xray-core, VLESS + Reality, XTLS Vision)
- Redis: кэш и очередь задач
- Worker: Celery worker
- Scheduler: Celery beat
- Nginx reverse proxy

## Порты контейнеров
- backend: `18081`
- bot: `18082`
- frontend: `18083`
- redis: `16379`
- panel: `19090`

Nginx принимает 80/443 и проксирует:
- `/api` -> backend
- `/` -> frontend

---

# Полная инструкция по запуску

## 1) Подготовка сервера

1. Установите Docker и Docker Compose.
2. Откройте порты 80/443 и убедитесь, что домен указывает на сервер.
3. Подготовьте внешнюю PostgreSQL (на другом сервере).
4. Решите, где будет Marzban:
   - Внутри `docker-compose` (контейнер `panel`)
   - На отдельном сервере (в этом случае используйте `PANEL_URL` с внешним адресом)

## 2) Подготовка домена и SSL

1. Создайте DNS запись `pineapple.ambot24.ru` на IP сервера.
2. Выпустите SSL-сертификат (LetsEncrypt). Можно использовать отдельный Nginx/Traefik для SSL.
3. Убедитесь, что `https://pineapple.ambot24.ru` открывается.

## 3) Настройка Telegram Bot и MiniApp

1. Создайте бота через @BotFather.
2. Получите `BOT_TOKEN`.
3. Настройте WebApp URL — укажите `https://pineapple.ambot24.ru`.
4. Создайте Telegram-чат для админ-логов и получите `ADMIN_CHAT_ID`.

## 4) Настройка YooKassa

1. Создайте магазин в YooKassa.
2. Получите `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY`.
3. В кабинете YooKassa настройте webhook:
   `https://pineapple.ambot24.ru/api/payments/webhook`
4. В `YOOKASSA_WEBHOOK_SECRET` укажите секрет, которым подписывается webhook.

## 5) Настройка Marzban

Подробная инструкция находится в `docs/marzban_setup.md`.

Коротко:
1. Установите Marzban (на этом сервере или на отдельном).
2. Получите API токен через `/api/admin/token`.
3. Укажите `PANEL_URL` и `PANEL_TOKEN` в `.env` Pineapple VPN.
4. Настройте inbound VLESS + Reality + XTLS Vision в панели.

## 6) Настройка .env

Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

Заполните `.env`:

### Общие
- `PROJECT_NAME` — Pineapple VPN
- `DOMAIN` — `pineapple.ambot24.ru`
- `APP_ENV` — `production`

### Безопасность и JWT
- `SECRET_KEY` — 32+ символов
- `JWT_SECRET` — отдельный секрет
- `JWT_ALG` — `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES` — срок жизни JWT

### CORS и URL
- `ALLOWED_ORIGINS` — `https://pineapple.ambot24.ru,https://t.me`
- `FRONTEND_URL` — `https://pineapple.ambot24.ru`
- `API_BASE_URL` — `https://pineapple.ambot24.ru/api`

### PostgreSQL (внешняя)
- `DB_HOST` — хост внешней БД
- `DB_PORT` — порт БД
- `DB_NAME` — имя БД
- `DB_USER` — пользователь
- `DB_PASSWORD` — пароль

### Redis
- `REDIS_URL` — `redis://redis:16379/0`

### Telegram
- `BOT_TOKEN` — токен
- `ADMIN_CHAT_ID` — чат для логов
- `TELEGRAM_MINIAPP_URL` — `https://pineapple.ambot24.ru`

### YooKassa
- `YOOKASSA_SHOP_ID` — ID магазина
- `YOOKASSA_SECRET_KEY` — секрет
- `YOOKASSA_WEBHOOK_SECRET` — секрет webhook

### VPN Panel (Marzban)
- `PANEL_URL` — `http://panel:19090` (если Marzban в compose) или внешний URL
- `PANEL_TOKEN` — токен Marzban
- `VPN_LIMIT_MBPS` — лимит скорости
- `VPN_MAX_CONNECTIONS` — лимит соединений

### Webhook
- `WEBHOOK_BASE_URL` — `https://pineapple.ambot24.ru`
- `WEBHOOK_PATH` — `/api/payments/webhook`

## 7) Запуск проекта

```bash
docker compose up -d
```

Проверьте статус:

```bash
docker compose ps
```

## 8) Миграции базы данных

Выполните миграции Alembic:

```bash
docker compose exec backend alembic upgrade head
```

Если нужно откатить:

```bash
docker compose exec backend alembic downgrade -1
```

## 9) Проверка работоспособности

1. `https://pineapple.ambot24.ru` — открывается MiniApp (через Telegram).
2. `https://pineapple.ambot24.ru/api/health` — ответ `{ "status": "ok" }`.
3. В админ-чат приходят логи.
4. Создается платеж YooKassa и проходит webhook.
5. Marzban создает пользователей и возвращает VLESS/Subscription URL.

## 10) Логи и обслуживание

- Логи контейнеров:

```bash
docker compose logs -f backend
```

- Очистка логов подключений старше 30 дней выполняется scheduler.

## 11) Структура проекта

```
vpn-service/
  backend/
  bot/
  frontend/
  worker/
  scheduler/
  nginx/
  docker/
  docs/
```

## 12) Админ-логирование

Все действия пользователей отправляются в Telegram-чат `ADMIN_CHAT_ID` с тегами:
- `#user_<telegram_id>`
- `#action`

Пример:
```
[ Pineapple VPN LOG ]

Новое событие: регистрация пользователя

User ID: 123456789
Username: @example
Trial: активирован
Дата: 2026-03-11

#user_123456789
#registration
```

## 13) Webhook YooKassa

Эндпоинт: `/api/payments/webhook`.
Ожидается заголовок `X-Webhook-Signature` (HMAC-SHA256 от тела запроса и секрета `YOOKASSA_WEBHOOK_SECRET`).

## 14) Правовые документы

Документы находятся в `docs/`:
- `docs/terms.md`
- `docs/privacy.md`
- `docs/acceptable_use.md`

## 15) Дополнительно

Если нужен адаптер под x-ui, напишите — добавлю сервис и настройки.
