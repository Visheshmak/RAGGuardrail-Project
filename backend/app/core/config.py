from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str
    REDIS_URL: str
    QDRANT_URL: str
    JWT_SECRET: str
    OPENAI_API_KEY: str
    CORS_ORIGINS: List[str] | str = []

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            try:
                return json.loads(self.CORS_ORIGINS)
            except json.JSONDecodeError:
                return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS

settings = Settings()
