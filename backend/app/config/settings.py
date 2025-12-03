from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator


class Settings(BaseSettings):
    # App Configuration
    app_name: str = "Quorum API"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    mistral_api_key: str = ""

    # CORS
    cors_origins: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    # Database
    database_url: str = "sqlite:///./data/quorum.db"

    # Redis (Optional)
    redis_url: str = "redis://localhost:6379/0"
    enable_rate_limiting: bool = False

    # Security
    secret_key: str = "your-secret-key-change-in-production"

    # LiteLLM
    litellm_log_level: str = "INFO"
    litellm_telemetry: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
