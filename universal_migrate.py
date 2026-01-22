import sqlite3
import os

def migrate_db(db_path):
    if not os.path.exists(db_path):
        print(f"Skipping {db_path} (not found)")
        return

    print(f"Checking {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(watchlists)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'position' not in columns:
            print(f"Adding 'position' column to {db_path}...")
            cursor.execute("ALTER TABLE watchlists ADD COLUMN position INTEGER DEFAULT 0")
            
            # Initialize positions for existing watchlists
            cursor.execute("SELECT id, user_id FROM watchlists ORDER BY user_id, id")
            rows = cursor.fetchall()
            
            user_counts = {}
            for row_id, user_id in rows:
                if user_id not in user_counts:
                    user_counts[user_id] = 0
                else:
                    user_counts[user_id] += 1
                
                cursor.execute("UPDATE watchlists SET position = ? WHERE id = ?", (user_counts[user_id], row_id))
            
            print(f"Successfully migrated {db_path}")
        else:
            print(f"Column 'position' already exists in {db_path}")
        
        conn.commit()
    except Exception as e:
        print(f"Error migrating {db_path}: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    dbs = ["finance.db", "backend/finance.db"]
    for db in dbs:
        migrate_db(db)
