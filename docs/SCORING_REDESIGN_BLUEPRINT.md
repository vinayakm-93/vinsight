# Vinsight AI Scoring Engine: Architecture & Implementation Blueprint (v11)

## Executive Summary
This document outlines the final, comprehensive implementation plan for the Vinsight Scoring Engine Redesign. The core philosophy of this redesign is **"Dumb AI, Smart Python."** 

By shifting all deterministic mathematical calculations, strict guardrails, and kill switches to the Python execution layer, we eliminate LLM algebraic hallucinations, improve latency by 2-3x, and reduce token generation costs by ~60%. The LLM's sole responsibility is qualitative synthesis: reading complex news and unstructured data to provide contextual overrides and human-readable narratives.

---

## The 5-Phase Implementation Plan

### Phase 0: The News Intelligence Pipeline ✅ [COMPLETED - Feb 2026]
*Replacing shallow headlines with deep, distilled, hype-filtered insight.*

1. **Ingestion**: Replace `yfinance` news with `finnhub_news.fetch_company_news()`.
2. **Rate Limit Protection & Volatility Bypass**: Wrap the Finnhub call in a 15-minute in-memory `TTLCache`. To prevent breaking news blindspots, a Python volatility sensor (e.g. daily price drop > 5%) will force a cache bypass and pull live news immediately.
3. **The Intelligence Agent**: Rather than dumping raw summaries into the scoring engine, a fast LLM (Groq/Llama) will process the 14-day news history to:
   - **Distill Hype**: Ignore PR spin; isolate facts.
   - **Historical Context**: Compare current headlines to past themes.
   - **Cross-Asset Insight**: Identify how the news impacts competitors/suppliers.
4. **Injection**: This distilled "Intelligence Report" is injected into the primary DeepSeek R1 prompt.

### Phase 1: Fix the Math (The Python Migration) ✅ [COMPLETED - Feb 2026]
*Eliminating LLM math to guarantee deterministic accuracy.*

1. **Prompt Rewrite**: Remove all point deduction instructions from the LLM prompt in `reasoning_scorer.py`.
2. **Python Execution**: Python calculates the baseline 0-100 score based on persona weights.
3. **Kill Switches**: Python independently applies stacking penalties (e.g., -20 pts for Solvency Risk, -15 pts for Revenue Collapse). 
4. **Pydantic Validation**: Enforce strict JSON output schemas from the LLM. If the LLM output fails schema validation, Python gracefully falls back to the algorithmic score.

### Phase 2: Grounding Verification
*Stopping hallucinated numbers from reaching the user interface.*

1. **Validation Layer**: Create a `grounding_validator.py` step.
2. **Cross-Check**: If the LLM generates a text narrative claiming "P/E is 15", but the actual injected metrics dictionary says "P/E is 80", the validator catches the contradiction.
3. **Resolution**: If >2 hallucinations are detected in the narrative, the AI text is discarded and replaced with a safe fallback template.

### Phase 3: Agent Collaboration
*Allowing Models to communicate context.*

1. **Score Anchoring**: Inject the legacy Algo Scorer's total score into the DeepSeek prompt as a baseline anchor.
2. **Guardian Status**: Query the `GuardianAlert` Postgres database to check if the Guardian Agent currently considers the user's thesis "BROKEN" or "INTACT". Inject this status into the scoring prompt so the Reasoning Scorer agrees with the Guardian.

### Phase 4: Scoring Memory
*Creating temporal awareness.*

1. **Database Schema**: Add a `ScoreHistory` table to Postgres.
2. **Throttling**: To prevent DB bloat, only write a new historical score row once per 24 hours, OR if the stock price moves >3% in a single day.
3. **Context Evolution**: Inject the last 3 historical scores into the prompt. This allows the AI to explain *why* a stock was downgraded from an 85 to a 71 over the last month, tracking deterioration rather than evaluating in a vacuum.

---

## Strategic Impact & Trade-offs

### 1. The Value of the 0-100 Score
A simple "Buy/Hold/Sell" rating is insufficient for portfolio construction. The 0-100 numerical score is essential because it allows for:
- **Relative Ranking**: Differentiating between two "Buy" rated stocks (e.g., an 88 vs a 71) to allocate capital optimally.
- **Delta Tracking**: Identifying deteriorating fundamentals *before* a formal downgrade (e.g., watching a score slowly bleed from 85 to 76).
- **Automated Triggers**: Enabling the Guardian Agent to execute programmatic alerts based on strict mathematical drops.

### 2. Why TTLCache over a Database for News?
While Earnings Transcripts are static and perfect for a Database, News is highly volatile. Storing news summaries in a Database requires complex invalidation. A 15-minute TTLCache, paired with a Volatility Bypass, achieves the API reduction of a DB while ensuring breaking news is captured instantly.

### 3. Why AI for News? (Zero-Shot vs Multi-Shot)
The AI acts as an immediate narrative translator. Instead of relying on rigid keyword analysis (TextBlob), the reasoning LLM comprehends the *implication* of news (e.g., understanding that a delayed factory impacts next quarter's revenue). 
We execute this in a **Single-Shot** prompt rather than a Multi-Shot orchestration loop to preserve sub-4-second latency for the frontend user experience.

---

## Future Roadmap (Deferred to Post-Phase 4)
- **Earnings RAG Pipeline**: Implementing ChromaDB/Pinecone to allow conversational querying of the raw 50,000-word earnings transcripts (e.g., "What did the CEO say about AI margins?").
- **Dynamic Persona Toggles**: Updating the frontend React UI to allow users to instantly switch the Python scoring weights from "Value" to "Momentum" and watch the AI narratives instantly adapt. 

*Document generated and audited: February 2026*
