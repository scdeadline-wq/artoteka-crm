from pydantic import AliasChoices, Field
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

    # AI — MixRoute (OpenAI-совместимый). OpenRouter забанен, его переменные не читаем.
    # Модели названы LLM_*, а не AI_MODEL: старый AI_MODEL в .env содержит имя OpenRouter.
    ai_api_key: str = Field("", validation_alias=AliasChoices("MIXROUTE_API_KEY", "AI_API_KEY"))
    ai_base_url: str = "https://api.mixroute.ai/v1"
    # Пусто — напрямую. Если с сервера MixRoute не открывается: http://user:pass@host:port или socks5://...
    ai_proxy: str = ""
    ai_model: str = Field("gemini-2.5-flash", validation_alias="LLM_MODEL")
    mockup_model: str = Field("gemini-2.5-flash-image", validation_alias="LLM_MOCKUP_MODEL")

    # Web search (SearchAPI.io — Yandex reverse image)
    searchapi_key: str = ""
    public_base_url: str = "http://176.124.219.38:8000"
    # Через запятую; на проде можно переопределить CORS_ORIGINS в .env
    cors_origins: str = "http://localhost:3000,http://176.124.219.38"

    # Telegram
    telegram_bot_token: str = ""

    # Airtable (read-only импорт каталога П. Давтяна)
    airtable_token: str = ""
    airtable_base_id: str = "applZNtWrs3z6dcHy"
    airtable_artworks_table: str = "tblw8RwQZv7IMa7e5"
    airtable_artists_table: str = "tblfCU3I2nCkuQy1r"

    model_config = {"env_file": "../../.env", "extra": "ignore"}


settings = Settings()
