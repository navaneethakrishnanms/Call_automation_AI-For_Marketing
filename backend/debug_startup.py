import traceback
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

import asyncio

async def test_lifespan():
    try:
        from app.main import app
        print("App imported successfully")
        async with app.router.lifespan_context(app):
            print("Lifespan context entered successfully")
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_lifespan())
