from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import admin, auth, payments, referral, subscriptions, users, vpn, webhooks
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware

app = FastAPI(
    title=settings.project_name,
    description=(
        "API сервиса Pineapple VPN для Telegram MiniApp.\n\n"
        "Рекомендуемый сценарий работы клиента:\n"
        "1) Авторизация через Telegram MiniApp (`/auth/telegram`).\n"
        "2) Проверка профиля и состояния (`/users/overview`, `/subscriptions/status`).\n"
        "3) Активация trial вручную (`/subscriptions/trial/activate`) "
        "или пополнение кошелька (`/payments/topup`) и покупка тарифа (`/subscriptions/purchase`).\n"
        "4) Получение VPN-конфига (`/vpn/config`) после активной подписки.\n\n"
        "Важно: сервис предназначен для защищенного удаленного доступа к российским сервисам из-за границы. "
        "Сервис не предназначен для противоправной деятельности."
    ),
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    openapi_tags=[
        {"name": "Auth", "description": "Авторизация пользователя через Telegram MiniApp"},
        {"name": "Users", "description": "Профиль, обзор кабинета и устройства пользователя"},
        {"name": "Subscriptions", "description": "Пробный период, статусы и покупка подписки"},
        {"name": "Payments", "description": "Пополнение кошелька и webhook ЮKassa"},
        {"name": "VPN", "description": "Выдача и получение VPN-конфигурации через Marzban"},
        {"name": "Referrals", "description": "Реферальная система и статистика приглашений"},
        {"name": "admin", "description": "Админ-эндпоинты: метрики, списки пользователей и платежей"},
        {"name": "webhooks", "description": "Внутренние системные webhook-эндпоинты"},
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
    app.include_router(users.router, prefix=prefix)
    app.include_router(subscriptions.router, prefix=prefix)
    app.include_router(payments.router, prefix=prefix)
    app.include_router(vpn.router, prefix=prefix)
    app.include_router(referral.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(webhooks.router, prefix=prefix)
