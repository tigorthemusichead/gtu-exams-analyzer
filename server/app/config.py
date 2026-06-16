"""Application settings loaded from environment / .env file."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./cheat_buster.db"
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"

    # --- Individual analysis thresholds ---
    BURST_LINES_THRESHOLD: int = 200
    BURST_WINDOW_SECONDS: int = 60
    LATE_START_THRESHOLD_MINUTES: int = 15
    INACTIVITY_GAP_MINUTES: int = 15

    # --- Group similarity thresholds ---
    SIMILARITY_EDGE_THRESHOLD: float = 0.6
    SIMILARITY_WEIGHT_COSINE: float = 0.3
    SIMILARITY_WEIGHT_STRUCTURAL: float = 0.2
    SIMILARITY_WEIGHT_SEQUENTIAL: float = 0.5
    SEQUENTIAL_WINDOW_SECONDS: int = 1800
    SEQUENTIAL_CONTENT_THRESHOLD: float = 0.4
    SEQUENTIAL_MIN_TOKEN_COUNT: int = 3

    # --- Suspect detection thresholds ---
    SUSPECT_ANOMALY_THRESHOLD: float = 0.5
    SUSPECT_SIMILARITY_THRESHOLD: float = 0.7

    class Config:
        env_file = ".env"


settings = Settings()
