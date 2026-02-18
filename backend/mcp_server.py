
import os
import sys
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# MCP Imports
from mcp.server.fastmcp import FastMCP, Context
import mcp.types as types

# Service Imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services import groq_sentiment, finnhub_news, simulation, yahoo_client, earnings
import database 

# --- CONFIGURATION ---
KILL_SWITCH_FILE = "mcp_kill_switch.lock"
LOG_FILE = "logs/mcp_server.log"
LIMITS_FILE = "logs/mcp_limits.json"

# Limits Configuration
GLOBAL_DAILY_LIMIT = 100 # Total calls per 24h

# Hourly Limits (Calls per Hour)
HOURLY_LIMITS = {
    "analyze_sentiment": 60,  # ~1 per min avg
    "run_monte_carlo": 100,   # Fast
    "analyze_earnings": 10    # Expensive
}

# --- LOGGING SETUP ---
os.makedirs("logs", exist_ok=True)

class SafeFormatter(logging.Formatter):
    def format(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = record.msg.replace('\n', '\\n').replace('\r', '')
        return super().format(record)

logger = logging.getLogger("VinSightMCP")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
handler.setFormatter(SafeFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
console = logging.StreamHandler()
console.setFormatter(SafeFormatter('%(levelname)s: %(message)s'))
logger.addHandler(console)

# --- SAFETY CORE ---
class SafetyGuard:
    def __init__(self):
        self.usage_data = self._load_usage()

    def _load_usage(self) -> Dict:
        """Load usage data from disk for persistence."""
        if os.path.exists(LIMITS_FILE):
            try:
                with open(LIMITS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"daily": {"count": 0, "reset_at": 0}, "hourly": {}}

    def _save_usage(self):
        """Save usage data to disk."""
        try:
            with open(LIMITS_FILE, 'w') as f:
                json.dump(self.usage_data, f)
        except Exception as e:
            logger.error(f"Failed to save limits: {e}")

    def _check_reset(self):
        """Reset counters if windows have passed."""
        now = time.time()
        
        # Daily Reset
        if now > self.usage_data["daily"]["reset_at"]:
            self.usage_data["daily"]["count"] = 0
            self.usage_data["daily"]["reset_at"] = now + 86400 # 24 hours
            logger.info("Daily limit counter reset.")

        # Clean Hourly Windows
        # We store hourly as {tool: [timestamp, ...]}
        # We verify on the fly in check_hourly, but let's prune occasionally
        pass 

    def check_kill_switch(self):
        """Gate 1: The Hard Stop."""
        if os.path.exists(KILL_SWITCH_FILE):
            logger.critical("BLOCKED: Kill Switch Engaged")
            raise RuntimeError("SERVICE_SUSPENDED: Kill Switch Active")

    def check_limits(self, tool_name: str):
        """Gate 2: Enforce Daily and Hourly Limits."""
        self._check_reset()
        now = time.time()

        # 1. Global Daily Check
        if self.usage_data["daily"]["count"] >= GLOBAL_DAILY_LIMIT:
             logger.warning("BLOCKED: Global Daily Limit Exceeded")
             raise RuntimeError(f"DAILY_LIMIT_EXCEEDED: Global limit of {GLOBAL_DAILY_LIMIT} calls reached.")

        # 2. Hourly Tool Check
        limit = HOURLY_LIMITS.get(tool_name, 10)
        tool_history = self.usage_data["hourly"].get(tool_name, [])
        
        # Prune old (older than 1 hour)
        tool_history = [t for t in tool_history if now - t < 3600]
        self.usage_data["hourly"][tool_name] = tool_history

        if len(tool_history) >= limit:
            logger.warning(f"BLOCKED: Hourly Limit Exceeded for {tool_name}")
            raise RuntimeError(f"HOURLY_LIMIT_EXCEEDED: {tool_name} limit of {limit}/hour reached.")
            
        # 3. Increment
        self.usage_data["daily"]["count"] += 1
        self.usage_data["hourly"][tool_name].append(now)
        self._save_usage()

guard = SafetyGuard()

def format_error(code: str, message: str) -> str:
    """Standardized Error JSON."""
    return json.dumps({
        "error": message,
        "code": code,
        "status": "failed"
    })

# --- MCP SERVER ---
mcp = FastMCP("VinSight")

@mcp.tool()
def analyze_sentiment(ticker: str) -> str:
    """
    Get AI-driven sentiment analysis based on the last 7 days of news.
    Output includes 'Today Score' vs 'Weekly Score' and key drivers.
    """
    start_time = time.time()
    sanitized_ticker = ticker.strip().upper()[:10]
    
    try:
        guard.check_kill_switch()
        guard.check_limits("analyze_sentiment")
        
        logger.info(f"START: analyze_sentiment({sanitized_ticker})")
        
        news = finnhub_news.fetch_company_news(sanitized_ticker)
        if not news['latest'] and not news['historical']:
            return format_error("NO_DATA", "No news found for ticker")

        analyzer = groq_sentiment.get_groq_analyzer()
        result = analyzer.analyze_dual_period(news['latest'], news['historical'], context=sanitized_ticker)
        
        duration = time.time() - start_time
        logger.info(f"SUCCESS: analyze_sentiment({sanitized_ticker}) - {duration:.2f}s")
        return json.dumps(result, indent=2)

    except RuntimeError as re:
        # Expected Safety Errors (Kill Switch / Limits)
        return format_error(str(re).split(":")[0], str(re))
    except Exception as e:
        logger.error(f"FAIL: analyze_sentiment({sanitized_ticker}) - {str(e)}")
        return format_error("INTERNAL_ERROR", str(e))

@mcp.tool()
def run_monte_carlo(ticker: str) -> str:
    """
    Run 5,000 Monte Carlo simulations to project price risk (P10/P50/P90).
    Use this to assess downside risk (VaR) and upside potential.
    """
    start_time = time.time()
    sanitized_ticker = ticker.strip().upper()[:10]

    try:
        guard.check_kill_switch()
        guard.check_limits("run_monte_carlo")
        
        logger.info(f"START: run_monte_carlo({sanitized_ticker})")
        
        chart = yahoo_client.get_chart_data(sanitized_ticker, range_="2y")
        if not chart or 'timestamp' not in chart:
             return format_error("DATA_FETCH_FAILED", "Failed to fetch price history")

        adj_close = chart['indicators']['adjclose'][0]['adjclose']
        timestamps = chart['timestamp']
        history = []
        for t, c in zip(timestamps, adj_close):
            if c: history.append({"Close": c, "Date": t})
            
        sim_result = simulation.run_monte_carlo(history, simulations=5000)
        
        summary = {
            "current_price": history[-1]['Close'],
            "projected_p50": sim_result['p50'][-1],
            "projected_p90_upside": sim_result['p90'][-1],
            "projected_p10_downside": sim_result['p10'][-1],
            "risk_value_at_risk": sim_result['risk_var'],
            "probabilities": sim_result['probabilities'],
            "volatility_annualized": sim_result['volatility']
        }

        duration = time.time() - start_time
        logger.info(f"SUCCESS: run_monte_carlo({sanitized_ticker}) - {duration:.2f}s")
        return json.dumps(summary, indent=2)

    except RuntimeError as re:
        return format_error(str(re).split(":")[0], str(re))
    except Exception as e:
        logger.error(f"FAIL: run_monte_carlo({sanitized_ticker}) - {str(e)}")
        return format_error("INTERNAL_ERROR", str(e))

@mcp.tool()
def analyze_earnings(ticker: str) -> str:
    """
    Scrape and analyze the LATEST earnings call transcript.
    Extracts: Forward Guidance, Management Confidence, and Analyst Q&A tone.
    """
    start_time = time.time()
    sanitized_ticker = ticker.strip().upper()[:10]

    try:
        guard.check_kill_switch()
        guard.check_limits("analyze_earnings")
        
        logger.info(f"START: analyze_earnings({sanitized_ticker})")
        
        db = database.SessionLocal()
        try:
            result = earnings.analyze_earnings(sanitized_ticker, db)
            
            result_str = json.dumps(result, indent=2)
            if len(result_str) > 10000:
                result_str = result_str[:10000] + "...(truncated)"
                
            duration = time.time() - start_time
            logger.info(f"SUCCESS: analyze_earnings({sanitized_ticker}) - {duration:.2f}s")
            return result_str
            
        finally:
            db.close()

    except RuntimeError as re:
        return format_error(str(re).split(":")[0], str(re))
    except Exception as e:
        logger.error(f"FAIL: analyze_earnings({sanitized_ticker}) - {str(e)}")
        return format_error("INTERNAL_ERROR", str(e))

if __name__ == "__main__":
    print(f"VinSight MCP Server Running... (Logs: {LOG_FILE})", file=sys.stderr)
    mcp.run()
