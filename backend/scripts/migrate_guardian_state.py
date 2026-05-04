import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'finance.db')

def migrate():
    print(f"Connecting to {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("ALTER TABLE guardian_theses ADD COLUMN last_trigger_state TEXT;")
        conn.commit()
        print("✅ Added last_trigger_state successfully to guardian_theses.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column last_trigger_state already exists.")
        else:
            print(f"Skipped adding column: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
