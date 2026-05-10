from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import os
import logging

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path) # Load environment variables from backend/.env explicitly

from database import init_db
from rate_limiter import limiter
import posthog

logger = logging.getLogger(__name__)

# Environment-based configuration
ENV = os.getenv("ENV", "development")
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").lower() == "true"

# Pre-import MCP server for lifespan management
_mcp_server = None
_mcp_app = None
MCP_API_KEY = os.getenv("MCP_API_KEY", "")

if MCP_ENABLED:
    try:
        from mcp_tools import mcp as _mcp_server
        _raw_mcp_app = _mcp_server.streamable_http_app()

        # Wrap with Bearer token auth middleware
        if MCP_API_KEY:
            from starlette.requests import Request as StarletteRequest
            from starlette.responses import JSONResponse as StarletteJSONResponse
            from mcp_telemetry import track_auth_failure
            import hmac

            class MCPAuthMiddleware:
                """ASGI middleware that validates Bearer token on all MCP requests."""
                def __init__(self, app):
                    self.app = app

                async def __call__(self, scope, receive, send):
                    if scope["type"] == "http":
                        headers = dict(scope.get("headers", []))
                        auth_header = headers.get(b"authorization", b"").decode()

                        # Constant-time comparison to prevent timing attacks
                        token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
                        if not token or not hmac.compare_digest(token, MCP_API_KEY):
                            # Track failed auth attempt
                            client = scope.get("client", ("unknown", 0))
                            user_agent = headers.get(b"user-agent", b"unknown").decode()
                            track_auth_failure(ip=client[0] if client else "unknown", user_agent=user_agent)

                            response = StarletteJSONResponse(
                                {"error": "Unauthorized", "code": "INVALID_API_KEY"},
                                status_code=401,
                            )
                            await response(scope, receive, send)
                            return

                    await self.app(scope, receive, send)

            _mcp_app = MCPAuthMiddleware(_raw_mcp_app)
            logger.info("MCP Server prepared with API key auth")
        else:
            _mcp_app = _raw_mcp_app
            logger.warning("MCP Server prepared WITHOUT auth (no MCP_API_KEY set — dev mode)")
    except Exception as e:
        logger.error(f"Failed to import MCP server: {e}")
        _mcp_server = None
        _mcp_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup (DB, migrations, PostHog, MCP session) and shutdown.
    """
    # ── Startup ──
    init_db()
    try:
        from migrate import migrate
        migrate()
    except Exception as e:
        logger.error(f"Migration failed during startup: {e}")
        
    # Initialize PostHog
    posthog_key = os.getenv("POSTHOG_API_KEY")
    if posthog_key:
        posthog.project_api_key = posthog_key
        posthog.host = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")
        logger.info("PostHog telemetry initialized")
    else:
        logger.warning("POSTHOG_API_KEY not found. PostHog telemetry is disabled.")

    logger.info(f"Server started in {ENV} mode with rate limiting enabled")

    # Start MCP session manager (required for Streamable HTTP)
    if _mcp_server is not None:
        async with _mcp_server.session_manager.run():
            logger.info("MCP session manager started")
            yield
            logger.info("MCP session manager shutting down")
    else:
        yield

    # ── Shutdown ──
    logger.info("Server shutting down")


app = FastAPI(
    title="Finance Research App",
    redirect_slashes=True,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
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
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Guest-UUID"],
)

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
app.router.default_response_class = NaNJSONResponse

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Finance Research Backend Running"}

# Import and include routers
from routes import watchlist, data, feedback, auth, alerts, sentiment, guardian, portfolio, theses, profile

# Mount MCP Server (Streamable HTTP for external AI agents)
if _mcp_app is not None:
    app.mount("/mcp", _mcp_app)
    logger.info("MCP Server mounted at /mcp (Streamable HTTP)")

app.include_router(watchlist.router)
app.include_router(data.router)
# app.include_router(feedback.router)
app.include_router(auth.router)
app.include_router(alerts.router)
app.include_router(sentiment.router, prefix="/api") # Assuming other routes are structured similarly (checked data.py prefix implicitly via usage)
app.include_router(guardian.router)
app.include_router(portfolio.router)
app.include_router(theses.router)
app.include_router(profile.router)

