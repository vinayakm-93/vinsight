"""
VinSight MCP Telemetry Module
Tracks all MCP tool calls, errors, cache hits, rate limits, and auth failures
via PostHog analytics. Provides data-driven phase transition signals.

Events emitted:
    - mcp_tool_call: Every successful tool execution
    - mcp_tool_error: Tool throws an exception
    - mcp_rate_limited: Rate limit hit
    - mcp_cache_hit: Cached response served
    - mcp_auth_failure: Invalid/missing API key
"""

import time
import posthog
import logging
from functools import wraps

logger = logging.getLogger("VinSightMCP")


def track_mcp_tool(func):
    """
    Decorator that wraps every MCP tool with PostHog telemetry.
    
    Tracks:
        - Tool name, ticker argument, duration
        - Success/failure status
        - Error details on failure
    
    Usage:
        @mcp.tool()
        @track_mcp_tool
        def analyze_sentiment(ticker: str) -> str:
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        # Extract ticker from kwargs or first positional arg
        ticker = kwargs.get("ticker") or (args[0] if args else "unknown")
        start = time.time()

        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000

            # Track success
            try:
                posthog.capture(
                    distinct_id="mcp_server",
                    event="mcp_tool_call",
                    properties={
                        "tool": tool_name,
                        "ticker": str(ticker).upper()[:10],
                        "duration_ms": round(duration_ms, 1),
                        "success": True,
                    }
                )
            except Exception:
                pass  # Telemetry should never break tool execution

            logger.info(f"MCP {tool_name}({ticker}) → {duration_ms:.0f}ms ✓")
            return result

        except Exception as e:
            duration_ms = (time.time() - start) * 1000

            # Track error
            try:
                posthog.capture(
                    distinct_id="mcp_server",
                    event="mcp_tool_error",
                    properties={
                        "tool": tool_name,
                        "ticker": str(ticker).upper()[:10],
                        "duration_ms": round(duration_ms, 1),
                        "error_code": type(e).__name__,
                        "error_message": str(e)[:200],
                    }
                )
            except Exception:
                pass

            logger.error(f"MCP {tool_name}({ticker}) FAILED: {e}")
            raise

    return wrapper


def track_rate_limit(tool_name: str, limit_type: str):
    """Fire when a rate limit is hit."""
    try:
        posthog.capture(
            distinct_id="mcp_server",
            event="mcp_rate_limited",
            properties={
                "tool": tool_name,
                "limit_type": limit_type,
            }
        )
    except Exception:
        pass


def track_cache_hit(tool_name: str, ticker: str, cache_age_seconds: float):
    """Fire when a cached response is served instead of executing the tool."""
    try:
        posthog.capture(
            distinct_id="mcp_server",
            event="mcp_cache_hit",
            properties={
                "tool": tool_name,
                "ticker": ticker.upper()[:10],
                "cache_age_seconds": round(cache_age_seconds, 1),
            }
        )
    except Exception:
        pass


def track_auth_failure(ip: str = "unknown", user_agent: str = "unknown"):
    """Fire when an unauthorized MCP request is rejected."""
    try:
        posthog.capture(
            distinct_id="mcp_server",
            event="mcp_auth_failure",
            properties={
                "ip": ip[:50],
                "user_agent": user_agent[:100],
            }
        )
    except Exception:
        pass
