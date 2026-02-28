from sqlalchemy.orm import Session
from database import SessionLocal
from models import ScoreHistory
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def save_score(symbol: str, score: float, rating: str, current_price: float) -> bool:
    """
    Saves a new score to the ScoreHistory table IF:
    1. More than 24 hours have passed since the last save OR
    2. The stock price has moved more than 3% since the last recorded score.
    
    Returns True if saved, False if skipped due to throttling.
    """
    db: Session = SessionLocal()
    try:
        last_record = db.query(ScoreHistory).filter(ScoreHistory.symbol == symbol).order_by(ScoreHistory.created_at.desc()).first()
        
        save_needed = False
        
        if not last_record:
            save_needed = True # First time scoring
        else:
            time_since_last = datetime.utcnow() - last_record.created_at
            
            # Condition 1: Time Elapsed (>24 hours)
            if time_since_last > timedelta(hours=24):
                save_needed = True
            
            # Condition 2: High Volatility (Price swung > 3%)
            elif last_record.price > 0:
                price_delta = abs((current_price - last_record.price) / last_record.price)
                if price_delta > 0.03:
                    logger.info(f"Memory Service: Volatility bypass triggered for {symbol}. Price moved {price_delta:.1%}")
                    save_needed = True
                    
        if save_needed:
            new_history = ScoreHistory(
                symbol=symbol,
                score=score,
                rating=rating,
                price=current_price
            )
            db.add(new_history)
            db.commit()
            logger.info(f"Memory Service: Successfully saved history for {symbol} ({score}/100 at ${current_price})")
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Score Memory Save Error for {symbol}: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def get_history(symbol: str, limit: int = 3) -> list:
    """
    Fetches the `limit` most recent scores for a symbol to provide temporal context.
    Returns a list of dictionaries with score, rating, price, and date.
    """
    db: Session = SessionLocal()
    try:
        records = db.query(ScoreHistory).filter(ScoreHistory.symbol == symbol).order_by(ScoreHistory.created_at.desc()).limit(limit).all()
        
        history = []
        for r in records:
            history.append({
                "score": r.score,
                "rating": r.rating,
                "price": r.price,
                "date": r.created_at.strftime("%Y-%m-%d")
            })
            
        return history
    except Exception as e:
        logger.error(f"Score Memory Fetch Error for {symbol}: {e}")
        return []
    finally:
        db.close()
