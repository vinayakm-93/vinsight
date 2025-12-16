from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import shutil
import os
import uuid
import logging
from database import get_db
from models import Watchlist, Stock
from services import importer

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

    class Config:
        from_attributes = True

# ... imports
from services import importer, auth
from models import Watchlist, Stock, User

# ...

@router.get("/", response_model=List[WatchlistOut])
def get_watchlists(db: Session = Depends(get_db), user: Optional[User] = Depends(auth.get_current_user_optional)):
    if not user:
        return []
        
    watchlists = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()
    results = []
    for w in watchlists:
        stock_list = w.stocks.split(",") if w.stocks else []
        stock_list = [s for s in stock_list if s] 
        results.append(WatchlistOut(id=w.id, name=w.name, stocks=stock_list))
    return results

@router.post("/", response_model=WatchlistOut)
def create_watchlist(watchlist: WatchlistCreate, db: Session = Depends(get_db), user: User = Depends(auth.get_current_user)):
    # Check for duplicate name for this user
    existing = db.query(Watchlist).filter(Watchlist.user_id == user.id, Watchlist.name == watchlist.name).first()
    if existing:
         raise HTTPException(status_code=400, detail="Watchlist with this name already exists")

    db_watchlist = Watchlist(name=watchlist.name, user_id=user.id)
    db.add(db_watchlist)
    db.commit()
    db.refresh(db_watchlist)
    return WatchlistOut(id=db_watchlist.id, name=db_watchlist.name, stocks=[])

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
    return WatchlistOut(id=db_watchlist.id, name=db_watchlist.name, stocks=stock_list)

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
    return WatchlistOut(id=db_watchlist.id, name=db_watchlist.name, stocks=stock_list)

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
    return WatchlistOut(id=source_wl.id, name=source_wl.name, stocks=stock_list)

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
