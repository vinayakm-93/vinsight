import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv("backend/.env")

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "finance")
CLOUDSQL_INSTANCE = os.getenv("CLOUDSQL_INSTANCE")

print(f"Testing local connection to Cloud SQL Proxy...")
print(f"User: {DB_USER}")
try:
    engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@127.0.0.1:5432/{DB_NAME}")
    with engine.connect() as conn:
        print("Success! Can connect to DB via Proxy.")
except Exception as e:
    print(f"Failed: {e}")
