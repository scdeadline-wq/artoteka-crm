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

    # Telegram
    telegram_bot_token: str = ""

    model_config = {"env_file": "../../.env", "extra": "ignore"}


settings = Settings()
