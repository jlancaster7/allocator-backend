"""Application configuration module"""

import os
from datetime import timedelta
from typing import Optional
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings"""
    
    # Flask settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG: bool = os.getenv("FLASK_ENV", "development") == "development"
    
    # API settings
    API_V1_STR: str = "/v1"
    PROJECT_NAME: str = "Order Allocation System"
    
    # JWT settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    JWT_ALGORITHM: str = "HS256"
    
    # Aladdin API settings
    ALADDIN_BASE_URL: str = os.getenv("ALADDIN_BASE_URL", "https://api.blackrock.com/api")
    ALADDIN_CLIENT_ID: str = os.getenv("ALADDIN_CLIENT_ID", "")
    ALADDIN_CLIENT_SECRET: str = os.getenv("ALADDIN_CLIENT_SECRET", "")
    ALADDIN_OAUTH_TOKEN_URL: str = os.getenv("ALADDIN_OAUTH_TOKEN_URL", "https://api.blackrock.com/oauth/token")
    ALADDIN_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("ALADDIN_RATE_LIMIT_PER_MINUTE", 100))
    
    # Mock data settings
    MOCK_ALADDIN_DATA: str = os.getenv("MOCK_ALADDIN_DATA", "true" if not os.getenv("ALADDIN_CLIENT_ID") else "false")
    MOCK_DATA_SCENARIO: str = os.getenv("MOCK_DATA_SCENARIO", "default")
    MOCK_DATA_SEED: int = int(os.getenv("MOCK_DATA_SEED", 42))
    
    # Snowflake settings (required for audit trail and historical data)
    SNOWFLAKE_ACCOUNT: str = os.getenv("SNOWFLAKE_ACCOUNT", "")
    SNOWFLAKE_USER: str = os.getenv("SNOWFLAKE_USER", "")
    SNOWFLAKE_PASSWORD: str = os.getenv("SNOWFLAKE_PASSWORD", "")
    SNOWFLAKE_WAREHOUSE: str = os.getenv("SNOWFLAKE_WAREHOUSE", "")
    SNOWFLAKE_DATABASE: str = os.getenv("SNOWFLAKE_DATABASE", "ALLOCATIONS_DB")
    SNOWFLAKE_SCHEMA: str = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
    
    # Database URL
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"snowflake://{self.SNOWFLAKE_USER}:{self.SNOWFLAKE_PASSWORD}@"
            f"{self.SNOWFLAKE_ACCOUNT}/{self.SNOWFLAKE_DATABASE}/{self.SNOWFLAKE_SCHEMA}"
            f"?warehouse={self.SNOWFLAKE_WAREHOUSE}"
        )
    
    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Celery settings
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    
    # Cache settings
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", 300))
    CACHE_TTL_TRADING_HOURS_SECONDS: int = int(os.getenv("CACHE_TTL_TRADING_HOURS_SECONDS", 300))
    
    # Allocation constraints
    DEFAULT_MIN_ALLOCATION: float = 1000.0
    DEFAULT_MIN_DENOMINATION: float = 1000.0
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    
    # CORS settings
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]
    
    # Request timeout settings
    REQUEST_TIMEOUT: int = 120  # seconds
    ALADDIN_REQUEST_TIMEOUT: int = 60  # seconds
    
    # Retry settings
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_BACKOFF_FACTOR: float = 2.0
    RETRY_MAX_WAIT: int = 60  # seconds


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()