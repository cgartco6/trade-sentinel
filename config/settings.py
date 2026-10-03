import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_paper: bool = True

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    telegram_bot_token: str
    telegram_chat_id: str

    max_risk_per_trade_pct: float = 0.015
    min_rr_ratio: float = 1.5
    scan_interval_seconds: int = 60

    database_url: str = "sqlite:///./data/sentinel.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
