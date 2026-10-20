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
        try:
            import backend.db.models.schema
            import backend.db.models.transport_agent_models
        except Exception:
            pass
        await conn.run_sync(Base.metadata.create_all)
        
        try:
            from backend.db.session import Base as V1Base
            await conn.run_sync(V1Base.metadata.create_all)
        except Exception as e:
            logging.warning(f"Failed to create V1 tables: {e}")

        # Safe automatic migrations for newly added columns in Postgres
        alter_statements = [
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS trace_id VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS workflow_mode VARCHAR DEFAULT 'FULL_SUPPLY_CHAIN';",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS user_id VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS farmer_name VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS crop VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS crop_category VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS variety VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS grade VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS quantity FLOAT;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS unit VARCHAR DEFAULT 'kg';",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS min_sale_quantity FLOAT;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS expected_price FLOAT;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS min_price FLOAT;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS price_unit VARCHAR DEFAULT 'per_kg';",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS quality_info JSONB;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS harvest_date VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS availability_date VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS preferred_selling_date VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS shelf_life INTEGER;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS location VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS latitude FLOAT;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS longitude FLOAT;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS storage_info JSONB;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS processing_info JSONB;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS transport_reqs JSONB;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS selected_services JSONB;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS images JSONB;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS description VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS language VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'ACTIVE';",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS created_at VARCHAR;",
            "ALTER TABLE produce ADD COLUMN IF NOT EXISTS updated_at VARCHAR;",
            
            "ALTER TABLE buyers ADD COLUMN IF NOT EXISTS trace_id VARCHAR;",
            "ALTER TABLE negotiations ADD COLUMN IF NOT EXISTS trace_id VARCHAR;",
            "ALTER TABLE offers ADD COLUMN IF NOT EXISTS trace_id VARCHAR;",
            "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS trace_id VARCHAR;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS trace_id VARCHAR;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS market_price FLOAT;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS negotiation_rounds INTEGER;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS successful BOOLEAN;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS failure_reason VARCHAR;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS farmer_strategy VARCHAR;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS farmer_reward FLOAT;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS buyer_strategy VARCHAR;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS buyer_reward FLOAT;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS warehouse_strategy VARCHAR;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS warehouse_reward FLOAT;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS transport_strategy VARCHAR;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS transport_reward FLOAT;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS processor_strategy VARCHAR;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS processor_reward FLOAT;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS compost_strategy VARCHAR;",
            "ALTER TABLE history ADD COLUMN IF NOT EXISTS compost_reward FLOAT;",
            "ALTER TABLE transport_carrier_bookings ADD COLUMN IF NOT EXISTS negotiation_id VARCHAR;",
            "ALTER TABLE transport_carrier_bookings ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR;"
        ]
        for stmt in alter_statements:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass


