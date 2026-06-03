import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    db_url = 'sqlite+aiosqlite:///D:/SSG_Fullstack_projects/call_automation_final (2)/call_automation_final/call_automation/call_automation_2/backend/marketing_ai.db'
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        res = await conn.execute(text('SELECT * FROM leads'))
        print('Leads:', res.fetchall())

asyncio.run(test())
