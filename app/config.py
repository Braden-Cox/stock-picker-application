from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GETXAPI_KEY: str
    ANTHROPIC_API_KEY: str
    GOOGLE_GEMINI_API_KEY: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    PIPELINE_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()
