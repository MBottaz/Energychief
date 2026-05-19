from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    TELEGRAM_BOT_TOKEN: str
    ENODE_CLIENT_ID: str
    ENODE_CLIENT_SECRET: str
    ENODE_ENVIRONMENT: str = "production"  # Default set to production as requested
    DATABASE_PATH: str = "data/energychief.db"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
