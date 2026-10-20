import asyncio
import logging
from sqlalchemy import text
from backend.db.session import engine

logging.basicConfig(level=logging.INFO)

async def main():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE produce ADD COLUMN trace_id VARCHAR;"))
            logging.info("Added trace_id to produce.")
        except Exception as e:
            logging.info(f"trace_id error (might exist): {e}")
            
        try:
            await conn.execute(text("ALTER TABLE produce ADD COLUMN workflow_mode VARCHAR DEFAULT 'FULL_SUPPLY_CHAIN';"))
            logging.info("Added workflow_mode to produce.")
        except Exception as e:
            logging.info(f"workflow_mode error (might exist): {e}")

if __name__ == "__main__":
    asyncio.run(main())
