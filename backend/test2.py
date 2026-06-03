import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    db_url = 'sqlite+aiosqlite:///D:/SSG_Fullstack_projects/call_automation_final (2)/call_automation_final/call_automation/call_automation_2/backend/marketing_ai.db'
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.execute(text('CREATE TABLE IF NOT EXISTS test (id int)'))
        await conn.execute(text('INSERT INTO test VALUES (1)'))
        res = await conn.execute(text('SELECT * FROM test'))
        print('Rows:', res.fetchall())

asyncio.run(test())
