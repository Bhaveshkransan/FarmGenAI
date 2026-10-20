import logging
import json
import redis.asyncio as aioredis
from config.settings import REDIS_URL

logger = logging.getLogger("backend.redis")

STREAM_KEY = "agri:negotiation:jobs"
CONSUMER_GROUP = "worker_group"


class RedisManager:
    client: aioredis.Redis | None = None

    @classmethod
    async def connect(cls):
        try:
            cls.client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1.5, socket_connect_timeout=1.5)
            await cls.client.ping()
            logger.info("Connected to Redis successfully.")
            # Ensure consumer group exists on startup
            try:
                await cls.client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
            except Exception:
                pass  # Group already exists
        except Exception as e:
            logger.warning(f"Redis not reachable ({e}). Falling back to memory.")
            cls.client = None

    @classmethod
    async def disconnect(cls):
        if cls.client:
            await cls.client.close()
            cls.client = None

    @classmethod
    async def enqueue_negotiation_job(cls, negotiation_id: str, payload: dict, stream_key: str = STREAM_KEY) -> str | None:
        """
        Dispatches a negotiation task payload to the Redis Stream.
        Consumed asynchronously by backend.workers.agent_worker.
        """
        if not cls.client:
            return None
        try:
            # Clean non-serializable agent objects
            clean_payload = {
                k: v for k, v in payload.items()
                if not k.startswith("_") and k not in ("farmer_agent_obj", "buyer_agent_objs", "farmer", "buyers")
            }
            job_id = await cls.client.xadd(
                stream_key,
                {
                    "neg_id": str(negotiation_id),
                    "payload": json.dumps(clean_payload, default=str)
                }
            )
            logger.info(f"🚀 Dispatched negotiation {negotiation_id} to Redis Stream '{stream_key}' (Job ID: {job_id})")
            return job_id
        except Exception as e:
            logger.warning(f"Failed to enqueue negotiation {negotiation_id} to Redis Stream: {e}")
            return None

    @classmethod
    async def has_active_stream_workers(cls, stream_key: str = STREAM_KEY, group: str = CONSUMER_GROUP, max_idle_ms: int = 45000) -> bool:
        """
        Checks whether any worker in the consumer group has polled the stream recently (within max_idle_ms).
        """
        if not cls.client:
            return False
        try:
            consumers = await cls.client.xinfo_consumers(stream_key, group)
            for c in consumers:
                idle = c.get("idle", float("inf"))
                if idle < max_idle_ms:
                    return True
            return False
        except Exception:
            return False

    @classmethod
    async def get_stream_stats(cls, stream_key: str = STREAM_KEY) -> dict:
        """
        Returns real-time diagnostics of the Redis job stream and consumer groups.
        """
        if not cls.client:
            return {"connected": False, "length": 0, "active_workers": False}
        try:
            length = await cls.client.xlen(stream_key)
            has_workers = await cls.has_active_stream_workers(stream_key)
            groups = []
            try:
                raw_groups = await cls.client.xinfo_groups(stream_key)
                for g in raw_groups:
                    groups.append({
                        "name": g.get("name"),
                        "consumers": g.get("consumers"),
                        "pending": g.get("pending"),
                        "last_delivered_id": g.get("last-delivered-id")
                    })
            except Exception:
                pass
            return {
                "connected": True,
                "stream_key": stream_key,
                "length": length,
                "active_workers": has_workers,
                "groups": groups
            }
        except Exception as e:
            return {"connected": False, "error": str(e), "active_workers": False}


redis_manager = RedisManager()


