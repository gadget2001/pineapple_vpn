from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    project_name: str = "Pineapple VPN"
    domain: str = "pineapple.ambot24.ru"
    app_env: str = "production"

    secret_key: str
    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 10080

    # Subscription pricing (RUB)
    subscription_price_week_rub: int = 99
    subscription_price_month_rub: int = 199

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_sslmode: str = "prefer"

    redis_url: str = "redis://redis:16379/0"

    bot_token: str
    admin_chat_id: int
    telegram_miniapp_url: str
    telegram_bot_username: str = "pineapple_AMBot"
    telegram_debug_auth: bool = False

    yookassa_shop_id: str
    yookassa_secret_key: str
    yookassa_webhook_secret: str

    panel_url: str
    panel_token: str = ""
    panel_username: str = ""
    panel_password: str = ""
    panel_inbound_name: str = "VLESS TCP REALITY"
    vpn_limit_mbps: int = 50
    vpn_max_connections: int = 2

    rate_limit_per_minute: int = 120
    frontend_url: str
    api_base_url: str
    allowed_origins: str = ""

    log_retention_days: int = 30
    sched_tz: str = "Europe/Moscow"

    webhook_base_url: str
    webhook_path: str

    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        db_name = quote_plus(self.db_name)
        return (
            f"postgresql+psycopg2://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{db_name}"
            f"?sslmode={self.db_sslmode}"
        )


settings = Settings()

