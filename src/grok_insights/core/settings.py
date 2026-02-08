"""
Core settings and configuration management using pydantic-settings.

Supports environment-based configuration with automatic type validation.
Environments: development, staging, production
"""

from typing import List
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Use .env files or direct environment variables to configure.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    APP_NAME: str = "Grok Insights Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    LOG_LEVEL: str = "INFO"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/data.db"
    DATABASE_ECHO: bool = False  # Log SQL queries
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Grok Analysis
    GROK_MODE: str = "mock"  # mock, real
    GROK_API_KEY: str = ""
    GROK_API_BASE_URL: str = "https://api.x.ai/v1"
    GROK_MODEL: str = "grok-1"
    GROK_COST_PER_1K: float = 0.002  # $ per 1000 tokens
    # HTTP & retry tuning for real Grok API
    GROK_HTTP_TIMEOUT: float = 30.0  # per-request timeout (seconds)
    GROK_MAX_RETRIES: int = 3
    GROK_RETRY_BACKOFF_BASE: float = 0.5  # base seconds for exponential backoff
    GROK_RETRY_MAX_JITTER: float = 0.5  # max jitter seconds added to backoff
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # Processing
    MIN_BATCH_SIZE: int = 1
    MAX_BATCH_SIZE: int = 50
    START_BATCH_SIZE: int = 5
    QUEUE_FLUSH_TIMEOUT_SECONDS: float = 1.0
    
    # Resilience
    ERROR_THRESHOLD: int = 5
    CIRCUIT_BREAKER_COOLDOWN_SECONDS: int = 10
    BACKPRESSURE_QUEUE_THRESHOLD: int = 1000
    
    # Filtering & Optimization
    ENABLE_CHEAP_PREFILTER: bool = True
    ENABLE_CACHING: bool = True
    MIN_TEXT_LENGTH: int = 20
    
    # Logging & Monitoring
    ENABLE_PROMETHEUS_METRICS: bool = True
    METRICS_PORT: int = 8001
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def database_is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Loads only once per application lifetime.
    """
    return Settings()


# Global instance for convenience
settings = get_settings()
