import os
import uuid
import shutil
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import User, Portfolio, PortfolioHolding, UserGoal
from services import auth
from services import portfolio_parser
from services import portfolio_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

ALLOWED_EXTENSIONS = {'.csv', '.txt'}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB


# --- Pydantic Schemas ---

class PortfolioCreate(BaseModel):
    name: str

class HoldingOut(BaseModel):
    id: int
    symbol: str
    quantity: float
    avg_cost: Optional[float]
    imported_at: Optional[datetime]

    class Config:
        from_attributes = True

class PortfolioOut(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime]
    holdings: List[HoldingOut]

    class Config:
        from_attributes = True

class InvestorProfileUpdate(BaseModel):
    risk_tolerance: Optional[str] = None       # conservative, moderate, aggressive
    time_horizon: Optional[str] = None         # "< 1 year", "1-3 years", etc.
    monthly_contribution: Optional[float] = None
    investment_goal: Optional[str] = None

class InvestorProfileOut(BaseModel):
    risk_tolerance: Optional[str]
    time_horizon: Optional[str]
    monthly_contribution: Optional[float]
    investment_goal: Optional[str]

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.post("", response_model=PortfolioOut)
async def create_portfolio(
    body: PortfolioCreate,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    """Create a new portfolio."""
    # Check for duplicate name
    existing = db.query(Portfolio).filter(
        Portfolio.user_id == user.id,
        Portfolio.name == body.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Portfolio with this name already exists")

    portfolio = Portfolio(user_id=user.id, name=body.name)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.get("", response_model=List[PortfolioOut])
async def list_portfolios(
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    """List all portfolios for the current user."""
    portfolios = db.query(Portfolio).filter(
        Portfolio.user_id == user.id
    ).order_by(Portfolio.created_at).all()
    return portfolios


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    """Delete a portfolio and all its holdings."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    db.delete(portfolio)  # Cascade deletes holdings
    db.commit()
    return {"status": "deleted", "id": portfolio_id}


@router.post("/{portfolio_id}/import", response_model=PortfolioOut)
async def import_portfolio_csv(
    portfolio_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    """Upload a CSV file to import holdings into a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Validate file extension
    file_ext = os.path.splitext(file.filename or '')[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum: {MAX_UPLOAD_SIZE // 1024}KB")

    # Save to temp file
    temp_dir = "/tmp/vinsight_portfolio_imports"
    os.makedirs(temp_dir, exist_ok=True)
    safe_filename = f"{uuid.uuid4()}{file_ext}"
    temp_file = os.path.join(temp_dir, safe_filename)

    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        parsed = portfolio_parser.parse_portfolio_csv(temp_file)
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    if not parsed:
        raise HTTPException(
            status_code=400, 
            detail="No valid holdings found in file. Supported formats: Fidelity, Schwab, Robinhood, or any CSV with 'Symbol' and 'Quantity' columns."
        )

    # Clear existing holdings for this portfolio, then insert new ones
    db.query(PortfolioHolding).filter(
        PortfolioHolding.portfolio_id == portfolio_id
    ).delete()

    for h in parsed:
        holding = PortfolioHolding(
            portfolio_id=portfolio_id,
            symbol=h['symbol'],
            quantity=h['quantity'],
            avg_cost=h.get('avg_cost')
        )
        db.add(holding)

    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.delete("/{portfolio_id}/holdings")
async def clear_holdings(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    """Clear all holdings from a portfolio (keep portfolio itself)."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    db.query(PortfolioHolding).filter(
        PortfolioHolding.portfolio_id == portfolio_id
    ).delete()
    db.commit()
    return {"status": "cleared", "portfolio_id": portfolio_id}


@router.get("/{portfolio_id}/profile", response_model=InvestorProfileOut)
async def get_investor_profile(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    """Get the investor profile for a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return InvestorProfileOut(
        risk_tolerance=portfolio.risk_tolerance,
        time_horizon=portfolio.time_horizon,
        monthly_contribution=portfolio.monthly_contribution,
        investment_goal=portfolio.investment_goal,
    )


@router.put("/{portfolio_id}/profile", response_model=InvestorProfileOut)
async def update_investor_profile(
    portfolio_id: int,
    body: InvestorProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    """Update the investor profile for a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    VALID_RISK = {"conservative", "moderate", "aggressive"}
    VALID_HORIZON = {"< 1 year", "1-3 years", "3-5 years", "5-10 years", "10+ years"}

    if body.risk_tolerance is not None:
        if body.risk_tolerance.lower() not in VALID_RISK:
            raise HTTPException(status_code=400, detail=f"risk_tolerance must be one of: {', '.join(VALID_RISK)}")
        portfolio.risk_tolerance = body.risk_tolerance.lower()
    if body.time_horizon is not None:
        if body.time_horizon not in VALID_HORIZON:
            raise HTTPException(status_code=400, detail=f"time_horizon must be one of: {', '.join(VALID_HORIZON)}")
        portfolio.time_horizon = body.time_horizon
    if body.monthly_contribution is not None:
        portfolio.monthly_contribution = body.monthly_contribution
    if body.investment_goal is not None:
        portfolio.investment_goal = body.investment_goal[:500]  # Cap length

    # Invalidate cached summary since profile changed
    portfolio.last_summary_at = None
    portfolio.last_summary_text = None

    db.commit()
    db.refresh(portfolio)
    return InvestorProfileOut(
        risk_tolerance=portfolio.risk_tolerance,
        time_horizon=portfolio.time_horizon,
        monthly_contribution=portfolio.monthly_contribution,
        investment_goal=portfolio.investment_goal,
    )


@router.get("/{portfolio_id}/summary")
async def get_portfolio_summary(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(auth.get_current_user)
):
    """Generate AI Portfolio Manager analysis for a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if not portfolio.holdings:
        return {"text": "No holdings to analyze. Import a CSV first.", "model": "System"}

    # Check cache (reuse if < 30 min old)
    from datetime import timedelta
    if (portfolio.last_summary_at
            and portfolio.last_summary_text
            and (datetime.utcnow() - portfolio.last_summary_at) < timedelta(minutes=30)):
        return {
            "text": portfolio.last_summary_text,
            "model": portfolio.last_summary_source or "Cached",
            "last_summary_at": portfolio.last_summary_at
        }

    # Enrich with live prices
    from services import finance
    symbols = [h.symbol for h in portfolio.holdings]

    try:
        live_data = finance.get_batch_stock_details(symbols)
    except Exception as e:
        logger.error(f"Failed to fetch live prices: {e}")
        live_data = []

    live_map = {}
    for item in live_data:
        if isinstance(item, dict) and 'symbol' in item:
            live_map[item['symbol']] = item

    holdings_data = []
    for h in portfolio.holdings:
        info = live_map.get(h.symbol, {})
        holdings_data.append({
            'symbol': h.symbol,
            'quantity': h.quantity,
            'avg_cost': h.avg_cost,
            'currentPrice': info.get('currentPrice') or info.get('regularMarketPrice') or 0,
            'sector': info.get('sector', 'N/A'),
            'companyName': info.get('shortName') or info.get('companyName', h.symbol)
        })

    # Fetch explicit user goals
    user_goals = db.query(UserGoal).filter(UserGoal.user_id == user.id).all()
    goals_list = [{"name": g.name, "amount": g.target_amount, "date": g.target_date.isoformat() if g.target_date else "N/A", "priority": g.priority} for g in user_goals]

    # Build investor profile context (per-portfolio overrides → user defaults)
    investor_profile = {
        'risk_tolerance': portfolio.risk_tolerance or user.risk_appetite,
        'time_horizon': portfolio.time_horizon or user.default_horizon,
        'monthly_contribution': portfolio.monthly_contribution or user.monthly_budget,
        'investment_goal': portfolio.investment_goal,
        'user_goals': goals_list
    }

    result = portfolio_summary.generate_portfolio_summary(portfolio.name, holdings_data, investor_profile)

    # Cache
    portfolio.last_summary_at = datetime.utcnow()
    portfolio.last_summary_text = result['text']
    portfolio.last_summary_source = result['model']
    db.commit()

    return {
        "text": result['text'],
        "model": result['model'],
        "last_summary_at": portfolio.last_summary_at
    }
