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
    legal_docs_version: str = "2026-03-15"

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
    yookassa_webhook_ips: str = (
        "185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,77.75.156.11,"
        "77.75.156.35,77.75.154.128/25,2a02:5180::/32"
    )
    yookassa_receipt_description: str = "Пополнение баланса Pineapple VPN"
    yookassa_receipt_vat_code: int = 1
    yookassa_receipt_payment_mode: str = "full_prepayment"
    yookassa_receipt_payment_subject: str = "service"

    panel_url: str
    panel_token: str = ""
    panel_username: str = ""
    panel_password: str = ""
    panel_inbound_name: str = "VLESS TCP REALITY"
    vpn_limit_mbps: int = 50
    vpn_max_connections: int = 2
    vpn_daily_data_limit_gb: int = 40
    vpn_daily_limit_alerts_enabled: bool = True
    vpn_connection_name_template: str = "🍍 Pineapple VPN ({username})"

    vpn_access_log_enabled: bool = True
    vpn_access_log_path: str = "/var/log/xray/access.log"
    vpn_access_log_cursor_key: str = "xray_access_log"
    vpn_access_log_max_lines_per_run: int = 5000
    vpn_access_log_poll_seconds: int = 120
    vpn_connection_log_retention_days: int = 30

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
