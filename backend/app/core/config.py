from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PayKotha Core Banking"
    app_env: str = "development"
    secret_key: str = "paykotha-dev-secret-change-in-production-32chars"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Use Postgres in production: postgresql+psycopg2://paykotha:paykotha@db:5432/paykotha
    database_url: str = "sqlite:///./data/paykotha.db"
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cash_out_fee_rate: float = 0.018
    send_fee_rate: float = 0.0
    excel_export_dir: str = "./data/exports"

    # Bank-grade controls
    otp_ttl_seconds: int = 120
    otp_length: int = 6
    max_failed_pin_attempts: int = 5
    lockout_minutes: int = 30
    high_value_threshold: float = 10000.0
    require_otp_above: float = 5000.0
    rail_mode: str = "sandbox"  # sandbox | mock_npsb
    admin_bootstrap_phone: str = "01999999999"
    admin_bootstrap_pin: str = "999999"
    # Seed Alice/Bob + ops maker-checker on boot (portfolio demos / Render)
    seed_demo: bool = True

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
