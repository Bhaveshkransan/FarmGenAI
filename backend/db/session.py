import os
import logging
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from config.settings import settings

Base = declarative_base()

from sqlalchemy import text

def _run_async(coro):
    import asyncio
    import threading
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        res_list = []
        exc_list = []
        def run_in_thread():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                res = new_loop.run_until_complete(coro)
                res_list.append(res)
                new_loop.close()
            except Exception as e:
                exc_list.append(e)
        t = threading.Thread(target=run_in_thread)
        t.start()
        t.join()
        if exc_list:
            raise exc_list[0]
        return res_list[0]
    else:
        return asyncio.run(coro)

def is_postgres_running(url: str) -> bool:
    if "postgres" not in url.lower():
        return False
    async def _test():
        try:
            temp_engine = create_async_engine(url, echo=False)
            async with temp_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await temp_engine.dispose()
            return True
        except Exception:
            return False
    try:
        return _run_async(_test())
    except Exception:
        return False

db_url = settings.DATABASE_URL
if os.getenv("TESTING") == "1" or not is_postgres_running(db_url):
    db_url = "sqlite+aiosqlite:///agrinegotiator.db"
    logging.warning("⚠️ PostgreSQL not reachable or credentials invalid. Falling back to local SQLite: agrinegotiator.db")

from sqlalchemy.pool import NullPool
engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        try:
            from backend.db.session import Base as V1Base
            await conn.run_sync(V1Base.metadata.create_all)
        except Exception as e:
            logging.warning(f"Failed to create V1 tables: {e}")


