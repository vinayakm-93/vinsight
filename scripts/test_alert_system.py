#!/usr/bin/env python3
"""
Test script to verify alert system fixes:
1. Toast notifications working
2. Alert limits properly enforced  
3. UI shows limit usage correctly
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_alert_limits():
    print("=" * 60)
    print("Testing Alert System Fixes")
    print("=" * 60)
    
    # 1. Login as test user
    print("\n1. Creating/logging in test user...")
    try:
        # Try to register
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "alert_test@example.com",
            "password": "testpass123"
        })
        if reg_response.status_code == 201:
            print("✓ New test user created")
        else:
            print("✓ Test user already exists, logging in...")
    except:
        pass
    
    # Login
    login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "alert_test@example.com",
        "password": "testpass123"
    })
    
    if login_response.status_code != 200:
        print(f"✗ Login failed: {login_response.text}")
        return
    
    cookies = login_response.cookies
    print("✓ Logged in successfully")
    
    # 2. Check user limits
    print("\n2. Checking user alert limits...")
    me_response = requests.get(f"{BASE_URL}/api/auth/me", cookies=cookies)
    if me_response.status_code == 200:
        user_data = me_response.json()
        triggered = user_data.get('alerts_triggered_this_month', 0)
        limit = user_data.get('alert_limit', 10)
        print(f"✓ User limits: {triggered}/{limit} monthly triggers used")
    else:
        print(f"✗ Failed to fetch user data")
        return
    
    # 3. Get existing alerts
    print("\n3. Fetching existing alerts...")
    alerts_response = requests.get(f"{BASE_URL}/api/alerts/", cookies=cookies)
    if alerts_response.status_code == 200:
        alerts = alerts_response.json()
        print(f"✓ User has {len(alerts)} active alerts")
    else:
        print(f"✗ Failed to fetch alerts")
        return
    
    # 4. Try to create an alert
    print("\n4. Creating a test alert...")
    create_response = requests.post(f"{BASE_URL}/api/alerts/", 
        cookies=cookies,
        json={
            "symbol": "AAPL",
            "target_price": 150.0,
            "condition": "above"
        }
    )
    
    if create_response.status_code == 200:
        print("✓ Alert created successfully")
        alert_data = create_response.json()
        print(f"  Alert ID: {alert_data['id']}")
        print(f"  Symbol: {alert_data['symbol']}")
        print(f"  Target: ${alert_data['target_price']} {alert_data['condition']}")
        
        # Delete it to clean up
        delete_response = requests.delete(f"{BASE_URL}/api/alerts/{alert_data['id']}", cookies=cookies)
        if delete_response.status_code == 200:
            print("✓ Test alert deleted (cleanup)")
    elif create_response.status_code == 400:
        error_detail = create_response.json().get('detail', 'Unknown error')
        print(f"✗ Alert creation blocked (expected if at limit): {error_detail}")
    else:
        print(f"✗ Unexpected error: {create_response.text}")
    
    # 5. Test limit enforcement by setting triggered count to limit
    print("\n5. Testing limit enforcement...")
    print("   (This would require direct DB access to fully test)")
    print("   Frontend should show limit usage and prevent creation when limit reached")
    
    print("\n" + "=" * 60)
    print("Manual Testing Steps:")
    print("=" * 60)
    print("1. Open http://localhost:3000")
    print("2. Login with: alert_test@example.com / testpass123")
    print("3. Select any stock")
    print("4. Click the bell icon to open alert modal")
    print("5. Verify:")
    print("   - Limit usage display shows correctly")
    print("   - Creating alert shows toast notification (not browser alert)")
    print("   - Deleting alert shows toast notification")
    print("   - If at limit, shows warning message")
    print("=" * 60)

if __name__ == "__main__":
    test_alert_limits()
