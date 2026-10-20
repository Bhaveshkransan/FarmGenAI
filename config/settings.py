"""Central runtime settings. Values are read from environment / .env file.
DEPRECATED: Use backend.core.config instead. This file exists for backward compatibility.
"""

from backend.core.config import (
    settings,
    Settings,
    ENABLE_LLM,
    OLLAMA_URL,
    OLLAMA_MODEL,
    GEMINI_API_KEY,
    DEFAULT_LLM_MODEL,
    API_HOST,
    API_PORT,
    WS_HOST,
    WS_PORT,
    DATABASE_URL,
    REDIS_URL,
    CHROMA_URL,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    OPEN_METEO_BASE_URL,
    OSRM_BASE_URL,
    ENABLE_MINIO,
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    DB_PATH,
    DEFAULT_MAX_ROUNDS,
    EMBEDDING_MODEL,
    DATA_GOV_IN_API_KEY
)
