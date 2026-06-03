import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    engine = create_async_engine('sqlite+aiosqlite:///d:\\SSG_Fullstack_projects\\call_automation_final (2)\\call_automation_final\\call_automation\\call_automation_2\\backend\\marketing_ai.db')
    async with engine.begin() as conn:
        await conn.execute(text('CREATE TABLE IF NOT EXISTS test_tb (id int);'))
    await engine.dispose()
    print("Done")

if __name__ == '__main__':
    asyncio.run(test())
