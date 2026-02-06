from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
from pydantic import BaseModel
import shutil
import os
import uuid
import logging
from database import get_db
from services import importer, finance, watchlist_summary, finnhub_news
import concurrent.futures
import logging

logger = logging.getLogger(__name__)

# Constants for file upload security
MAX_UPLOAD_SIZE = 1024 * 1024  # 1MB
ALLOWED_EXTENSIONS = {'.csv', '.txt'}

router = APIRouter(prefix="/api/watchlists", tags=["watchlist"])

# Pydantic models
class StockAdd(BaseModel):
    symbol: str

class StockMove(BaseModel):
    symbol: str
    target_watchlist_id: int

class WatchlistCreate(BaseModel):
    name: str

class WatchlistOut(BaseModel):
    id: int
    name: str
    stocks: List[str]
    position: int = 0

    class Config:
        from_attributes = True

# ... imports
from services import importer, auth
from models import Watchlist, Stock, User

class ReorderWatchlists(BaseModel):
    ids: List[int]

class ReorderStocks(BaseModel):
    symbols: List[str]

@router.get("", response_model=List[WatchlistOut])
@router.get("/", response_model=List[WatchlistOut])
def get_watchlists(db: Session = Depends(get_db), user: Optional[User] = Depends(auth.get_current_user_optional)):
    logger.info(f"GET /watchlists called. User: {user.email if user else 'None'}")
    
    if not user:
        logger.info("No user authenticated, returning empty list")
        return []

    watchlists = db.query(Watchlist).filter(Watchlist.user_id == user.id).order_by(Watchlist.position.asc()).all()
    logger.info(f"Found {len(watchlists)} watchlists for user {user.id}")
    
    # Self-healing: If no watchlists exist, create a default one
    if not watchlists:
        logger.info(f"No watchlists found for user {user.id}, creating default watchlist")
        try:
            default_watchlist = Watchlist(
                name="My First List",
                user_id=user.id,
                stocks="AAPL,NVDA,GOOGL,MSFT,TSLA"
            )
            db.add(default_watchlist)
            db.commit()
            db.refresh(default_watchlist)
            watchlists = [default_watchlist]
            logger.info(f"Created default watchlist id={default_watchlist.id} for user {user.id}")
        except Exception as e:
            logger.exception(f"Failed to create default watchlist for user {user.id}: {e}")
            db.rollback()
    
    results = []
    for w in watchlists:
        stock_list = w.stocks.split(",") if w.stocks else []
        stock_list = [s for s in stock_list if s] 
        results.append(WatchlistOut(id=w.id, name=w.name, stocks=stock_list, position=w.position))
    return results

