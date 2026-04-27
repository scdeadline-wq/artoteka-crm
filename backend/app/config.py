from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://artoteka:artoteka_secret@localhost:5432/artoteka"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # S3 / MinIO
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "artoteka"
    s3_secret_key: str = "artoteka_secret"
    s3_bucket: str = "artoteka-images"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # AI (OpenRouter)
    openrouter_api_key: str = ""
    ai_model: str = "google/gemini-2.0-flash-001"
    mockup_model: str = "openai/gpt-5-image"

    # Web search (SearchAPI.io — Yandex reverse image)
    searchapi_key: str = ""
    public_base_url: str = "http://185.152.94.51:8000"

    # Telegram
    telegram_bot_token: str = ""

    model_config = {"env_file": "../../.env", "extra": "ignore"}


settings = Settings()
