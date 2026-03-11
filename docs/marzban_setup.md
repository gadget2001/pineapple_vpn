# Инструкция по установке и настройке Marzban API (production)

Дата: 2026-03-11

Эта инструкция описывает установку Marzban на сервере с Ubuntu для работы с Pineapple VPN. Используется VLESS + Reality + XTLS Vision.

## 1) Варианты установки

### Вариант A (рекомендовано): официальный install-скрипт Marzban

1. Запустите установку Marzban:

```bash
sudo bash -c "$(curl -sL https://github.com/Gozargah/Marzban-scripts/raw/master/marzban.sh)" @ install
```

2. После установки:
- файлы Marzban будут в `/opt/marzban`
- данные — в `/var/lib/marzban`
- команда `marzban` будет доступна глобально

### Вариант B: собственный docker-compose
Если хотите полностью контролировать compose и конфиги — используйте собственный `docker-compose.yml` Marzban (см. документацию проекта).

## 2) SSL и домен

Панель Marzban по умолчанию доступна по HTTPS и требует домен с валидным SSL.

Рекомендуемый порядок:
1. Создайте DNS запись для домена (например `panel.pineapple.ambot24.ru`).
2. Выпустите SSL сертификат (LetsEncrypt).
3. Убедитесь, что панель доступна по `https://YOUR_DOMAIN:8000/dashboard/`.

## 3) Первичная настройка Marzban

1. Откройте панель: `https://YOUR_DOMAIN:8000/dashboard/`
2. Создайте admin пользователя.
3. Включите API docs (опционально, для тестов): в `/opt/marzban/.env` установите `DOCS=True`.

## 4) Получение API токена

Pineapple VPN использует токен Marzban для доступа к API.

1. Сгенерируйте токен через API:

```bash
curl -X POST "https://YOUR_DOMAIN:8000/api/admin/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=ADMIN_USERNAME&password=ADMIN_PASSWORD"
```

2. Ответ содержит `access_token`. Его нужно указать в `.env` проекта Pineapple VPN как `PANEL_TOKEN`.

## 5) Настройка Pineapple VPN для Marzban

В `.env` проекта Pineapple VPN:

```
PANEL_URL=https://YOUR_DOMAIN:8000
PANEL_TOKEN=ACCESS_TOKEN
VPN_LIMIT_MBPS=50
VPN_MAX_CONNECTIONS=2
```

## 6) Настройка Reality / VLESS / XTLS Vision

Настройка входящих соединений (inbounds) выполняется через Marzban dashboard:
1. Создайте inbound VLESS.
2. Включите Reality + XTLS Vision.
3. Укажите домен и параметры Reality (public key, short ID).
4. Сохраните и протестируйте подключение.

## 7) Проверка API

Проверьте доступность API:

```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  https://YOUR_DOMAIN:8000/api/users
```

## 8) Совместимость с Pineapple VPN

Pineapple VPN вызывает Marzban API для:
- создания пользователей
- выдачи VLESS ссылки
- выдачи subscription URL
- отключения пользователей

## 9) Рекомендации по безопасности

- не публикуйте API Marzban наружу без защиты
- ограничьте доступ по IP (если возможно)
- храните токен в `.env` и никогда не логируйте его
- включите резервное копирование `/var/lib/marzban`

## 10) FAQ

**Q: Можно ли использовать x-ui вместо Marzban?**
Да, но для этого нужен адаптер API. Pineapple VPN сейчас рассчитан на Marzban.

**Q: Нужно ли держать Marzban в docker, если он установлен отдельно?**
Нет. Pineapple VPN взаимодействует по HTTP API, ему важно только `PANEL_URL` и `PANEL_TOKEN`.
