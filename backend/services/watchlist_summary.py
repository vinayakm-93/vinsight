import os
import logging
import json
import re
import google.generativeai as genai
from openai import OpenAI
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def _get_openrouter_client():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    return None

def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from DeepSeek R1 output."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def generate_watchlist_summary(watchlist_name: str, stocks_data: List[Dict], news_data: Dict[str, List[Dict]] = None) -> Dict:
    """
    Generate an AI-powered summary of a watchlist.
    Priority: DeepSeek R1 (OpenRouter) -> Gemini 2.0 Flash (Fallback)
    """
    
    # 1. Prepare Data
    formatted_stocks = []
    for stock in stocks_data:
        price = f"${stock.get('currentPrice', 0):.2f}" if isinstance(stock.get('currentPrice'), (int, float)) else "N/A"
        change = f"{stock.get('regularMarketChangePercent', 0):.2f}%" if isinstance(stock.get('regularMarketChangePercent'), (int, float)) else "N/A"
        pe = f"{stock.get('trailingPE', 0):.1f}x" if isinstance(stock.get('trailingPE'), (int, float)) else "N/A"
        fwd_pe = f"{stock.get('forwardPE', 0):.1f}x" if isinstance(stock.get('forwardPE'), (int, float)) else "N/A"
        peg = f"{stock.get('pegRatio', 0):.2f}" if isinstance(stock.get('pegRatio'), (int, float)) else "N/A"
        perf_ytd = f"{stock.get('ytdChangePercent', 0):.1f}%" if isinstance(stock.get('ytdChangePercent'), (int, float)) else "N/A"

        formatted_stocks.append(f"- **{stock['symbol']}**: {price} ({change}) | P/E: {pe} | Fwd P/E: {fwd_pe} | PEG: {peg} | YTD: {perf_ytd} | Sector: {stock.get('sector', 'N/A')}")
    
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
You are the Executive Strategy Director at a premier fund, writing a confidential briefing for a **Retail Client**. 
The client is smart but needs YOU to connect the macroscopic dots to their specific portfolio.

Provide a high-conviction, professional market intelligence briefing for the "{watchlist_name}" watchlist.

### REAL-TIME PORTFOLIO DATA
{formatted_stocks_str}
{news_str}

### INSTRUCTIONS (The "Deep Monitor" Protocol):
1. **Thematic Intelligence**: Synthesize the watchlist into 1-2 core investment themes.
   - Don't just list moves. Explain: "Tech is selling off because 10Y yields hit 4.5%."
2. **Movers & Implications**: Analyze the Top 3 Gainers/Losers.
   - Explain *WHY* they moved and *WHAT* it means for the rest of the list.
3. **Valuation Pulse**: Flag outliers.
   - "NVDA at 35x Sales is priced for perfection; any miss will be punished."
4. **Actionable Conclusion**: Provide 3 concrete "Watch Items".
   - "Watch for support at $150."
   - "Rotate from Utilities to Tech if CPI cools."

### STYLE RULES:
- **Tone**: "Mentor / Senior Partner". Candid, decisive, and educational.
- **Depth**: Write a Comprehensive Narrative (**500-600 words**). No "too long; didn't read" summaries.
- **Formatting**: Use MARKDOWN headers (`##`, `###`).
- **Data Highlighting (CRITICAL)**: You MUST wrap EVERY instance of the following in double asterisks `**`:
    - All Tickers: e.g., **NVDA**, **AAPL**, **TSLA**
    - All Percentages: e.g., **+5.2%**, **(-1.2%)**, **26.2% YTD**
    - All Valuations: e.g., **22.5x P/E**, **371.2x**

RESPOND IN MARKDOWN ONLY.
"""

    # 2. Attempt DeepSeek R1 (OpenRouter)
    openrouter = _get_openrouter_client()
    if openrouter:
        try:
            logger.info("AI Strategist: Generating via DeepSeek R1...")
            completion = openrouter.chat.completions.create(
                model="deepseek/deepseek-r1",
                messages=[
                    {"role": "system", "content": "You are a pragmatic, cynical hedge fund strategist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6, # Slightly higher for creative synthesis
                max_tokens=2000,
                extra_headers={
                    "HTTP-Referer": "https://vinsight.app",
                    "X-Title": "VinSight AI Strategist"
                },
                timeout=180.0 # R1 is slow; user requested 180s timeout
            )
            raw_text = completion.choices[0].message.content
            clean_text = _strip_think_tags(raw_text)
            return {
                "text": clean_text,
                "model": "DeepSeek R1 (OpenRouter)"
            }
        except Exception as e:
            logger.error(f"DeepSeek R1 failed: {e}. Fallback to Gemini.")

    # 3. Fallback to Gemini 2.0 Flash
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        return {
            "text": "AI Summary unavailable. Please configure OPENROUTER_API_KEY or GEMINI_API_KEY.",
            "model": "System"
        }

    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        response = model.generate_content(prompt, generation_config={"temperature": 0.4})
        
        if response and response.text:
            return {
                "text": response.text,
                "model": "Gemini 2.0 Flash"
            }
        return {
            "text": "AI Summary generated an empty response (Gemini).",
            "model": "Gemini 2.0 Flash"
        }
        
    except Exception as e:
        logger.error(f"Gemini summary generation failed: {e}")
        return {
            "text": f"AI Summary failed to generate: {str(e)}",
            "model": "System"
        }
