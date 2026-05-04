# VinSight Technical System Design (v13.0)

**Version:** 13.0  
**Status:** Production  
**Scope:** Agentic Ecosystem & Quantitative Scoring Architecture

---

## 1. Executive Summary & LLM Routing Strategy
The VinSight v13 platform is an enterprise-grade AI financial intelligence ecosystem. It acts as an autonomous co-pilot, mitigating retail investor confirmation bias through rigorous, multi-agent adversarial debate and dynamic quantitative scoring.

### Intelligent LLM Routing Strategy
VinSight utilizes a specialized model routing architecture to optimize for both latency and deep cognitive reasoning:
1. **Llama 3.3 70B (via Groq)**: **High-Speed Sentiment & Routing**. Chosen for its extreme inference speed (sub-second TTFB). Used for parsing massive daily news feeds and simple sentiment tagging where latency is the primary constraint.
2. **DeepSeek R1 (via OpenRouter)**: **Deep Reasoning & Thesis Generation**. Chosen specifically for its superior Chain-of-Thought (CoT) capabilities. R1 acts as the Judge and primary Thesis Generator because it can systematically weigh evidence without premature conclusions. We allocate large **180-second reasoning windows** to prevent CoT truncation.
3. **Gemini 2.0 Flash**: **Pure Text SEC RAG Summarization**. Chosen for its massive context window (1M+ tokens) and cost efficiency. It serves as the workhorse for pre-summarizing dense 10-K risk factors into compact text blocks before caching.

---

## 2. Stream A: Agent Optimization & Scaffolding
The intelligence layer is structured around an **Agentic Scaffolding** pattern explicitly designed to prevent confirmation bias.

### 2.1 Multi-Agent Debate Scaffolding
We implemented a rigid Multi-Agent Debate scaffolding architecture rather than relying on a single, unstructured autonomous agent.
1. **Turn 0 (The Fact Dossier)**: A Neutral Researcher Agent gathers verified ground truth (SEC filings, live prices) to prevent parallel agents from hallucinating or redundantly searching the web.
2. **Turn 1 (Adversarial Parallel Search)**: A `Bull Agent` and `Bear Agent` are spawned. They are independently constrained—the Bear must attempt to break the thesis by searching for macroeconomic headwinds or bearish keywords, while the Bull searches exclusively for catalysts.
3. **Turn 2 (Judge Synthesis)**: DeepSeek R1 acts as the Judge. It evaluates both briefs against the Fact Dossier and issues a final verdict (`INTACT`, `AT_RISK`, `BROKEN`). The debate is strictly capped at a **maximum of 2 escalation turns** to prevent infinite looping and bound API costs.

### 2.2 Memory Architecture: Pure Text RAG via SQLite
We ripped out legacy Vector Databases (FAISS, pgvector) in v11.2 due to unnecessary computational overhead and poor exact-keyword retrieval for financial metrics.
- **The Pivot**: We transitioned to a "Zero-Cost Ingestion" pipeline. We fetch raw SEC 10-K/10-Q documents (`edgartools`), summarize the specific "Risk Factors" and "MD&A" sections using Gemini 2.0 Flash, and store these highly dense, pure text blocks directly in a relational **SQLite (`finance.db`)**.
- **Context Injection**: When the Thesis Agent boots up, it doesn't execute a fuzzy vector search; it injects the *entire* pre-calculated SEC Risk Summary directly into the DeepSeek baseline prompt. This guarantees 100% recall of critical corporate risks.

### 2.3 Sentiment Analysis & The "False Positive" Solution
**The Challenge**: Early versions of the sentiment engine exhibited an 89% positive bias because corporate PR wires aggressively use positive "spin" (e.g., framing layoffs as "strategic realignment").
**The Solution**: We implemented a hybrid Spin Detection algorithm:
1. **Bearish Keyword Heuristic**: The pipeline runs a highly optimized regex scan for 25+ institutional bearish keywords ("miss", "loss", "layoffs", "headwinds").
2. **Divergence Penalty**: If the LLM generates a "Positive" sentiment label, but the text triggers a Bearish Keyword, the system flags a "Spin Divergence". It mathematically overrides the LLM's confidence score, aggressively pulling the aggregate sentiment down to Neutral or Negative. **This successfully reduced the platform's positive bias from 89% to 33%.**

