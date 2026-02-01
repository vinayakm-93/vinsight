import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Use DATABASE_URL if set, or construct from components (Secrets), otherwise local SQLite
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    # Check if we have Cloud SQL credentials (e.g. from Secrets)
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_name = os.getenv("DB_NAME", "finance")
    cloud_sql_instance = os.getenv("CLOUDSQL_INSTANCE")

    if db_user and db_pass and cloud_sql_instance:
         # URL-encode password to handle special characters
         encoded_pass = quote_plus(db_pass)
         SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{db_user}:{encoded_pass}@/{db_name}?host=/cloudsql/{cloud_sql_instance}"
    else:
        # Fallback to local SQLite
        SQLALCHEMY_DATABASE_URL = "sqlite:///./finance.db"

check_same_thread = False
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args=connect_args
    )
else:
    # Production / Cloud SQL (PostgreSQL)
    # Recommended pool settings for Cloud Run
    connect_args = {}
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def init_db():
    # Create tables if they don't exist
    # Note: This checks for table existence but won't migrate columns.
    # Use 'python migrate.py' for schema migrations.
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized (Tables checked)")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
