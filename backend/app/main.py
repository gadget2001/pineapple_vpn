from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import admin, auth, payments, referral, subscriptions, users, vpn, webhooks
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware

app = FastAPI(
    title=settings.project_name,
    description=(
        "Pineapple VPN API. Telegram MiniApp backend with wallet top-up, "
        "trial activation, subscriptions, referrals, and VPN profile issuance via Marzban."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "Auth", "description": "Telegram MiniApp authorization"},
        {"name": "Users", "description": "Profile, dashboard and devices"},
        {"name": "Subscriptions", "description": "Trial and paid subscription management"},
        {"name": "Payments", "description": "Wallet top-up and YooKassa webhook"},
        {"name": "VPN", "description": "VPN profile generation and retrieval"},
        {"name": "Referrals", "description": "Referral stats and invited users"},
        {"name": "admin", "description": "Admin metrics and lists"},
        {"name": "webhooks", "description": "System webhooks"},
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


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}


for prefix in ("", "/api"):
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(subscriptions.router, prefix=prefix)
    app.include_router(payments.router, prefix=prefix)
    app.include_router(vpn.router, prefix=prefix)
    app.include_router(referral.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(webhooks.router, prefix=prefix)