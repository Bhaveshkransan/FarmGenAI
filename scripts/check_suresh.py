import asyncio
from sqlalchemy import text
from database.db import AsyncSessionLocal

async def check_suresh():
    async with AsyncSessionLocal() as session:
        for t in ['farmers', 'produce', 'buyers', 'negotiations', 'users']:
            query = text(f"SELECT count(1) FROM {t} WHERE cast(row_to_json({t}) as text) ILIKE '%Suresh Deshmukh%'")
            res = await session.execute(query)
            print(f"{t:<15}: {res.scalar()} rows mention Suresh Deshmukh")

asyncio.run(check_suresh())
