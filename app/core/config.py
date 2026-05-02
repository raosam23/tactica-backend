from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration."""
    APP_NAME: str = "Tactica"
    APP_ENV: str = "development"
    DEBUG: bool = True
    """Database configuration."""
    DATABASE_URL: str
    """Authentication configuration."""
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SALT_ROUNDS: int = 12
    """OPENAI configuration."""
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_DIMENSION: int = 1536
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()