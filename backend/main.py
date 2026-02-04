from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
import logging

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path) # Load environment variables from backend/.env explicitly

from database import init_db
from rate_limiter import limiter

logger = logging.getLogger(__name__)

app = FastAPI(title="Finance Research App", redirect_slashes=False)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Environment-based CORS configuration
ENV = os.getenv("ENV", "development")
if ENV == "production":
    # Production: Restrict to specific allowed origins
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
    allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
else:
    # Development: Allow localhost and 127.0.0.1
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001", # Common fallback
    ]

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

# --- Custom JSON Encoder for NaN Handling ---
import simplejson
from typing import Any
from starlette.responses import JSONResponse

class NaNJSONResponse(JSONResponse):
    """
    Custom JSONResponse that handles NaN values by converting them to null,
    preventing 500 errors when data providers return gaps or invalid floats.
    """
    def render(self, content: Any) -> bytes:
        return simplejson.dumps(
            content,
            ensure_ascii=False,
            ignore_nan=True, # Critical: Converts NaN/Infinity to null
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

# Register the custom response class globally
# Note: We must re-instantiate FastAPI to set the default response class if we want it global,
# OR we can just use the middleware / exception handlers.
# But since we already instantiated 'app' above, we can just patch it or swap it.
# Simplest for this existing file structure:
# We already defined 'app' earlier. Let's just create a new one with the custom class 
# and re-attach dependencies if we were writing from scratch.
# But to be safe with existing imports:
app.router.default_response_class = NaNJSONResponse

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Finance Research Backend Running"}

# Import and include routers
from routes import watchlist, data, feedback, auth, alerts, sentiment
app.include_router(watchlist.router)
app.include_router(data.router)
# app.include_router(feedback.router)
app.include_router(auth.router)
app.include_router(alerts.router)
app.include_router(sentiment.router, prefix="/api") # Assuming other routes are structured similarly (checked data.py prefix implicitly via usage)
