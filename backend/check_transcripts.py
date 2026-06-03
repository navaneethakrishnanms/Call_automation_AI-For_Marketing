import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/marketing_ai.db')
cursor = conn.execute('SELECT id, transcript FROM calls WHERE transcript IS NOT NULL ORDER BY id DESC LIMIT 5')
for r in cursor.fetchall():
    print(f"=== Call ID: {r[0]} ===")
    print(r[1][:600] if r[1] else "None")
    print()
