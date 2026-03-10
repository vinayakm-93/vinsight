import os
from sqlalchemy import create_engine
import time
from dotenv import load_dotenv

load_dotenv("backend/.env")

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "finance")

print("Testing direct public IP connection to rule out socket issues...")
# Public IP of Cloud SQL instance is needed here, or we can just test if the socket path is reachable
# But since we are local, we can't test the Cloud Run Unix socket anyway.
# Let's check if the Cloud Run service has the Cloud SQL connection configured.
