"""
Configuration management using Pydantic Settings.
Loads environment variables from .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    # Primary model (will try fallbacks automatically if not available)
    # For PDF support via vision API, prefer: gpt-4o-mini, gpt-4o, gpt-4-turbo
    OPENAI_MODEL: str = "gpt-4.1-mini"  # Available models: gpt-4.1-mini, gpt-4.1
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Upstash Vector
    UPSTASH_VECTOR_REST_URL: Optional[str] = None
    UPSTASH_VECTOR_REST_TOKEN: Optional[str] = None
    UPSTASH_VECTOR_NAMESPACE: str = "swe-test-godwin-j"

    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: Optional[str] = None  # Should use prefix: swe-test-godwin-j

    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"


# Global settings instance
# Note: Only DATABASE_URL is required for Alembic migrations
# Other settings are optional and will be validated when actually used
settings = Settings()

