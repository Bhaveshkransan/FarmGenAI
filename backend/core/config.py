"""Central runtime settings. Values are read from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── LLM (Ollama Primary / Gemini Fallback) ──────────────────────
    ENABLE_LLM: bool = True
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"
    GEMINI_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "qwen3:8b"

    # ── Server ───────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    WS_HOST: str = "localhost"
    WS_PORT: int = 8765

    # ── Database & Cache & Search ────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://admin:admin_password@localhost:5432/agrinegotiator"
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMA_URL: str = "http://localhost:8001"

    # ── Security & Authentication ────────────────────────────────────
    JWT_SECRET_KEY: str = "supersecretkeyforagrinegotiatorsigningtokens12345"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ── External Integrations (Weather, Maps, Storage) ───────────────
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com"
    OSRM_BASE_URL: str = "https://router.project-osrm.org"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    DATA_GOV_IN_API_KEY: str = ""

    # ── Embeddings & Simulation ──────────────────────────────────────
    DB_PATH: str = "agrinegotiator.db"
    DEFAULT_MAX_ROUNDS: int = 5
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"


settings = Settings()

# Export for backward compatibility
ENABLE_LLM = settings.ENABLE_LLM
OLLAMA_URL = settings.OLLAMA_URL
OLLAMA_MODEL = settings.OLLAMA_MODEL
GEMINI_API_KEY = settings.GEMINI_API_KEY
DEFAULT_LLM_MODEL = settings.DEFAULT_LLM_MODEL
API_HOST = settings.API_HOST
API_PORT = settings.API_PORT
WS_HOST = settings.WS_HOST
WS_PORT = settings.WS_PORT
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
CHROMA_URL = settings.CHROMA_URL
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
OPEN_METEO_BASE_URL = settings.OPEN_METEO_BASE_URL
OSRM_BASE_URL = settings.OSRM_BASE_URL
MINIO_ENDPOINT = settings.MINIO_ENDPOINT
MINIO_ACCESS_KEY = settings.MINIO_ACCESS_KEY
MINIO_SECRET_KEY = settings.MINIO_SECRET_KEY
DB_PATH = settings.DB_PATH
DEFAULT_MAX_ROUNDS = settings.DEFAULT_MAX_ROUNDS
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
DATA_GOV_IN_API_KEY = settings.DATA_GOV_IN_API_KEY

