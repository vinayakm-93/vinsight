from sqlalchemy.orm import Session
from ..models import Alert
from .finance import get_stock_info
from .mail import send_alert_email

async def check_alerts(db: Session):
    """
    Checks all active alerts against current market prices.
    Triggers emails if conditions are met.
    """
    print("Checking alerts...")
    alerts = db.query(Alert).filter(Alert.is_triggered == False).all()
    if not alerts:
        print("No active alerts.")
        return

    # Group by symbol to minimize API calls
    symbols = set(a.symbol for a in alerts)
    prices = {}
    
    print(f"Fetching prices for: {symbols}")
    for s in symbols:
        try:
             # This is synchronous, blocking. For production, use async fetching or threadpool.
             # For MVP, it's fine.
             info = get_stock_info(s)
             prices[s] = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        except Exception as e:
             print(f"Error fetching price for {s}: {e}")
             prices[s] = None

    triggered_count = 0
    for alert in alerts:
        current = prices.get(alert.symbol)
        if current is None:
            continue

        triggered = False
        if alert.condition == 'above' and current >= alert.target_price:
            triggered = True
        elif alert.condition == 'below' and current <= alert.target_price:
            triggered = True

        if triggered:
            user = alert.user
            if user:
                 # Check Limit
                 if user.alerts_triggered_this_month >= user.alert_limit:
                     print(f"Skipping alert for {user.email}: Monthly limit reached ({user.alerts_triggered_this_month}/{user.alert_limit})")
                     continue

                 print(f"Alert TRIGGERED: {alert.symbol} {alert.condition} {alert.target_price} (Current: {current})")
                 alert.is_triggered = True
                 triggered_count += 1
                 
                 # Increment Usage
                 user.alerts_triggered_this_month += 1
                 
                 # Send Email
                 if user.email:
                      await send_alert_email(user.email, alert.symbol, current, alert.condition, alert.target_price)
                      # We could pass limit info here if we updated send_alert_email signature to take user obj or counts
                      # user.alert_limit - user.alerts_triggered_this_month remaining
    
    if triggered_count > 0:
        db.commit()
    print(f"Alert check complete. Triggered {triggered_count} alerts.")
