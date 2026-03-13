from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse

from app.api.routers import admin, auth, onboarding, payments, referral, subscriptions, users, vpn, webhooks
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware

app = FastAPI(
    title=settings.project_name,
    description=(
        "API сервиса Pineapple VPN для Telegram MiniApp.\n\n"
        "Рекомендуемый сценарий клиента:\n"
        "1) Авторизация через Telegram MiniApp (`/auth/telegram`).\n"
        "2) Прохождение мастера подключения (`/onboarding/*`).\n"
        "3) Пополнение кошелька (`/payments/topup`) и покупка тарифа (`/subscriptions/purchase`) при необходимости.\n"
        "4) Получение VPN-конфигурации (`/vpn/config` или `/onboarding/config`).\n\n"
        "Сервис предназначен для защищенного удаленного доступа к российским сервисам из-за границы "
        "и не предназначен для противоправной деятельности."
    ),
    version="1.1.0",
    servers=[
        {
            "url": "/api",
            "description": "Префикс API за reverse proxy",
        }
    ],
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    openapi_tags=[
        {"name": "Auth", "description": "Авторизация пользователя через Telegram MiniApp"},
        {"name": "Onboarding", "description": "Пошаговый мастер первого подключения VPN"},
        {"name": "Users", "description": "Профиль и обзор кабинета"},
        {"name": "Subscriptions", "description": "Trial, статусы и покупка подписки"},
        {"name": "Payments", "description": "Пополнение кошелька и webhook ЮKassa"},
        {"name": "VPN", "description": "Выдача VPN-конфигурации через Marzban"},
        {"name": "Referrals", "description": "Реферальная система и статистика приглашений"},
        {"name": "admin", "description": "Админ-эндпоинты"},
        {"name": "webhooks", "description": "Системные webhook-эндпоинты"},
    ],
)

app.add_middleware(RateLimitMiddleware)

if settings.allowed_origins:
    origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health", summary="Проверка доступности API")
def health():
    return {"status": "ok"}


@app.get("/openapi.json", include_in_schema=False)
@app.get("/api/openapi.json", include_in_schema=False)
def openapi_json():
    return JSONResponse(app.openapi())


@app.get("/docs", include_in_schema=False)
@app.get("/api/docs", include_in_schema=False)
def swagger_docs():
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title=f"{settings.project_name} API Docs",
    )


@app.get("/redoc", include_in_schema=False)
@app.get("/api/redoc", include_in_schema=False)
def redoc_docs():
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title=f"{settings.project_name} ReDoc",
    )


for prefix in ("", "/api"):
    app.include_router(auth.router, prefix=prefix)
    app.include_router(onboarding.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(subscriptions.router, prefix=prefix)
    app.include_router(payments.router, prefix=prefix)
    app.include_router(vpn.router, prefix=prefix)
    app.include_router(referral.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(webhooks.router, prefix=prefix)
