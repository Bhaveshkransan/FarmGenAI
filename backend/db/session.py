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
            from sqlalchemy.pool import NullPool
            temp_engine = create_async_engine(url, echo=False, poolclass=NullPool)
            async with temp_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await temp_engine.dispose()
            return True
        except Exception:
            return False
    # Always use a fresh thread to avoid event loop conflicts
    return _run_async(_test())

db_url = settings.DATABASE_URL
if os.getenv("TESTING") == "1" or not is_postgres_running(db_url):
    db_url = "sqlite+aiosqlite:///agrinegotiator.db"
    logging.warning("⚠️ PostgreSQL not reachable or credentials invalid. Falling back to local SQLite: agrinegotiator.db")

from sqlalchemy.pool import NullPool
engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    try:
        from backend.db.models.schema import (
            DBUser, DBFarmer, DBBuyer, DBProduce, DBNegotiation,
            DBOffer, DBContract, DBHistory, DBAuthLog, DBWorkflowPlan
        )
        from backend.db.models.transport_agent_models import (
            DBVehicle, DBFuelPrice, DBTollRate, DBTransportCostParameter, DBTransportTrip
        )
    except Exception as e:
        logging.warning(f"Error importing models in init_db: {e}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Automatic schema sync: add missing columns if tables existed previously
        def _migrate_schema(sync_conn):
            from sqlalchemy import inspect
            inspector = inspect(sync_conn)
            existing_tables = set(inspector.get_table_names())
            for table_name, table in Base.metadata.tables.items():
                if table_name in existing_tables:
                    existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
                    for col in table.columns:
                        if col.name not in existing_cols:
                            col_type = col.type.compile(sync_conn.dialect)
                            sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"
                            try:
                                sync_conn.execute(text(sql))
                                logging.info(f"Auto-migrated missing column: {table_name}.{col.name}")
                            except Exception as err:
                                logging.warning(f"Could not add column {table_name}.{col.name}: {err}")

        await conn.run_sync(_migrate_schema)


