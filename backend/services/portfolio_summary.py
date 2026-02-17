import os
import logging
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


def _format_holdings_for_prompt(holdings_data: List[Dict]) -> tuple:
    """
    Format holdings with live prices into prompt-ready text.
    
    Each holding dict: {symbol, quantity, avg_cost, currentPrice, sector, companyName}
    Returns: (formatted_text, total_value, total_cost, largest_symbol, largest_pct)
    """
    total_value = 0
    total_cost = 0
    formatted = []

    for h in holdings_data:
        current_price = h.get('currentPrice', 0) or 0
        quantity = h.get('quantity', 0)
        avg_cost = h.get('avg_cost') or 0
        market_value = quantity * current_price
        cost_basis = quantity * avg_cost
        pl = market_value - cost_basis if avg_cost else 0
        pl_pct = (pl / cost_basis * 100) if cost_basis > 0 else 0
        total_value += market_value
        total_cost += cost_basis
        sector = h.get('sector', 'N/A')

        formatted.append({
            'symbol': h['symbol'],
            'quantity': quantity,
            'avg_cost': avg_cost,
            'current_price': current_price,
            'market_value': market_value,
            'pl': pl,
            'pl_pct': pl_pct,
            'sector': sector,
            'weight': 0  # computed after totals
        })

    # Compute weights
    for f in formatted:
        f['weight'] = (f['market_value'] / total_value * 100) if total_value > 0 else 0

    # Sort by weight (largest first)
    formatted.sort(key=lambda x: x['weight'], reverse=True)

    largest = formatted[0] if formatted else None
    largest_symbol = largest['symbol'] if largest else 'N/A'
    largest_pct = f"{largest['weight']:.1f}" if largest else '0'

    lines = []
    for f in formatted:
        sign = '+' if f['pl'] >= 0 else ''
        avg_str = f"${f['avg_cost']:.2f}" if f['avg_cost'] else "N/A"
        lines.append(
            f"- **{f['symbol']}**: {f['quantity']:.0f} shares @ {avg_str} avg "
            f"→ Current: ${f['current_price']:.2f} ({sign}${f['pl']:.2f}, "
            f"**{sign}{f['pl_pct']:.1f}%**) | Weight: **{f['weight']:.1f}%** "
            f"| Sector: {f['sector']}"
        )

    return '\n'.join(lines), total_value, total_cost, largest_symbol, largest_pct


def generate_portfolio_summary(portfolio_name: str, holdings_data: List[Dict]) -> Dict:
    """
    Generate an AI-powered portfolio analysis.
    Priority: DeepSeek R1 (OpenRouter) -> Gemini 2.0 Flash (Fallback)
    
    holdings_data: list of dicts with keys:
        symbol, quantity, avg_cost, currentPrice, sector, companyName
    """
    if not holdings_data:
        return {
            "text": "No holdings to analyze. Import a CSV or add stocks to your portfolio.",
            "model": "System"
        }

    # Format data
    formatted_text, total_value, total_cost, largest_symbol, largest_pct = \
        _format_holdings_for_prompt(holdings_data)

    total_pl = total_value - total_cost
    total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0
    pl_sign = '+' if total_pl >= 0 else ''
    count = len(holdings_data)

    prompt = f"""
Analyze the "{portfolio_name}" portfolio for a retail investor.
Be their trusted advisor: honest, specific, and actionable.

### PORTFOLIO HOLDINGS (REAL DATA)
{formatted_text}

### PORTFOLIO METRICS
- Total Cost Basis: ${total_cost:,.2f}
- Current Market Value: ${total_value:,.2f}
- Total P&L: {pl_sign}${total_pl:,.2f} ({pl_sign}{total_pl_pct:.1f}%)
- Number of Holdings: {count}
- Largest Position: {largest_symbol} ({largest_pct}%)

### ANALYSIS PROTOCOL (6-Point Framework):

1. **Portfolio Health Score** (Rate 1-10)
   - Consider: diversification, sector spread, concentration risk, risk/reward
   - Format: `## Portfolio Health: X/10 — [One-Line Verdict]`

2. **Concentration Risk**
   - Flag any single position > 25% of total value
   - Flag any single sector > 40% of total value
   - "NVDA at 42% is a concentrated bet. A 20% drawdown wipes $3,700."

3. **Winner & Loser Analysis**
   - Top 3 gainers: "Lock in gains or let it run?"
   - Top 3 losers: "Average down, hold thesis, or cut losses?"
   - Be specific: "TSLA at -15% — if your thesis was EV dominance, 
     that thesis is weakening. Cut at -20% if no catalyst."

4. **Sector & Correlation Audit**
   - Sector breakdown with over/underweight calls
   - Correlation warning: "AAPL + MSFT + GOOGL all move together — 
     you're not as diversified as you think"
   - What's missing: "No exposure to Healthcare, Energy, or International"

5. **Risk Scenarios**
   - Bull case: "If tech rallies 15%, portfolio gains ~$X"
   - Bear case: "A 2022-style drawdown (-30% tech) means you lose ~$X"
   - Rate shock: "If Fed hikes, your growth-heavy book drops ~X%"

6. **Actionable Recommendations** (3-5 specific moves)
   - "Trim NVDA by 20% at +97% gains → redeploy into XLV (Healthcare)"
   - "Set stop-loss on TSLA at $165 (-7% from here)"
   - "Add 5% defensive allocation: GLD or TLT"
   - "Your cash-on-sidelines ($0) means no dry powder — consider 10% cash"

### STYLE RULES:
- **Tone**: Trusted advisor. Candid but not alarmist.
- **Depth**: 600-800 words. Comprehensive narrative, not bullet soup.
- **Formatting**: Use MARKDOWN headers (##, ###).
- **Data Highlighting (CRITICAL)**: Wrap in ** double asterisks **:
    - All Tickers: **NVDA**, **AAPL**
    - All Percentages: **+97.9%**, **-15.1%**
    - All Dollar Amounts: **$4,404**, **$127,450**
    - All Weightings: **42%**, **25%**

RESPOND IN MARKDOWN ONLY.
"""

    # 1. Attempt DeepSeek R1 (OpenRouter)
    openrouter = _get_openrouter_client()
    if openrouter:
        try:
            logger.info("AI Portfolio Manager: Generating via DeepSeek R1...")
            completion = openrouter.chat.completions.create(
                model="deepseek/deepseek-r1",
                messages=[
                    {"role": "system", "content": "You are a Certified Financial Planner and Portfolio Strategist at a premier advisory firm. You provide candid, data-driven portfolio analysis for retail investors."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=2500,
                extra_headers={
                    "HTTP-Referer": "https://vinsight.app",
                    "X-Title": "VinSight AI Portfolio Manager"
                },
                timeout=180.0
            )
            raw_text = completion.choices[0].message.content
            clean_text = _strip_think_tags(raw_text)
            return {
                "text": clean_text,
                "model": "DeepSeek R1 (OpenRouter)"
            }
        except Exception as e:
            logger.error(f"DeepSeek R1 failed: {e}. Fallback to Gemini.")

    # 2. Fallback to Gemini 2.0 Flash
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        return {
            "text": "AI Portfolio Manager unavailable. Please configure OPENROUTER_API_KEY or GEMINI_API_KEY.",
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
            "text": "AI Portfolio Manager generated an empty response.",
            "model": "Gemini 2.0 Flash"
        }

    except Exception as e:
        logger.error(f"Gemini portfolio analysis failed: {e}")
        return {
            "text": f"AI Portfolio Manager failed to generate: {str(e)}",
            "model": "System"
        }
