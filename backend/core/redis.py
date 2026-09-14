import logging
import redis.asyncio as aioredis
from config.settings import REDIS_URL

logger = logging.getLogger("backend.redis")

class RedisManager:
    client: aioredis.Redis | None = None

    @classmethod
    async def connect(cls):
        try:
            cls.client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1.5, socket_connect_timeout=1.5)
            await cls.client.ping()
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.warning(f"Redis not reachable ({e}). Falling back to memory.")
            cls.client = None

    @classmethod
    async def disconnect(cls):
        if cls.client:
            await cls.client.close()
            cls.client = None

redis_manager = RedisManager()

