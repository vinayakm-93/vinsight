from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, UniqueConstraint, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Removed alerts relation from Stock as we use symbols in Alert now

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    investing_goals = Column(String, nullable=True)
    feature_requests = Column(String, nullable=True)
    
    # Alert Limits & Tracking
    alerts_triggered_this_month = Column(Integer, default=0)
    alert_limit = Column(Integer, default=30) # Default limit: 30 alerts per month
    guardian_limit = Column(Integer, default=10) # Default limit: 10 active guardian stocks
    thesis_limit = Column(Integer, default=10) # Default limit: 10 theses per month
    theses_generated_this_month = Column(Integer, default=0)

    last_alert_reset = Column(DateTime, default=datetime.utcnow)
    is_vip = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    watchlists = relationship("Watchlist", back_populates="user")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    message = Column(String, nullable=False)
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class Watchlist(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=False, nullable=False)
    stocks = Column(String, default="") # Comma separated tickers
    position = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Nullable for guest lists/backward compatibility

    # AI Summary Fields
    last_summary_at = Column(DateTime, nullable=True)
    last_summary_text = Column(Text, nullable=True)
    last_summary_stocks = Column(String, nullable=True) # Symbols included in the summary

    user = relationship("User", back_populates="watchlists")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_watchlist_name'),
    )

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    target_price = Column(Float, nullable=False)
    condition = Column(String, nullable=False) # "above", "below"
    is_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="alerts")

class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reset_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_used = Column(Boolean, default=False)

    user = relationship("User")

class VerificationCode(Base):
    __tablename__ = "verification_codes"

    email = Column(String, primary_key=True, index=True)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class EarningsAnalysis(Base):
    __tablename__ = "earnings_analysis"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    quarter = Column(String, nullable=False)
    year = Column(String, nullable=False)
    content = Column(Text, nullable=False) # JSON string
    last_api_check = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('ticker', 'quarter', 'year', name='uq_ticker_quarter_year'),
    )

class GuardianThesis(Base):
    __tablename__ = "guardian_theses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    thesis = Column(Text, nullable=False)
    auto_generated = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    last_checked_at = Column(DateTime, nullable=True)
    last_manual_scan_at = Column(DateTime, nullable=True)
    last_price = Column(Float, nullable=True)
    check_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='uq_user_guardian_thesis'),
    )

class InvestmentThesis(Base):
    __tablename__ = "investment_theses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    
    # Tier 1 Info
    stance = Column(String, nullable=True) # BULLISH, BEARISH, NEUTRAL
    one_liner = Column(String, nullable=True)
    
    # Tier 2 Info
    key_drivers = Column(Text, nullable=True) # JSON array of strings
    primary_risk = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Tier 3 Info
    content = Column(Text, nullable=True) # Detailed analysis (markdown/HTML)
    sources = Column(Text, nullable=True) # JSON list of citations
    agent_log = Column(Text, nullable=True) # Working trace
    
    is_edited = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")

class GuardianAlert(Base):
    __tablename__ = "guardian_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    thesis_status = Column(String, nullable=False)      # INTACT / AT_RISK / BROKEN
    confidence = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    recommended_action = Column(String, nullable=True)  # HOLD / REDUCE / SELL
    key_evidence = Column(Text, nullable=True)          # JSON string
    events_detected = Column(Text, nullable=True)       # JSON string
    research_history = Column(Text, nullable=True)      # JSON string - full agent search trail
    thinking_log = Column(Text, nullable=True)          # JSON string - internal agent thought trace
    is_read = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # AI Summary Fields (mirrors Watchlist pattern)
    last_summary_at = Column(DateTime, nullable=True)
    last_summary_text = Column(Text, nullable=True)
    last_summary_source = Column(String, nullable=True)

    user = relationship("User", back_populates="portfolios")
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_portfolio_name'),
    )

class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    quantity = Column(Float, nullable=False, default=0)
    avg_cost = Column(Float, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="holdings")

    __table_args__ = (
        UniqueConstraint('portfolio_id', 'symbol', name='uq_portfolio_symbol'),
    )

class ScoreHistory(Base):
    __tablename__ = "score_history"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    score = Column(Float, nullable=False)
    rating = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SecSummary(Base):
    __tablename__ = "sec_summaries"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    business_description = Column(Text, nullable=True)
    risk_factors_10k = Column(Text, nullable=True)
    legal_proceedings = Column(Text, nullable=True)
    mda = Column(Text, nullable=True)
    latest_10q_delta = Column(Text, nullable=True)
    latest_10k_date = Column(String, nullable=True)
    latest_10q_date = Column(String, nullable=True)
    last_updated_at = Column(DateTime, default=datetime.utcnow)

