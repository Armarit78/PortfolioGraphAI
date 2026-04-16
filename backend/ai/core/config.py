import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    MISTRAL_API_KEY: SecretStr | None
    MISTRAL_MODEL :str
    LLM_TEMPERATURE: float
    SUPABASE_DIRECT_LINK:str
    SUPABASE_URL:str
    SUPABASE_SERVICE_KEY:str
    DEBUG_MODE:bool=True

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )


