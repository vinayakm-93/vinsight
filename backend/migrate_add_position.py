# Migration script to add 'position' column to watchlists table
import sqlite3
import os

DB_PATH = "backend/finance.db"
# If running from project root, path might be finance.db
if not os.path.exists(DB_PATH):
    DB_PATH = "finance.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Starting migration to add 'position' column to watchlists...")

        # Check if column already exists
        cursor.execute("PRAGMA table_info(watchlists)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'position' not in columns:
            print("Adding 'position' column...")
            cursor.execute("ALTER TABLE watchlists ADD COLUMN position INTEGER DEFAULT 0")
            
            # Initialize positions for existing watchlists
            cursor.execute("SELECT id FROM watchlists ORDER BY id")
            rows = cursor.fetchall()
            for i, (row_id,) in enumerate(rows):
                cursor.execute("UPDATE watchlists SET position = ? WHERE id = ?", (i, row_id))
            
            print(f"Column added and {len(rows)} positions initialized.")
        else:
            print("Column 'position' already exists.")

        conn.commit()
        print("Migration successful.")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
