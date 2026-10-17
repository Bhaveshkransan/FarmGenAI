import asyncio
from database.db import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"))
        tables = [r[0] for r in res.fetchall()]
        print("TABLES:", tables)
        for t in tables:
            cnt = (await session.execute(text(f"SELECT COUNT(*) FROM {t}"))).scalar()
            print(f"  {t}: {cnt} rows")

if __name__ == "__main__":
    asyncio.run(main())
