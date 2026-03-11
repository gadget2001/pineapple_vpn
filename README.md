# Pineapple VPN

Production-ready сервис защищенного удаленного доступа к российскому IP для пользователей за границей. Сервис не предназначен для обхода блокировок.

## Важно про x-ui
В текущем проекте интеграция реализована через Marzban API (контейнер `panel`).
Если у вас уже установлен x-ui, есть два пути:
1. Оставить x-ui как есть и реализовать адаптер API под x-ui (я могу добавить его по запросу).
2. Отключить/не использовать x-ui и использовать Marzban (рекомендуется для этой реализации).

Сейчас проект ожидает `PANEL_URL` и `PANEL_TOKEN` от Marzban. Для x-ui потребуется отдельная прослойка.

## Архитектура
- Backend API: FastAPI + SQLAlchemy + Alembic
- Telegram Bot: aiogram
- Telegram MiniApp: React + Telegram WebApp SDK
- VPN Panel API: Marzban (Xray-core, VLESS + Reality, XTLS Vision)
- Redis: кэш и очередь задач
- Worker: Celery worker
- Scheduler: Celery beat
- Nginx reverse proxy

## Размещение и порты
Контейнеры работают на нестандартных портах:
- backend: `18081`
- bot: `18082`
- frontend: `18083`
- redis: `16379`
- panel: `19090`

Nginx принимает 80/443 и проксирует:
- `/api` -> backend
- `/` -> frontend

## Подготовка сервера
1. Установите Docker и Docker Compose.
2. Откройте порты 80/443 и убедитесь, что домен указывает на сервер.
3. Подготовьте внешнюю PostgreSQL (на другом сервере).

## Запуск проекта
1. Скопируйте `.env.example` в `.env`.
2. Заполните `.env`.
3. Запустите:

```bash
docker compose up -d
```

4. Выполните миграции:

```bash
docker compose exec backend alembic upgrade head
```

## Настройка .env (подробно)
Пример файла находится в `.env.example`. Ниже пояснения по ключам.

### Общие
- `PROJECT_NAME` — название проекта.
- `DOMAIN` — домен, например `pineapple.ambot24.ru`.
- `APP_ENV` — `production`.

### Безопасность и JWT
- `SECRET_KEY` — произвольная строка 32+ символа.
- `JWT_SECRET` — отдельный секрет для JWT.
- `JWT_ALG` — `HS256`.
- `ACCESS_TOKEN_EXPIRE_MINUTES` — срок жизни токена (минуты).

### CORS и URL
- `ALLOWED_ORIGINS` — список доменов через запятую.
- `FRONTEND_URL` — публичный URL фронтенда.
- `API_BASE_URL` — публичный URL API.

### PostgreSQL (внешняя)
- `DB_HOST` — хост БД.
- `DB_PORT` — порт БД.
- `DB_NAME` — имя БД.
- `DB_USER` — пользователь.
- `DB_PASSWORD` — пароль.

### Redis
- `REDIS_URL` — `redis://redis:16379/0`.

### Telegram
- `BOT_TOKEN` — токен Telegram-бота.
- `ADMIN_CHAT_ID` — ID чата для логов.
- `TELEGRAM_MINIAPP_URL` — URL MiniApp.

### YooKassa
- `YOOKASSA_SHOP_ID` — ID магазина.
- `YOOKASSA_SECRET_KEY` — секретный ключ.
- `YOOKASSA_WEBHOOK_SECRET` — секрет для подписи webhook.

### VPN Panel (Marzban)
- `PANEL_URL` — URL панели (например `http://panel:19090`).
- `PANEL_TOKEN` — токен панели.
- `VPN_LIMIT_MBPS` — лимит скорости на пользователя.
- `VPN_MAX_CONNECTIONS` — лимит одновременных подключений.

### Webhook
- `WEBHOOK_BASE_URL` — публичный URL сервера.
- `WEBHOOK_PATH` — `/api/payments/webhook`.

## Настройка Telegram Bot и MiniApp
1. Создайте бота через @BotFather и получите `BOT_TOKEN`.
2. Включите WebApp URL, укажите `TELEGRAM_MINIAPP_URL`.
3. Создайте админ-чат и укажите его ID как `ADMIN_CHAT_ID`.

## Настройка YooKassa
1. Создайте магазин и получите `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY`.
2. В кабинете YooKassa укажите webhook на:
`https://<DOMAIN>/api/payments/webhook`
3. Секрет подписи укажите в `YOOKASSA_WEBHOOK_SECRET`.

## Настройка VPN панели
Если используете Marzban:
1. Запустите контейнер `panel`.
2. Создайте токен и укажите `PANEL_TOKEN`.
3. Убедитесь, что API доступно по `PANEL_URL`.

Если используете x-ui:
- Нужен адаптер между x-ui и backend Pineapple VPN.
- Напишите, и я добавлю x-ui интеграцию (API обертка + конфигурация).

## Админ-логирование
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

## Webhook YooKassa
Эндпоинт: `/api/payments/webhook`.
Ожидается заголовок `X-Webhook-Signature` (HMAC-SHA256 от тела запроса и секрета `YOOKASSA_WEBHOOK_SECRET`).

## Логи подключений
Сохраняются:
- Telegram ID
- IP подключения
- Время подключения
Срок хранения: 30 дней.

## Инструкции подключения
MiniApp показывает инструкции:
- Windows: NekoRay
- iPhone: Streisand

## Правовые документы
Документы находятся в `docs/`:
- `docs/terms.md`
- `docs/privacy.md`
- `docs/acceptable_use.md`
