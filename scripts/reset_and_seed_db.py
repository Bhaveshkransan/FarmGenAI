import asyncio
import sys
import os

sys.path.insert(0, ".")

from backend.db.session import engine, Base, init_db
from backend.db.models.schema import *
from backend.db.models.transport_agent_models import *
from scripts.seed_real_database import seed

async def main():
    print("Dropping outdated tables and creating clean schema in PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully. Now seeding data...")
    await seed()
    print("Database reset and seeded successfully!")

if __name__ == "__main__":
    asyncio.run(main())
