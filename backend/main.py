from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
import logging

load_dotenv() # Load environment variables from .env file

from database import init_db
from rate_limiter import limiter

logger = logging.getLogger(__name__)

app = FastAPI(title="Finance Research App")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Environment-based CORS configuration
ENV = os.getenv("ENV", "development")
if ENV == "production":
    # Production: Restrict to specific allowed origins
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
    allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
else:
    # Development: Allow localhost
    allowed_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

@app.on_event("startup")
def on_startup():
    init_db()
    # MarketWatcher moved to Cloud Run Job
    logger.info(f"Server started in {ENV} mode with rate limiting enabled")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Finance Research Backend Running"}

# Import and include routers
from routes import watchlist, data, feedback, auth, alerts
app.include_router(watchlist.router)
app.include_router(data.router)
# app.include_router(feedback.router)
app.include_router(auth.router)
app.include_router(alerts.router)
