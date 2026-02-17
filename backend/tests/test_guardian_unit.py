import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
import os
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from main import app
from database import get_db, Base
from models import User, GuardianThesis, GuardianAlert
from services import guardian_agent, finance

# Setup In-Memory DB for Testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Helper to create test user
def create_test_user(db):
    user = User(email="unit_test@example.com", hashed_password="hashed_password", guardian_limit=10)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Helper to authenticate (Mocking get_current_user)
# We can override the dependency or just mock the token handling.
# Easiest is to override get_current_user dependency if possible, but let's see.
# Actually, let's just mock the auth dependency.
from services.auth import get_current_user

def override_get_current_user():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "unit_test@example.com").first()
    db.close()
    return user

app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    create_test_user(db)
    yield db
    Base.metadata.drop_all(bind=engine)
    db.close()

# --- Tests ---

def test_enable_guardian_success(test_db):
    # Mock LLM and Finance
    with patch('services.guardian_agent.generate_thesis_detected') as mock_gen:
        mock_gen.return_value = "Long TEST based on growth."
        
        response = client.post("/api/guardian/enable", json={"symbol": "TEST"})
        assert response.status_code == 200
        data = response.json()
        assert data["thesis"] == "Long TEST based on growth."
        assert "Guardian enabled" in data["message"]
        
        # Verify DB
        thesis = test_db.query(GuardianThesis).filter(GuardianThesis.symbol == "TEST").first()
        assert thesis is not None
        assert thesis.is_active == True
        assert thesis.thesis == "Long TEST based on growth."

def test_enable_guardian_limit(test_db):
    # Create 10 dummy theses
    user = test_db.query(User).filter(User.email == "unit_test@example.com").first()
    
    # We already have 1 from previous test? No, scope is module but tests run sequentially?
    # Pytest fixtures scope module means DB persists across tests in this file.
    # Logic: "TEST" is already added. Add 9 more.
    
    for i in range(9):
        t = GuardianThesis(user_id=user.id, symbol=f"S{i}", thesis="Dummy", is_active=True)
        test_db.add(t)
    test_db.commit()
    
    # Now we have 1 + 9 = 10 active. Next one should fail.
    
    response = client.post("/api/guardian/enable", json={"symbol": "FAIL"})
    assert response.status_code == 400
    assert "limit reached" in response.json()["detail"]

def test_disable_guardian(test_db):
    # Disable "TEST" (created in first test)
    response = client.post("/api/guardian/disable/TEST")
    assert response.status_code == 200
    
    thesis = test_db.query(GuardianThesis).filter(GuardianThesis.symbol == "TEST").first()
    assert thesis.is_active == False

def test_enable_reactivate(test_db):
    # Enable "TEST" again (it's currently disabled)
    # Counts checks: We had 10 active. Disabled 1 ("TEST"). Now 9 active.
    # Enabling "TEST" again should make it 10 active.
    
    with patch('services.guardian_agent.generate_thesis_detected') as mock_gen:
        mock_gen.return_value = "New Thesis?" # Should NOT be called for reactivation
        
        response = client.post("/api/guardian/enable", json={"symbol": "TEST"})
        assert response.status_code == 200
        assert "re-enabled" in response.json()["message"]
        
        thesis = test_db.query(GuardianThesis).filter(GuardianThesis.symbol == "TEST").first()
        assert thesis.is_active == True
        # Thesis text should NOT change on reactivation unless we decided otherwise. 
        # Current logic preserves old thesis.
        assert thesis.thesis == "Long TEST based on growth." 
        
        # Mock should not have been called
        mock_gen.assert_not_called()

def test_update_thesis(test_db):
    response = client.put("/api/guardian/theses/TEST", json={"thesis": "Updated manually."})
    assert response.status_code == 200
    
    thesis = test_db.query(GuardianThesis).filter(GuardianThesis.symbol == "TEST").first()
    assert thesis.thesis == "Updated manually."
    assert thesis.auto_generated == False

def test_get_theses(test_db):
    response = client.get("/api/guardian/theses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 10 # We added 10+
    
    # Check structure
    item = next(x for x in data if x["symbol"] == "TEST")
    assert item["thesis"] == "Updated manually."
    assert item["is_active"] == True
    assert item["status"] == "INTACT" # Default

def test_event_detection_logic():
    # Unit test for services/guardian.py without DB
    from services.guardian import detect_events
    
    # Mock finance.get_stock_info
    with patch('services.finance.get_stock_info') as mock_info:
        # Case 1: No Drop
        mock_info.return_value = {"currentPrice": 100.0, "regularMarketChangePercent": -1.0}
        result = detect_events("OKAY")
        assert result["triggered"] == False
        
        # Case 2: Price Drop > 5%
        mock_info.return_value = {"currentPrice": 90.0, "regularMarketChangePercent": -6.0}
        result = detect_events("DROP")
        assert result["triggered"] == True
        assert "Price dropped" in result["events"][0]
        
    # Mock analyst
    with patch('services.finance.get_analyst_targets') as mock_analyst:
        mock_analyst.return_value = {"recommendationKey": "sell"}
        # Need to re-patch info to return None or safe value to avoid crash
        with patch('services.finance.get_stock_info', return_value={}): 
            result = detect_events("SELL")
            assert result["triggered"] == True
            assert "Analyst consensus is now SELL" in result["events"][0]

