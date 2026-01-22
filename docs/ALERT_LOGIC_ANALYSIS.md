# Alert System Logic Documentation

## Overview

The alert system allows users to set price alerts for stocks. When the stock price reaches the target, an email is sent to the user.

## Key Components

### 1. Alert Creation (`routes/alerts.py`)

**Flow:**
```
User creates alert → Validate → Check limits → Save to DB → Return success
```

**Validation Steps:**
1. **Monthly Reset Check** (Lines 72-81)
   - Compares `last_alert_reset` month/year with current
   - If different month → Reset `alerts_triggered_this_month` to 0
   - Update `last_alert_reset` to now

2. **Limit Checks** (Lines 83-94)
   - **Monthly Trigger Limit**: Check if user has triggered >= limit this month
   - **Active Alerts Limit**: Max 50 concurrent alerts per user
   - Throws 400 error if limits exceeded

3. **Symbol Validation** (Lines 96-102)
   - Try to fetch stock info to validate symbol exists
   - Warning logged if not found, but proceeds anyway

4. **Save Alert** (Lines 104-113)
   - Create Alert record with:
     - `user_id`
     - `symbol` (uppercase)
     - `target_price`
     - `condition` ("above" or "below")
     - `is_triggered` = False

### 2. Alert Checking (`services/alert_checker.py`)

**Triggered by:**
- Cloud Scheduler (production) - runs periodically
- Manual trigger via `/api/alerts/check` endpoint
- Job: `jobs/market_watcher_job.py`

**Flow:**
```
Fetch all active alerts → Get current prices → Check conditions → Trigger + Email
```

**Logic:**
1. **Fetch Active Alerts** (Line 12)
   ```python
   alerts = db.query(Alert).filter(Alert.is_triggered == False).all()
   ```

2. **Fetch Current Prices** (Lines 18-30)
   - Groups alerts by symbol to minimize API calls
   - Fetches price for each unique symbol
   - Tries: `currentPrice` → `regularMarketPrice` → `previousClose`

3. **Check Each Alert** (Lines 33-42)
   ```python
   if alert.condition == 'above' and current >= alert.target_price:
       triggered = True
   elif alert.condition == 'below' and current <= alert.target_price:
       triggered = True
   ```

4. **Trigger Alert** (Lines 44-63)
   - **Check user's monthly limit** (Lines 48-50)
     - If `alerts_triggered_this_month >= alert_limit` → Skip
   - Mark alert as triggered: `alert.is_triggered = True`
   - Increment user's counter: `user.alerts_triggered_this_month += 1`
   - Send email to user
   - Commit changes to DB

### 3. Monthly Limits

**Two Separate Concepts:**

1. **Monthly Trigger Limit** (`alert_limit` = 30)
   - How many alerts can **trigger/fire** in a month
   - Resets automatically on new month
   - Prevents spam emails
   - Checked when:
     - Creating new alert (prevent if already hit limit)
     - Triggering existing alert (skip if hit limit)

2. **Active Alerts Limit** (50)
   - How many **active/pending** alerts user can have
   - Hard limit at any time
   - Prevents database bloat

**Example Scenario:**
```
User has alert_limit = 30
- Creates 50 alerts (all active)
- 30 of them trigger this month → email sent, alerts_triggered = 30
- Remaining 20 alerts remain active but won't trigger this month
- Next month: counter resets to 0, those 20 can trigger
```

## Issues Found & Fixes Needed

### ❌ Issue 1: Monthly Limit Check is Wrong

**Current Logic** (Line 85 in `routes/alerts.py`):
```python
if user.alerts_triggered_this_month >= user.alert_limit:
    raise HTTPException(...)
```

**Problem:** This checks **already triggered** count when creating a NEW alert.

**Correct Logic Should Be:**
- User should be able to **create** unlimited alerts (up to 50 active limit)
- The monthly limit should only apply to **triggering** (sending emails)
- Creating an alert ≠ Triggering an alert

**Fix:** Remove the monthly trigger limit check from alert creation, keep only the active limit check.

### ✅ Issue 2: Alert Checker Logic is Correct

The `alert_checker.py` correctly:
- Only checks `is_triggered == False` alerts
- Respects monthly limit when triggering
- Increments counter only when actually triggering

### ⚠️ Issue 3: No Auto-Reset on Check

**Current:** Monthly reset only happens when creating a new alert (Line 77-81 in routes)

**Problem:** If user doesn't create alerts, their counter never resets

**Better Approach:** Reset should happen in alert_checker OR on any API call that checks limits

### 💡 Issue 4: No Way to View Limit Usage

Users can't see:
- How many alerts they've triggered this month
- When their limit resets
- How many they have left

**Current Fix:** We added this to the UI (shows X/30 in Active Alerts)

## Recommended Fixes

### 1. Remove Monthly Limit Check from Alert Creation

```python
# in routes/alerts.py, REMOVE lines 84-89
# Users should be able to create alerts freely (only check active count)
```

### 2. Add Reset Check to Alert Checker

```python
# in services/alert_checker.py, add at start of check_alerts():
def check_alerts(db: Session):
    # Reset monthly counters if new month
    users = db.query(User).filter(User.last_alert_reset != None).all()
    now = datetime.utcnow()
    for user in users:
        if user.last_alert_reset.month != now.month or user.last_alert_reset.year != now.year:
            user.alerts_triggered_this_month = 0
            user.last_alert_reset = now
    db.commit()
    
    # Then continue with alert checking...
```

### 3. Add Endpoint to Check Limit Status

```python
@router.get("/status")
def get_alert_status(db: Session, user: User = Depends(auth.get_current_user)):
    return {
        "triggered_this_month": user.alerts_triggered_this_month,
        "monthly_limit": user.alert_limit,
        "remaining": max(0, user.alert_limit - user.alerts_triggered_this_month),
        "active_alerts": db.query(Alert).filter(Alert.user_id == user.id, Alert.is_triggered == False).count(),
        "last_reset": user.last_alert_reset
    }
```

## Testing the System

### Local Testing

```bash
# 1. Create an alert
curl -X POST http://localhost:8000/api/alerts/ \
  -H "Cookie: session=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "target_price": 100.0,
    "condition": "above"
  }'

# 2. Manually trigger check
curl -X POST http://localhost:8000/api/alerts/check \
  -H "Cookie: session=YOUR_TOKEN"

# 3. Check if triggered
curl http://localhost:8000/api/alerts/ \
  -H "Cookie: session=YOUR_TOKEN"
```

### Database Queries

```sql
-- See all alerts for a user
SELECT * FROM alerts WHERE user_id = 1;

-- Check user's limit status
SELECT email, alerts_triggered_this_month, alert_limit, last_alert_reset 
FROM users WHERE id = 1;

-- See triggered alerts this month
SELECT COUNT(*) FROM alerts 
WHERE user_id = 1 AND is_triggered = true;
```

## Summary

**What's Working:**
✅ Alert creation and storage
✅ Alert checking logic (condition matching)
✅ Monthly limit enforcement during triggering
✅ Email sending

**What Needs Fixing:**
❌ Remove monthly limit check from creation endpoint
⚠️ Add auto-reset to alert checker
💡 Consider adding limit status endpoint
