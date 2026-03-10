# AI Scorer Data Pipeline & Prompt Logic

This document details the data flow, architecture, and prompt engineering behind the VinSight AI Scorer (v10.0).

## 1. Data Pipeline Architecture (Concept)

The system uses a **Hybrid Intelligence** model:
1.  **Objective Data Layer (The "Truth")**: Yahoo Finance provides raw, unopinionated numbers.
2.  **Subjective Analysis Layer (The "Judge")**: The AI (Gemini/DeepSeek) interprets these numbers based on a persona.

### Data Flow Diagram

```mermaid
graph TD
    subgraph Data Sources [The Truth]
        YF[Yahoo Finance API] -->|Real-Time| Price[Price & Volume]
        YF -->|Quarterly| Fund[Fundamentals (P/E, Debt/Eq)]
        YF -->|Daily| Tech[Technicals (SMA, RSI)]
    end

    subgraph Backend Logic [The Assembler]
        Py[Python Backend] -->|Validates| RawData{Data Validity?}
        RawData -->|Yes| Context[Context Builder]
        RawData -->|No| Fail[Wait/Retry]
        
        Context -->|Injects| Persona[Active Persona Rules]
        Context -->|Injects| Metrics[Calculated Metrics (PEG, FCF Yield)]
        Context -->|Injects| UserProfile[Investor Profile & Goals]
    end

    subgraph AI Engine [The Judge]
        Context -->|JSON Prompt| LLM[LLM (Gemini 2.0 / DeepSeek R1)]
        LLM -->|Reasoning Chain| Score[Reasoned Score (0-100)]
        LLM -->|Confidence Check| Conf[Confidence Score (0-100)]
    end

    subgraph Frontend [The Display]
        Score -->|Weighted| FinalScore[Final Display Score]
        Conf -->|Discount Factor| FinalScore
        FinalScore --> UI[React Dashboard]
    end
```

---

## 2. The Context Injection (What the AI Sees)

Before the AI writes a single word, it receives a structured JSON context. It doesn't "browse the web" for P/E ratios; we feed it the exact numbers to prevent hallucinations.

**Example Context Block (Injected into Prompt):**
```json
{
  "ticker": "AAPL",
  "sector": "Technology",
  "metrics": {
    "Valuation": {
      "P/E": 32.5,
      "PEG": 2.1,
      "P/Sales": 8.4
    },
    "Profitability": {
      "Net Margin": 25.3,
      "ROE": 145.0
    },
    "Health": {
      "Debt/Equity": 1.8,
      "Interest Coverage": 42.0
    },
    "Technicals": {
      "RSI": 68.5,
      "vs SMA200": "+15.2%"
    }
  },
  "persona": {
    "name": "Value Investor",
    "focus": "Margin of Safety, Cash Flow",
    "style": "Skeptical, Contrarian"
  },
  "investor_profile": {
    "risk_tolerance": "moderate",
    "time_horizon": "5-10 years",
    "monthly_contribution": 500.0,
    "user_goals": [
      {
        "name": "House Downpayment",
        "amount": 50000.0,
        "date": "2028-12-01"
      }
    ]
  }
}
```

---

## 3. The System Prompt (The "Brain")

This is the exact prompt structure used in `services/reasoning_scorer.py` to enforce the v10.0 logic.

**System Prompt Template:**

```text
You are a expert financial mentor for a Retail Investor.
Your name is VinSight AI. Evaluate {ticker} ({sector}) and assign a conviction score (0-100).

YOUR AUDIENCE:
- Smart retail investors who want to understand *WHY* a stock is good or bad.
- Avoid excessive jargon. Explain implications (e.g., "High Debt means rising rates will hurt profits").

USER ALIGNMENT / PERSONALIZATION (CRITICAL):
- The user's risk tolerance is {user_risk} and time horizon is {user_horizon}.
- You MUST penalize volatile stocks if their risk is "conservative" or if they have short-term goals ({user_goals}).

STYLE: {persona_style} (e.g. "Ruthless, Skeptical")
FOCUS: {persona_focus} (e.g. "Free Cash Flow, Deep Value")

SENSITIVITY RULES ({persona_name}):
- {sensitivity_rule} 
  (Example for Value: "Penalize P/B > 3.0. Ignore Momentum.")

SCORING RUBRIC (10-Tier Precision):
- 0-19: ☠️ Bankruptcy Risk (Solvency failure likely).
- 20-39: 🛑 Hard Sell (Broken thesis).
- 40-49: ⚠️ Underperform (Deteriorating fundamentals).
- ... (Full Rubric) ...
- 90-100: 🦄 Generational (Perfect setup).

CRITICAL INSTRUCTION:
The Final Score MUST be a reasoned verdict. 
If Confidence < 50%, you MUST discount the score heavily.

OUTPUT FORMAT (JSON ONLY):
{
  "thought_process": "Detailed chain of thought...",
  "total_score": 0-100,
  "confidence_score": 0-100,
  "primary_driver": "The ONE reason to buy/sell",
  "summary": { ... },
  "risk_factors": ["SOLVENCY RISK: -20 pts", "VALUATION CAP: -15 pts"]
}
```

---

## 4. Kill Switch Logic (The Guardrails)

Even if the AI likes a stock, specific "Kill Switch" conditions are hard-coded or strictly enforced in the prompt to prevent dangerous recommendations.

| Trigger | Description | Impact |
| :--- | :--- | :--- |
| **Solvency Risk** | Debt/Equity > 2.0 OR Negative Interest Coverage | **-20 Points** (Auto-Badge) |
| **Valuation Cap** | P/E > 50 AND Growth < 10% | **-15 Points** (Value Trap) |
| **Momentum Crash**| Price < SMA200 | **-10 Points** (Downtrend) |
| **Low Confidence**| Missing data fields | **Score Discounted by %** |
