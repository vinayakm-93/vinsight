import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "vinsight.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE guardian_theses ADD COLUMN last_manual_scan_at DATETIME;")
    conn.commit()
    print("Added last_manual_scan_at to guardian_theses.")
except sqlite3.OperationalError as e:
    print(f"Column might already exist or other error: {e}")
finally:
    conn.close()
