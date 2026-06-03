import asyncio
import os
import sys

# Add backend directory to sys.path so we can import app modules
sys.path.insert(0, os.path.abspath('.'))

from app.services.retell_service import get_retell_call

async def main():
    import sqlite3
    import json
    
    conn = sqlite3.connect('data/marketing_ai.db')
    cursor = conn.cursor()
    cursor.execute("SELECT twilio_call_sid FROM calls WHERE twilio_call_sid IS NOT NULL AND status='completed' LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("No completed calls with sid found.")
        return
        
    sid = row[0]
    print(f"Fetching sid: {sid}")
    
    res = await get_retell_call(sid)
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
