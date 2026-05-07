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
    """TAVILY configuration."""
    TAVILY_API_KEY: str
    """CORS configuration."""
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000",]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

SPORT_RSS_FEEDS: dict[str, list[str]] = {
    "general": [
        "https://www.espn.com/espn/rss/news",
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.theguardian.com/sport/rss",
        "https://www.skysports.com/rss/12040",
    ],
    "cricket": [
        "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
        "https://www.skysports.com/rss/12110",
    ],
    "football": [
        "https://www.espn.com/espn/rss/soccer/news",
        "https://www.skysports.com/rss/11095",
    ],
    "soccer": [
        "https://www.espn.com/espn/rss/soccer/news",
        "https://www.skysports.com/rss/11095",
    ],
    "basketball": [
        "https://www.espn.com/espn/rss/nba/news",
    ],
    "nba": [
        "https://www.espn.com/espn/rss/nba/news",
    ],
    "american football": [
        "https://www.espn.com/espn/rss/nfl/news",
    ],
    "nfl": [
        "https://www.espn.com/espn/rss/nfl/news",
    ],
    "baseball": [
        "https://www.espn.com/espn/rss/mlb/news",
    ],
    "tennis": [
        "https://www.espn.com/espn/rss/tennis/news",
    ],
    "formula 1": [
        "https://www.espn.com/espn/rss/rpm/news",
    ],
    "f1": [
        "https://www.espn.com/espn/rss/rpm/news",
    ],
    "golf": [
        "https://www.espn.com/espn/rss/golf/news",
    ],
    "rugby": [
        "https://www.espn.com/espn/rss/rugby/news",
    ],
    "hockey": [
        "https://www.espn.com/espn/rss/nhl/news",
    ],
    "nhl": [
        "https://www.espn.com/espn/rss/nhl/news",
    ],
    "boxing": [
        "https://www.espn.com/espn/rss/boxing/news",
    ],
    "mma": [
        "https://www.espn.com/espn/rss/mma/news",
    ],
    "ufc": [
        "https://www.espn.com/espn/rss/mma/news",
    ],
}