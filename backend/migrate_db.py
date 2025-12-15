import sys
import os
from sqlalchemy import text

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from backend.database import engine

def migrate():
    print("Migrating Database...")
    try:
        with engine.connect() as conn:
            # Check and Add alerts_triggered_this_month
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN alerts_triggered_this_month INTEGER DEFAULT 0"))
                print("Added alerts_triggered_this_month")
            except Exception as e:
                print(f"Skipped alerts_triggered_this_month (Exists or Error: {e})")

            # Check and Add alert_limit
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN alert_limit INTEGER DEFAULT 10"))
                print("Added alert_limit")
            except Exception as e:
                print(f"Skipped alert_limit (Exists or Error: {e})")
                
            # Check and Add last_alert_reset
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_alert_reset DATETIME"))
                print("Added last_alert_reset")
            except Exception as e:
                print(f"Skipped last_alert_reset (Exists or Error: {e})")

            conn.commit()
            print("Migration Done.")
    except Exception as e:
        print(f"Migration Failed: {e}")

if __name__ == "__main__":
    migrate()
