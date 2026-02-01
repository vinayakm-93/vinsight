from fastapi import APIRouter, HTTPException, Query
from services.analysis import analyze_sentiment_ondemand
from pydantic import BaseModel
from typing import List, Optional, Any

router = APIRouter()

class NewsItem(BaseModel):
    title: str
    summary: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    date_str: Optional[str] = None

class SentimentResponse(BaseModel):
    score_today: float
    score_weekly: float
    reasoning: str
    key_drivers: List[str]
    news_flow: Any
    article_count: int
    timestamp: str
    source: str

@router.get("/analyze")
async def get_sentiment_analysis(ticker: str = Query(..., description="Stock Ticker Symbol")):
    """
    Trigger on-demand sentiment analysis (Finnhub + Groq) with caching.
    """
    try:
        result = analyze_sentiment_ondemand(ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
