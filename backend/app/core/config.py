import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development", description="Environment mode: development, test, or production")
    HOST: str = Field(default="127.0.0.1", description="Server bind host")
    PORT: int = Field(default=8000, description="Server bind port")
    DATABASE_URL: str = Field(default="sqlite:///./signal_studio.db", description="Database connection URL")
    SECRET_KEY: str = Field(default="signal-studio-secret-key-alan-vo-2026", description="Secret key for signing tokens")
    
    # Authentication & OIDC Settings
    AUTH_DEMO_MODE: bool = Field(default=True, description="Enable local-only demo mode for development")
    OIDC_ISSUER_URL: str = Field(default="http://127.0.0.1:8080/realms/signal-studio", description="OIDC Issuer URL")
    OIDC_CLIENT_ID: str = Field(default="signal-studio-app", description="OIDC Client ID")
    OIDC_CLIENT_SECRET: Optional[str] = Field(default=None, description="Optional OIDC Client Secret")
    OIDC_AUDIENCE: str = Field(default="signal-studio-app", description="OIDC Token Audience")

    # LLM Gateway Configuration
    LLM_API_KEY: Optional[str] = Field(default=None, description="Sole credential variable for LLM providers")
    LLM_PROVIDER: str = Field(default="openai-compatible", description="Provider adapter: openai-compatible, anthropic, gemini, ollama")
    LLM_MODEL: str = Field(default="gpt-4o-mini", description="Configured model identifier")
    LLM_BASE_URL: Optional[str] = Field(default=None, description="Optional base URL for OpenAI-compatible/Ollama endpoints")
    LLM_TIMEOUT_SECONDS: float = Field(default=30.0, description="HTTP request timeout for LLM gateway")

    @field_validator("AUTH_DEMO_MODE")
    @classmethod
    def validate_demo_mode_safety(cls, v: bool, info) -> bool:
        env = os.getenv("ENVIRONMENT", "development").lower()
        if v and env == "production":
            raise ValueError("SECURITY VIOLATION: AUTH_DEMO_MODE cannot be enabled in production environment.")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()


def verify_startup_safety():
    if settings.AUTH_DEMO_MODE and settings.ENVIRONMENT.lower() == "production":
        raise RuntimeError("Startup refused: AUTH_DEMO_MODE is forbidden when ENVIRONMENT=production")
    if settings.AUTH_DEMO_MODE and settings.HOST not in ("127.0.0.1", "localhost", "0.0.0.0"):
        raise RuntimeError("Startup refused: AUTH_DEMO_MODE must bind localhost only")
