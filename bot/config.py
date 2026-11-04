from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    telegram_bot_token: str = ""
    allowed_telegram_ids: str = ""
    # Подмножество allowed_telegram_ids. Эти юзеры видят закупочную цену
    # и могут удалять работы (/delete, /trash). Назначает владелец бота.
    admin_telegram_ids: str = ""

    crm_base_url: str = "http://backend:8000"
    # Публичный URL CRM (для Telegram — он сам качает фото по URL)
    crm_public_url: str = "http://176.124.219.38:8000"
    crm_user_email: str = ""
    crm_user_password: str = ""

    # MixRoute (тот же ключ, что у backend). OpenRouter забанен.
    # Имена моделей — из каталога MixRoute; Claude там сейчас не отвечает, поэтому Gemini.
    ai_api_key: str = Field("", validation_alias=AliasChoices("MIXROUTE_API_KEY", "AI_API_KEY"))
    ai_base_url: str = "https://api.mixroute.ai/v1"
    ai_proxy: str = ""
    parse_model: str = Field("gemini-2.5-flash", validation_alias="LLM_PARSE_MODEL")
    # Голос: модель должна принимать input_audio (Gemini понимает ogg/opus из Telegram)
    voice_model: str = Field("gemini-2.5-flash", validation_alias="LLM_VOICE_MODEL")

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def allowed_ids(self) -> set[int]:
        if not self.allowed_telegram_ids:
            return set()
        return {int(x.strip()) for x in self.allowed_telegram_ids.split(",") if x.strip()}

    @property
    def admin_ids(self) -> set[int]:
        if not self.admin_telegram_ids:
            return set()
        return {int(x.strip()) for x in self.admin_telegram_ids.split(",") if x.strip()}


settings = BotSettings()
