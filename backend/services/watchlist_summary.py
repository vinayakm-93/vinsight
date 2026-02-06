import os
import logging
import json
import google.generativeai as genai
from typing import List, Dict

logger = logging.getLogger(__name__)

def generate_watchlist_summary(watchlist_name: str, stocks_data: List[Dict], news_data: Dict[str, List[Dict]] = None) -> Dict:
    """
    Generate an AI-powered summary of a watchlist using Gemini 2.0 Flash.
    Includes news catalysts for top/bottom performers if provided.
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        logger.error("No Gemini API key found for watchlist summary.")
        return {
            "text": "AI Summary unavailable (API key missing). Please configure GEMINI_API_KEY.",
            "model": "System"
        }

    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        
        # 1. Format Stock Metrics
        formatted_stocks = []
        for stock in stocks_data:
            price = f"${stock.get('currentPrice', 0):.2f}" if isinstance(stock.get('currentPrice'), (int, float)) else "N/A"
            change = f"{stock.get('regularMarketChangePercent', 0):.2f}%" if isinstance(stock.get('regularMarketChangePercent'), (int, float)) else "N/A"
            pe = f"{stock.get('trailingPE', 0):.1f}x" if isinstance(stock.get('trailingPE'), (int, float)) else "N/A"
            perf_ytd = f"{stock.get('ytdChangePercent', 0):.1f}%" if isinstance(stock.get('ytdChangePercent'), (int, float)) else "N/A"

            formatted_stocks.append(f"- **{stock['symbol']}**: {price} ({change}) | P/E: {pe} | YTD: {perf_ytd} | Sector: {stock.get('sector', 'N/A')}")
        
        # 2. Format News Catalysts
        news_str = ""
        if news_data:
            news_sections = []
            for ticker, articles in news_data.items():
                if not articles: continue
                article_texts = []
                for art in articles[:3]: # Cap at 3 for prompt density
                    headline = art.get('title', art.get('headline', 'No Title'))
                    summary = art.get('summary', '')
                    article_texts.append(f"  - {headline}" + (f": {summary[:200]}..." if summary else ""))
                
                news_sections.append(f"### {ticker} News Catalysts:\n" + "\n".join(article_texts))
            
            if news_sections:
                news_str = "\n\n## RECENT NEWS & CATALYSTS\n" + "\n".join(news_sections)

        formatted_stocks_str = "\n".join(formatted_stocks)
        prompt = f"""
You are the Executive Research Director at a premier quantitative hedge fund. 
Provide a high-conviction, professional market intelligence briefing for the "{watchlist_name}" watchlist.

### REAL-TIME PORTFOLIO DATA
{formatted_stocks_str}
{news_str}

### STRICT INSTRUCTIONS:
1. **Thematic Intelligence**: Synthesize the watchlist into 1-2 core investment themes based on current sector exposure.
2. **Movers & Catalysts**: Analyze the Top 3 Gainers and Bottom 3 Losers. Use news to explain the specific drivers (e.g., "Yield curve compression impacting financials", "NVDA earnings pull-through").
3. **Valuation Pulse**: Flag outliers in PEG ratios or P/E vs industry medians with professional skepticism.
4. **Research Conclusion**: Provide 3 data-driven, actionable intelligence points. Use terms like "Relative Strength", "Mean Reversion", or "Concentration Risk".

### STYLE RULES:
- **NO Generic Filler**: Avoid phrases like "mixed signals" or "market is showing". Be decisive.
- **Tone**: Sophisticated, cynical, and institutional-grade.
- **Brevity**: Maximum 250 words.
- **Formatting**: Use MARKDOWN headers (`##`, `###`). Avoid plain text section titles.
- **Data Highlighting (CRITICAL)**: You MUST wrap EVERY instance of the following in double asterisks `**`:
    - All Tickers: e.g., **NVDA**, **AAPL**, **TSLA**
    - All Percentages: e.g., **+5.2%**, **(-1.2%)**, **26.2% YTD**
    - All Valuations: e.g., **22.5x P/E**, **371.2x**
    - Failure to bold these will result in poor UI rendering.

RESPOND IN MARKDOWN ONLY.
"""
        
        response = model.generate_content(prompt)
        if response and response.text:
            return {
                "text": response.text,
                "model": "Gemini 2.0 Flash"
            }
        return {
            "text": "AI Summary generated an empty response.",
            "model": "Gemini 2.0 Flash"
        }
        
    except Exception as e:
        logger.error(f"Gemini summary generation failed: {e}")
        return {
            "text": f"AI Summary failed to generate: {str(e)}",
            "model": "Gemini 2.0 Flash"
        }
