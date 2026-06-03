import asyncio
import os
import sys
import sqlite3

sys.path.insert(0, os.path.abspath('.'))

from app.services.retell_service import get_retell_call

async def main():
    conn = sqlite3.connect('data/marketing_ai.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, twilio_call_sid FROM calls WHERE twilio_call_sid IS NOT NULL AND status='completed' AND cost IS NULL")
    rows = cursor.fetchall()
    
    for row in rows:
        call_id, sid = row
        print(f"Fetching sid: {sid} for call_id: {call_id}")
        res = await get_retell_call(sid)
        if res.get("status") == "success":
            data = res.get("data", {})
            call_cost_data = data.get("call_cost", {})
            if call_cost_data and isinstance(call_cost_data, dict):
                combined = call_cost_data.get("combined_cost")
                if combined is not None:
                    cost_in_dollars = combined / 100.0
                    cursor.execute("UPDATE calls SET cost=? WHERE id=?", (cost_in_dollars, call_id))
                    conn.commit()
                    print(f"Updated call {call_id} with cost ${cost_in_dollars}")
    
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
