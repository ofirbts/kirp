# app/config/settings.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    mongodb_uri: str
    redis_url: str
    debug: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
