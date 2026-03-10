import os
import logging
import re
from google.genai import Client
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
    
    largest_value = 0
    largest_symbol = ""
    
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
        
        if market_value > largest_value:
            largest_value = market_value
            largest_symbol = h.get('symbol', '')
            
        sign = '+' if pl >= 0 else ''
        formatted.append(f"- **{h.get('symbol', 'UNKNOWN')}**: {quantity} shares @ ${current_price:,.2f} | Value: **${market_value:,.2f}** | P&L: **{sign}${pl:,.2f}** (**{sign}{pl_pct:.1f}%**) | Sector: {h.get('sector', 'N/A')}")
        
    largest_pct = (largest_value / total_value * 100) if total_value > 0 else 0
    return "\n".join(formatted), total_value, total_cost, largest_symbol, round(largest_pct, 1)

def _build_profile_section(profile: Optional[Dict]) -> str:
    """Build the INVESTOR PROFILE prompt section. Returns empty string if no profile data."""
    if not profile:
        return ""
    lines = []
    has_data = False
    if profile.get('risk_tolerance'):
        lines.append(f"- Risk Tolerance: {profile['risk_tolerance'].upper()}")
        has_data = True
    if profile.get('time_horizon'):
        lines.append(f"- Time Horizon: {profile['time_horizon']}")
        has_data = True
    if profile.get('monthly_contribution') is not None:
        lines.append(f"- Expected Monthly Contribution: ${profile['monthly_contribution']:,.0f}")
        has_data = True
    goals = profile.get('user_goals', [])
    if goals:
        lines.append("- Specific Investment Goals:")
        for g in goals:
            # Handle empty amount safely
            amount = g.get('amount')
            amount_str = f"${amount:,.0f}" if amount else "Unspecified"
            lines.append(f"  * {g['name']} (Target: {amount_str} by {g['date']}) - Priority: {g['priority']}")
        has_data = True
    elif profile.get('investment_goal'):
        lines.append(f"- Primary Investment Goal: {profile['investment_goal']}")
        has_data = True
    if not has_data:
        return ""
    return "\n### INVESTOR PROFILE\n" + "\n".join(lines) + "\n"

def _build_goal_alignment_item(profile: Optional[Dict]) -> str:
    """Build the Goal Alignment Check framework item. Returns empty string if no profile."""
    if not profile:
        return ""
    has_data = any(profile.get(k) for k in ['risk_tolerance', 'time_horizon', 'monthly_contribution', 'investment_goal', 'user_goals'])
    if not has_data:
        return ""
    return """
7. **Goal Alignment Check**
   - Does this portfolio match the investor's stated risk tolerance, time horizon, and specific goals?
   - "You say 'conservative' but 65% in volatile tech — that's a mismatch"
   - If monthly contribution is provided, project future portfolio value:
     "At $500/month for 10 years with 8% avg return, you'd reach ~$91K from contributions alone"
   - Evaluate whether current allocation supports or conflicts with the stated goals and target dates.
   - Suggest specific rebalancing moves to better align with stated goals.
"""

def generate_portfolio_summary(portfolio_name: str, holdings_data: List[Dict], investor_profile: Optional[Dict] = None) -> Dict:
    """
    Generate an AI-powered portfolio analysis.
    Priority: DeepSeek R1 (OpenRouter) -> Gemini 2.0 Flash (Fallback)
    
    holdings_data: list of dicts with keys:
        symbol, quantity, avg_cost, currentPrice, sector, companyName
    investor_profile: optional dict with keys:
        risk_tolerance, time_horizon, monthly_contribution, investment_goal
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

    # Build investor profile section
    profile_section = _build_profile_section(investor_profile)
    goal_alignment_item = _build_goal_alignment_item(investor_profile)

    prompt = f"""
Analyze the "{portfolio_name}" portfolio for a retail investor.
Be their trusted advisor: honest, specific, and actionable.
{profile_section}
### PORTFOLIO HOLDINGS (REAL DATA)
{formatted_text}

### PORTFOLIO METRICS
- Total Cost Basis: ${total_cost:,.2f}
- Current Market Value: ${total_value:,.2f}
- Total P&L: {pl_sign}${total_pl:,.2f} ({pl_sign}{total_pl_pct:.1f}%)
- Number of Holdings: {count}
- Largest Position: {largest_symbol} ({largest_pct}%)

### ANALYSIS PROTOCOL ({7 if goal_alignment_item else 6}-Point Framework):

1. **Portfolio Health Score** (Rate 1-10)
   - Consider: diversification, sector spread, concentration risk, risk/reward
   - Format: `## Portfolio Health: X/10 — [One-Line Verdict]`

2. **Concentration Risk**
   - Flag any single position > 25% of total value
   - Flag any single sector > 40% of total value
   - "NVDA at 42% is a concentrated bet. A 20% drawdown wipes $3,700."

3. **Sector & Correlation Audit**
   - Sector breakdown with over/underweight calls
   - Correlation warning: "AAPL + MSFT + GOOGL all move together — 
     you're not as diversified as you think"
   - What's missing: "No exposure to Healthcare, Energy, or International"

4. **Risk Scenarios**
   - Bull case: "If tech rallies 15%, portfolio gains ~$X"
   - Bear case: "A 2022-style drawdown (-30% tech) means you lose ~$X"
   - Rate shock: "If Fed hikes, your growth-heavy book drops ~X%"

5. **Winner & Loser Analysis**
   - Top 3 gainers: "Lock in gains or let it run?"
   - Top 3 losers: "Average down, hold thesis, or cut losses?"
   - Be specific: "TSLA at -15% — if your thesis was EV dominance, 
     that thesis is weakening. Cut at -20% if no catalyst."

6. **Actionable Recommendations** (3-5 specific moves)
   - "Trim NVDA by 20% at +97% gains → redeploy into XLV (Healthcare)"
   - "Set stop-loss on TSLA at $165 (-7% from here)"
   - "Add 5% defensive allocation: GLD or TLT"
   - "Your cash-on-sidelines ($0) means no dry powder — consider 10% cash"
{goal_alignment_item}
### STYLE RULES:
- **Tone**: Trusted advisor. Candid but not alarmist.
- **Depth**: 600-800 words. Comprehensive narrative, not bullet soup.
- **Formatting**: Use MARKDOWN headers (##, ###).
- **Data Highlighting (CRITICAL)**: You MUST wrap EVERY instance of the following in double asterisks `**`:
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
        gemini_client = Client()
        model = gemini_client.models.GenerativeModel('gemini-2.0-flash') # No tools for this model
        response = model.generate_content(
            contents=prompt, 
            generation_config={"temperature": 0.4}
        )

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