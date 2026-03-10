from sqlalchemy import text
from backend.database import engine

def migrate():
    print("Migrating guardian_alerts table...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE guardian_alerts ADD COLUMN research_history TEXT"))
            conn.commit()
            print("Added research_history column.")
        except Exception as e:
            print(f"research_history column might already exist: {e}")

        try:
            conn.execute(text("ALTER TABLE guardian_alerts ADD COLUMN thinking_log TEXT"))
            conn.commit()
            print("Added thinking_log column.")
        except Exception as e:
            print(f"thinking_log column might already exist: {e}")

if __name__ == "__main__":
    migrate()
