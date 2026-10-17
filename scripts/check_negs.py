import asyncio
from database.db import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as s:
        res = await s.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'negotiations';"))
        print("NEGOTIATIONS COLUMNS:")
        for r in res.fetchall():
            print(f"  {r[0]} ({r[1]})")

asyncio.run(check())
