# Yahoo Finance Rate Limit RCA

**Date:** 2026-02-01  
**Issue:** Stocks failing to load with "Too Many Requests" error  
**Status:** Resolved ✅

---

## Symptoms
- All stock data showing "Loading..." indefinitely
- Backend logs showing: `Error fetching XXXX: Too Many Requests. Rate limited. Try after a while.`
- HTTP 429 responses from Yahoo Finance API

## Root Cause

Yahoo Finance's `query1.finance.yahoo.com` endpoint aggressively rate-limits requests that:

1. **Lack a proper User-Agent header** - The `yfinance` library sends a Python user-agent which Yahoo blocks
2. **Originate from the same IP in rapid succession** - Dashboard loads 9+ tickers simultaneously, each making 4+ API calls

The `yfinance` library uses `query1.finance.yahoo.com` which is more strictly rate-limited than `query2.finance.yahoo.com`.

## Solution

Created a fallback client (`yahoo_client.py`) that:

1. **Uses `query2.finance.yahoo.com`** - Less rate-limited endpoint
2. **Sends browser User-Agent** - Mimics Chrome browser requests
3. **Implements caching** - 1-hour TTL to reduce API calls

### Files Modified

| File | Change |
|:---|:---|
| `backend/services/yahoo_client.py` | **NEW** - Direct Yahoo API client with proper headers |
| `backend/services/finance.py` | Added fallback to yahoo_client when yfinance fails |
| `backend/routes/data.py` | Added User-Agent session for yfinance calls |

### Key Code

```python
# yahoo_client.py
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'

_session = requests.Session()
_session.headers.update({'User-Agent': USER_AGENT})

def get_chart_data(ticker: str, interval: str = "1d", range_: str = "1y"):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    response = _session.get(url, params={"interval": interval, "range": range_})
    return response.json()
```

## Prevention

1. **Always use browser User-Agent** for Yahoo Finance requests
2. **Prefer `query2` over `query1`** endpoint
3. **Implement request throttling** - Max 3 requests/second
4. **Add aggressive caching** - Reduce redundant API calls
5. **Graceful fallback** - Don't fail completely on rate limit

## Timeline

| Time | Event |
|:---|:---|
| 15:22 | User reported "Loading..." for all stocks |
| 15:28 | Confirmed Yahoo Finance returning 429 |
| 15:57 | Discovered `query2` endpoint works with browser User-Agent |
| 16:03 | Created `yahoo_client.py` with fallback |
| 16:07 | Verified fix - ORCL and JHJRX loading correctly |

---

## Update: Feb 2026 - `curl_cffi` Security Update
Yahoo Finance updated their backend security to require TLS fingerprinting via `curl_cffi`. Standard `requests` sessions are now flagged and blocked even with a valid User-Agent.

### Resolution
- **Removed custom sessions**: All `session=yf_session` parameters were removed from `yfinance.Ticker` calls.
- **Library Autonomy**: Allowing `yfinance` to manage its own session ensures it uses its internal `curl_cffi` implementation, which successfully bypasses the new security checks.
- **Impact**: Restored full access to institutional, insider, and news data.
