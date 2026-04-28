from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    telegram_bot_token: str = ""
    allowed_telegram_ids: str = ""

    crm_base_url: str = "http://backend:8000"
    # Публичный URL CRM (для Telegram — он сам качает фото по URL)
    crm_public_url: str = "http://185.152.94.51:8000"
    crm_user_email: str = ""
    crm_user_password: str = ""

    # OpenRouter (тот же что у backend): Claude для текста, gpt-audio для голоса
    openrouter_api_key: str = ""
    parse_model: str = "anthropic/claude-sonnet-4.6"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def allowed_ids(self) -> set[int]:
        if not self.allowed_telegram_ids:
            return set()
        return {int(x.strip()) for x in self.allowed_telegram_ids.split(",") if x.strip()}


settings = BotSettings()