@router.post("", response_model=WatchlistOut)
@router.post("/", response_model=WatchlistOut)
def create_watchlist(watchlist: WatchlistCreate, db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    logger.info(f"POST /watchlists called. User: {user.id}, Name: {watchlist.name}")
    
    # Check for duplicate name for this user
    existing = db.query(Watchlist).filter(Watchlist.user_id == user.id, Watchlist.name == watchlist.name).first()
    if existing:
        logger.warning(f"Duplicate watchlist name '{watchlist.name}' for user {user.id}")
        raise HTTPException(status_code=400, detail="Watchlist with this name already exists")

    try:
        db_watchlist = Watchlist(name=watchlist.name, user_id=user.id)
        db.add(db_watchlist)
        db.commit()
        db.refresh(db_watchlist)
        logger.info(f"Created watchlist id={db_watchlist.id} for user {user.id}")
        return WatchlistOut(id=db_watchlist.id, name=db_watchlist.name, stocks=[], position=db_watchlist.position)
    except Exception as e:
        logger.exception(f"Failed to create watchlist for user {user.id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create watchlist")

@router.delete("/{watchlist_id}")
def delete_watchlist(watchlist_id: int, db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    db_watchlist = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not db_watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    db.delete(db_watchlist)
    db.commit()
    return {"status": "success", "id": watchlist_id}

@router.post("/{watchlist_id}/add", response_model=WatchlistOut)
def add_stock_to_watchlist(watchlist_id: int, stock: StockAdd, db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    db_watchlist = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not db_watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    current_stocks = db_watchlist.stocks.split(",") if db_watchlist.stocks else []
    if stock.symbol not in current_stocks:
        current_stocks.append(stock.symbol)
        db_watchlist.stocks = ",".join(current_stocks)
        db.commit()
    
    db.refresh(db_watchlist)
    stock_list = db_watchlist.stocks.split(",") if db_watchlist.stocks else []
    stock_list = [s for s in stock_list if s]
    return WatchlistOut(id=db_watchlist.id, name=db_watchlist.name, stocks=stock_list, position=db_watchlist.position)

@router.delete("/{watchlist_id}/remove/{symbol}", response_model=WatchlistOut)
def remove_stock_from_watchlist(watchlist_id: int, symbol: str, db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    db_watchlist = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not db_watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
        
    current_stocks = db_watchlist.stocks.split(",") if db_watchlist.stocks else []
    if symbol in current_stocks:
        current_stocks.remove(symbol)
        db_watchlist.stocks = ",".join(current_stocks)
        db.commit()
        
    db.refresh(db_watchlist)
    stock_list = db_watchlist.stocks.split(",") if db_watchlist.stocks else []
    stock_list = [s for s in stock_list if s]
    return WatchlistOut(id=db_watchlist.id, name=db_watchlist.name, stocks=stock_list, position=db_watchlist.position)

@router.post("/{watchlist_id}/move", response_model=WatchlistOut)
def move_stock(watchlist_id: int, move: StockMove, db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    # 1. Remove from source
    source_wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not source_wl:
         raise HTTPException(status_code=404, detail="Source watchlist not found")
         
    source_stocks = source_wl.stocks.split(",") if source_wl.stocks else []
    if move.symbol in source_stocks:
        source_stocks.remove(move.symbol)
        source_wl.stocks = ",".join(source_stocks)
        
    # 2. Add to target
    target_wl = db.query(Watchlist).filter(Watchlist.id == move.target_watchlist_id, Watchlist.user_id == user.id).first()
    if not target_wl:
        # Rollback source change if key target missing? Ideally transaction.
        # For MVP, just fail. (Source technically modified in object but not committed yet if we use same session transaction? valid.)
        raise HTTPException(status_code=404, detail="Target watchlist not found")
        
    target_stocks = target_wl.stocks.split(",") if target_wl.stocks else []
    if move.symbol not in target_stocks:
        target_stocks.append(move.symbol)
        target_wl.stocks = ",".join(target_stocks)
        
    db.commit()
    db.refresh(source_wl)
    
    stock_list = source_wl.stocks.split(",") if source_wl.stocks else []
    stock_list = [s for s in stock_list if s]
    return WatchlistOut(id=source_wl.id, name=source_wl.name, stocks=stock_list, position=source_wl.position)

@router.post("/reorder")
def reorder_watchlists(data: ReorderWatchlists, db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    """Reorder watchlists for the current user."""
    for index, watchlist_id in enumerate(data.ids):
        db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).update({"position": index})
    db.commit()
    return {"status": "success"}

@router.post("/{watchlist_id}/reorder")
def reorder_stocks(watchlist_id: int, data: ReorderStocks, db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    """Reorder stocks within a specific watchlist."""
    db_watchlist = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not db_watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    # Update the stocks field with the new order
    db_watchlist.stocks = ",".join(data.symbols)
    db.commit()
    return {"status": "success"}

@router.post("/{watchlist_id}/import", response_model=WatchlistOut)
async def import_stocks(watchlist_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    db_watchlist = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == user.id).first()
    if not db_watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    # Security: Validate file extension
    file_ext = os.path.splitext(file.filename or '')[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Security: Use safe temp directory with UUID filename
    temp_dir = "/tmp/vinsight_imports"
    os.makedirs(temp_dir, exist_ok=True)
    safe_filename = f"{uuid.uuid4()}{file_ext}"
    temp_file = os.path.join(temp_dir, safe_filename)
    
    # Security: Check file size before reading
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE // 1024}KB")
    
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        symbols = importer.parse_import_file(temp_file)
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
    if not symbols:
         raise HTTPException(status_code=400, detail="No valid symbols found in file")

    current_stocks = db_watchlist.stocks.split(",") if db_watchlist.stocks else []
    
    added_count = 0
    for s in symbols:
        if s not in current_stocks:
            current_stocks.append(s)
            added_count += 1
            
    if added_count > 0:
        db_watchlist.stocks = ",".join(current_stocks)
        db.commit()
        db.refresh(db_watchlist)

    stock_list = db_watchlist.stocks.split(",") if db_watchlist.stocks else []
    stock_list = [s for s in stock_list if s]
    return WatchlistOut(id=db_watchlist.id, name=db_watchlist.name, stocks=stock_list)

@router.get("/{watchlist_id}/summary")
def get_watchlist_summary(
    watchlist_id: int, 
    refresh: bool = False,
    symbols: Optional[str] = None, # For Guest Watchlists (virtual)
    db: Session = Depends(get_db), 
    user: Optional[User] = Depends(auth.get_current_user_optional),
    request: Request = None
):
    """
    Get or generate an AI summary for a watchlist.
    Rate limited to 1 hour per refresh, unless user is VIP.
    """
    # 1. Fetch Watchlist
    db_watchlist = None
    if watchlist_id == -1:
        # Virtual Guest Watchlist
        from services.disk_cache import DiskCache
        guest_cache = DiskCache("guest_summaries")
        guest_uuid = request.headers.get("X-Guest-UUID", "anonymous")
        cache_key = f"summary_{guest_uuid}"
        
        # Load virtual watchlist data from request or default
        # The frontend sends standard symbols for ID -1
        # For refresh, we'll generate. For non-refresh, we check cache.
        
        cached_data = guest_cache.get(cache_key)
        
        # Mock a DB object for cleaner logic downstream
        class VirtualWatchlist:
            def __init__(self, name, stocks, last_summary_at=None, last_summary_text=None, last_summary_stocks=None):
                self.id = -1
                self.name = name
                self.stocks = stocks
                self.last_summary_at = last_summary_at
                self.last_summary_text = last_summary_text
                self.last_summary_stocks = last_summary_stocks

        if cached_data:
            db_watchlist = VirtualWatchlist(
                name="Guest Watchlist",
                stocks=symbols or cached_data.get('stocks', ""), # Use provided symbols or cached
                last_summary_at=cached_data.get('at'),
                last_summary_text=cached_data.get('text'),
                last_summary_stocks=cached_data.get('stocks')
            )
        else:
            db_watchlist = VirtualWatchlist("Guest Watchlist", symbols or "AAPL,NVDA,MSFT")
    else:
        query = db.query(Watchlist).filter(Watchlist.id == watchlist_id)
        if user:
            query = query.filter(Watchlist.user_id == user.id)
        db_watchlist = query.first()

    if not db_watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found or unauthorized")

    # 2. Check VIP Status
    is_vip = False
    if user and user.is_vip:
        is_vip = True
    
    # 3. Check for existing summary and recent refresh
    now = datetime.datetime.utcnow() # Naive UTC for DB compatibility
    cooldown_seconds = 3600 # 1 hour
    
    can_refresh = True
    time_left = 0
    
    if db_watchlist.last_summary_at:
        elapsed = (now - db_watchlist.last_summary_at).total_seconds()
        if elapsed < cooldown_seconds and not is_vip:
            can_refresh = False
            time_left = int(cooldown_seconds - elapsed)

    # 4. Generate if requested and allowed, or if no summary exists
    should_generate = False
    if refresh:
        if can_refresh:
            should_generate = True
        else:
            # If user wants refresh but is rate limited, we return the existing one with a warning
            pass 
    elif not db_watchlist.last_summary_text:
        # First time generation is allowed if it was never generated
        # or we can apply the same rate limit to first-time generation to prevent burst (unlikely problem)
        should_generate = True

    if should_generate:
        logger.info(f"Generating new AI summary for watchlist {watchlist_id}")
        
        # Get Stock Data
        symbols_list = db_watchlist.stocks.split(",") if db_watchlist.stocks else []
        symbols_list = [s.strip() for s in symbols_list if s.strip()]
        
        if not symbols_list:
            raise HTTPException(status_code=400, detail="Cannot summarize an empty watchlist")
            
        stocks_data = finance.get_batch_stock_details(symbols_list)
        
        # Prepare Movers (Top 3 Gainers / Bottom 3 Losers)
        stocks_with_change = [s for s in stocks_data if s.get('regularMarketChangePercent') is not None]
        sorted_stocks = sorted(stocks_with_change, key=lambda x: x['regularMarketChangePercent'], reverse=True)
        
        top_movers = sorted_stocks[:3]
        bottom_movers = sorted_stocks[-3:] if len(sorted_stocks) > 3 else []
        movers_symbols = list(set([s['symbol'] for s in top_movers + bottom_movers]))
        
        # Parallel News Fetching for Movers
        news_results = {}
        sources_used = set()
        
        def fetch_enriched_news(symbol):
            # 1. Finnhub (Detailed)
            fh_data = finnhub_news.fetch_company_news(symbol, days=3)
            articles = fh_data.get('latest', []) + fh_data.get('historical', [])
            if articles:
                sources_used.add("Finnhub")
                return articles[:5]
            
            # 2. Yahoo (Fallback)
            try:
                y_news = finance.get_news(symbol)
                if y_news:
                    sources_used.add("Yahoo Finance")
                    return y_news[:5]
            except:
                pass
            return []

        if movers_symbols:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(movers_symbols), 6)) as executor:
                future_to_symbol = {executor.submit(fetch_enriched_news, sym): sym for sym in movers_symbols}
                for future in concurrent.futures.as_completed(future_to_symbol):
                    sym = future_to_symbol[future]
                    try:
                        news_results[sym] = future.result()
                    except Exception as e:
                        logger.error(f"Failed to fetch news for {sym}: {e}")
        
        # Call AI Service with News
        ai_data = watchlist_summary.generate_watchlist_summary(
            db_watchlist.name, 
            stocks_data, 
            news_data=news_results
        )
        summary_text = ai_data["text"]
        model_name = ai_data["model"]
        
        # Update DB or Cache
        if db_watchlist.id == -1:
            from services.disk_cache import DiskCache
            guest_cache = DiskCache("guest_summaries")
            guest_uuid = request.headers.get("X-Guest-UUID", "anonymous")
            cache_key = f"summary_{guest_uuid}"
            guest_cache.set(cache_key, {
                "text": summary_text,
                "at": now,
                "stocks": ",".join(symbols_list)
            })
            # Sync back to virtual object for return
            db_watchlist.last_summary_text = summary_text
            db_watchlist.last_summary_at = now
        else:
            db_watchlist.last_summary_text = summary_text
            db_watchlist.last_summary_at = now
            db_watchlist.last_summary_stocks = ",".join(symbols_list)
            db.commit()
            db.refresh(db_watchlist)
        
        source_label = " & ".join(sorted(list(sources_used))) if sources_used else "Technical Metrics"
        
        return {
            "summary": db_watchlist.last_summary_text,
            "last_summary_at": db_watchlist.last_summary_at.isoformat() + "Z" if db_watchlist.last_summary_at else None,
            "symbols": symbols_list,
            "refreshed": True,
            "source": f"Research Node: {source_label} | {model_name}"
        }

    # 5. Return existing summary
    return {
        "summary": db_watchlist.last_summary_text,
        "last_summary_at": db_watchlist.last_summary_at.isoformat() + "Z" if db_watchlist.last_summary_at else None,
        "symbols": db_watchlist.last_summary_stocks.split(",") if db_watchlist.last_summary_stocks else [],
        "refreshed": False,
        "cooldown_remaining": time_left if refresh and not can_refresh else 0,
        "source": "Market Intelligence"
    }