### 2.4 Prompt Engineering Schema
All agents use strict, heavily engineered system prompts enforcing JSON output schemas to ensure programmatic reliability.
*Example Schema injected into DeepSeek R1 for the Core Strategist:*
```json
{
  "thought_process": "[MANDATORY: 300 words of Chain-of-Thought reasoning. Weigh the Bear case first.]",
  "summary": {
    "verdict": "[1 sentence explicit action: BUY, SELL, or HOLD]",
    "bull_case": "[List 2 verified catalysts]",
    "bear_case": "[List 2 verified risks]"
  },
  "contextual_adjustment": "[Integer between -10 and +10]",
  "adjustment_reasoning": "[MANDATORY: Must explain the adjustment or it defaults to 0]"
}
```
**Fiduciary Guardrails**: The output is validated against a strict **5% fuzzy-match grounding threshold**. Any number or exact quote cited in the output must exist in the retrieved Fact Dossier context, or it is automatically tagged as `[UNVERIFIED]`.

---

## 3. Stream B: Scoring Engine Upgrades
The v13 Scoring Engine is a deterministic, quantitative pipeline ensuring absolute "Ruthless Objectivity."

### 3.1 The Three-Axis Framework
To provide institutional clarity, the engine separates traditional blended scores into three distinct mathematical axes (0-100 scales):
1. **Quality Axis**: Measures fundamental business health *ignoring price*. (ROE, Margins, D/E, EPS Stability, Altman Z, ROIC Spread).
2. **Value Axis**: Measures cheapness relative to intrinsic value. (PEG, Forward P/E, FCF Yield, RIM Margin of Safety).
3. **Timing Axis**: Measures market momentum and entry signals. (Price vs SMA50/200, RSI, Relative Volume).

**Persona Conviction Matrix**: The final score is a linear combination of these axes weighted by the user's Persona:
`Conviction = (Q × Wq) + (V × Wv) + (T × Wt)`
*(e.g., A CFA Persona applies Q=45%, V=30%, T=25%, while a Momentum Persona applies Q=10%, V=10%, T=80%).*

### 3.2 Residual Income Model (RIM) & Valuation Formulas
We replaced rudimentary P/E capping with a rigorous Intrinsic Valuation model inside the Value Axis.
**Justification**: The Residual Income Model evaluates whether a company actually generates returns *above* its cost of capital, punishing companies that grow unprofitably (which P/E models often fail to catch).

**1. Cost of Equity (WACC Approximation)**
`WACC = Risk_Free_Rate + (Market_Premium × Beta)`
*Justification*: Because strict Beta is historically noisy for micro-caps, the engine defaults to a strict 10% baseline cost of equity, automatically penalizing/adjusting up to 12% for high-debt companies (Altman Z < 1.8).

**2. Residual Income Generation**
`Residual_Income = Net_Income - (Equity_Book_Value × WACC)`
*Justification*: A company with $100M in Net Income but $2B in Book Equity is destroying shareholder value (if WACC is 10%, it should be earning $200M just to break even on capital costs).

**3. Margin of Safety (MoS)**
`MoS = (Intrinsic_Value - Current_Market_Price) / Intrinsic_Value`
*Justification*: The Value Axis directly scales with the MoS. If MoS > 30%, the Value Axis receives maximum points. If MoS < 0 (overvalued), it triggers a **Continuous Outlier Penalty**, linearly scaling down to a -15 point deduction.

### 3.3 Fiduciary Data Refusal (The 50% Rule)
**Challenge**: Missing API data (e.g., recent IPOs with no 3-year growth history) artificially crashed scores to zero, or, if the denominator was dropped, artificially inflated them to 100.
**Solution**: The **50% Rule**. If an entire mathematical Axis (Quality, Value, Timing) is starved of more than 50% of its required data points from the upstream providers, the algorithm explicitly aborts the score aggregation for that axis and neutralizes it to exactly `50.0`. This mathematically prevents bizarre edge-case inflations and ensures a documented, predictable flat fallback.

---

## 4. Backtesting & Empirical Validation
The v13 engine is empirically validated using the `Backtester` framework.
- **Methodology**: The engine evaluates stocks at monthly historical snapshots over a 12-month window, using point-in-time fundamentals and reconstructed technicals to prevent lookahead bias.
- **Empirical Results**:
  - **Elite Tier (80-100 Score)**: Achieves a **72% hit rate** at 3 months and a **100% win rate** at 12 months, delivering a **+7.4% excess return** over the S&P 500 benchmark.
  - **Avoid Tier (0-49 Score)**: Achieves a 0% hit rate at 12 months, with a -17.6% excess return, validating the penalty logic.
- **Disclosures**: The current test pipeline acknowledges survivorship bias (tests only currently listed stocks). Future implementations will integrate delisted equity databases.
