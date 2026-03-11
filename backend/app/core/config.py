from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    project_name: str = "Pineapple VPN"
    domain: str = "pineapple.ambot24.ru"
    app_env: str = "production"

    secret_key: str
    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 10080

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    redis_url: str = "redis://redis:16379/0"

    bot_token: str
    admin_chat_id: int
    telegram_miniapp_url: str

    yookassa_shop_id: str
    yookassa_secret_key: str
    yookassa_webhook_secret: str

    panel_url: str
    panel_token: str
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
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
