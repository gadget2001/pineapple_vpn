from app.core.config import settings
from app.schemas.subscription import SubscriptionPlan


PLAN_TITLES = {
    "week": "Неделя",
    "month": "Месяц",
}

PLAN_DAYS = {
    "week": 7,
    "month": 30,
}


def plan_prices() -> dict[str, int]:
    return {
        "week": settings.subscription_price_week_rub,
        "month": settings.subscription_price_month_rub,
    }


def available_plans() -> list[SubscriptionPlan]:
    prices = plan_prices()
    return [
        SubscriptionPlan(
            code="week",
            title=PLAN_TITLES["week"],
            price_rub=prices["week"],
            duration_days=PLAN_DAYS["week"],
        ),
        SubscriptionPlan(
            code="month",
            title=PLAN_TITLES["month"],
            price_rub=prices["month"],
            duration_days=PLAN_DAYS["month"],
        ),
    ]


def plans_text() -> str:
    prices = plan_prices()
    return (
        "Тарифы Pineapple VPN:\n"
        f"• {PLAN_TITLES['week']} — {prices['week']} ₽\n"
        f"• {PLAN_TITLES['month']} — {prices['month']} ₽"
    )
