# Scoring Engine Redesign (v11.0) — Session Handoff

## Context
We are in the middle of a major architectural redesign of the AI Scoring Engine (`reasoning_scorer.py`).
The old architecture heavily relied on the LLM to perform hidden math (like point deductions and weighted averages) which caused mathematical contradictions, ignored persona weights, and displayed hallucinatory scores.

## "Dumb AI, Smart Python" Architecture
The new architecture shifts all mathematical calculations, kill switches, and benchmark deltas to the Python execution layer. The LLM's sole responsibility is qualitative synthesis (reading news, earnings transcripts, and metrics) to output flat component scores (1-10) and narrative text (`bull_case`, `bear_case`).

## The 5-Phase Implementation Plan
We have agreed on the following execution plan:

### Phase 0: Rebuild the News Pipeline (Prerequisite)
- **Current State**: `data.py` passes 10 shallow headlines from `yfinance` to `TextBlob`.
- **Action**: Rip out `yfinance` news in `data.py`. Pipe in 14-day history from `finnhub_news.fetch_company_news()`. Inject the physical text summaries of the top 5 articles into the AI's system prompt in `reasoning_scorer.py`.

### Phase 1: Fix the Math
- **Action**: Modify `_build_system_prompt` and `_parse_response` in `reasoning_scorer.py`. Remove LLM point deductions. Python calculates the persona-weighted score and applies strict boolean kill switches (e.g., `is_valuation_trap`). Include Pydantic validation for the JSON response.

### Phase 2: Grounding Verification
- **Action**: Create `grounding_validator.py` to cross-check AI numeric claims against injected data. If >2 contradictions occur, fallback to the Algo Scorer (`vinsight_scorer.py`).

### Phase 3: Agent Collaboration
- **Action**: Inject the Algo Scorer's total score as a prompt anchor. Query the DB for the Guardian Agent's `thesis_status` and inject it. Add `score_stock` as an MCP tool.

### Phase 4: Scoring Memory
- **Action**: Add `ScoreHistory` DB model. Throttle DB writes to once per 24 hours (or 3% price move). Inject the last 3 historical scores into the prompt so the AI can explain trend changes.

## Current Status (COMPLETED)
- The entire 5-Phase "Dumb AI, Smart Python" architectural migration is **100% Complete**.
- **Phase 0 (News)**: Ripped out `yfinance`, implemented `finnhub_news` with TTL cache, injected dual-period Groq sentiment analysis.
- **Phase 1 (Math)**: Migrated scoring logic and kill switches to strict Python execution. Enforced Pydantic validation on LLM output.
- **Phase 2 (Grounding)**: Built `GroundingValidator` with 5% fuzzy-match thresholds to instantly suppress LLM numerical hallucinations.
- **Phase 3 (Collaboration)**: Hooked reasoning engine to the offline Algo Score and the Postgres Guardian Agent DB.
- **Phase 4 (Memory)**: Built Postgres `ScoreHistory` table with volatility-bypassing throttles to give the LLM temporal awareness of deteriorating trends.
- **Testing**: All automated pipelines (Phase 0, 1, 2, 3, 4) and manual regression tests have passed successfully. `test_results_reference.md` has been archived in the brain directory.

The Scoring Engine is now rigorously deterministic, structurally aware, and protected against generative hallucinations.
