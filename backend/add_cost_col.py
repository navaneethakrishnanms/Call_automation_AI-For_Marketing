import sqlite3
import sys

def main():
    try:
        conn = sqlite3.connect('data/marketing_ai.db')
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE calls ADD COLUMN cost FLOAT;")
        conn.commit()
        print("Column 'cost' added successfully.")
    except Exception as e:
        print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
