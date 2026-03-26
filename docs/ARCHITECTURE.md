# Architecture Overview

VinSight follows a modern **Client-Server Architecture** with a **Proxy Layer** for cookie handling and a micro-batching background worker for market alerts.

## 1. System Diagram

```mermaid
graph TD
    User[User Browser]
    FE[Next.js Frontend]
    Proxy[Next.js Rewrites Proxy]
    BE[FastAPI Backend]
    DB[(PostgreSQL / SQLite)]
    AI1[Groq API]
    AI2[Gemini API]
    AV[Alpha Vantage API]
    Data[yfinance]
    Mail[SMTP Server]
    Worker[Cloud Run Job: Market Watcher]

    User -->|HTTP| FE
    FE -->|/api/* requests| Proxy
    Proxy -->|Forward + Cookies| BE
    BE -->|SQLAlchemy| DB
    BE -->|AI Conviction| AI1
    BE -->|Search & Scrape| Web[Serper/DDG + MotleyFool]
    BE -->|News + Sentiment| AV
    BE -->|Stock Data (v9.1 Coordinated)| Data
    BE -->|Trigger Alerts| Mail
    BE -->|Portfolio Logic| Parser[CSV Parser: Robinhood/Generic]
    Worker -->|Check Price Targets| BE
```

## 2. Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | Next.js 14/15, TypeScript, Tailwind CSS, Framer Motion |
| **Backend** | Python 3.11, FastAPI, Pydantic, SQLAlchemy |
| **Database** | Cloud SQL (PostgreSQL 15) & Local SQLite |
| **AI Models** | Groq (Llama 3.3 70B), Gemini 1.5 Pro, edgartools (SEC) |
| **Email** | FAST-Mail (SMTP/Gmail) |
| **Infrastructure** | Google Cloud Run, Cloud Scheduler, Secret Manager |

## 3. Core Engine Logic
- **[VinSight Scoring Engine v13](./SCORING_ENGINE.md)**: Three-axis architecture (Quality, Value, Timing) with persona-weighted conviction.
- **Three-Axis Scoring (v13)**:
    - **Quality Axis (0-100)**: ROE, margins, D/E, EPS stability, Altman Z, ROIC spread. No valuation metrics.
    - **Value Axis (0-100)**: PEG, Forward P/E, FCF Yield, RIM Margin of Safety.
    - **Timing Axis (0-100)**: Price vs SMA50/200, RSI, volume, momentum.
    - **Conviction**: `Q×Wq + V×Wv + T×Wt` where weights are persona-specific (e.g., CFA: 45/30/25).
- **Guardian Conviction Modifiers**: BROKEN thesis → cap score at 40. AT_RISK → -10pts.
- **Python Guardrails (Kill Switches)**: Extreme fundamental flaws trigger absolute point caps injected before the narrative is generated.
- **Agent Collaboration & Grounding Validation**:
    - **1. Tri-Layer Synthesis**: DeepSeek R1/Llama 3.3 handles qualitative synthesis, anchored to the offline `VinSightScorer` algorithmic baseline score.
    - **1.5 Deep Personalization**: The `ReasoningScorer` dynamically ingests the explicit `UserProfile` (risk tolerance, investment goals, monthly budget, and time horizon) to structurally penalize/reward stocks based on strict fiduciary alignment to the user's goals.
    - **2. Guardian Integration**: `ReasoningScorer` queries the `GuardianAlert` module via Postgres. If a thesis is "BROKEN", the reasoning engine is forced to aggressively address the risks.
    - **3. Scoring Memory**: AI fetches the last 3 score outputs from Postgres (throttled locally by volatility) to evaluate temporal momentum rather than scoring in a vacuum.
    - **4. Strict Grounding Layer**: All generated numbers and quotes are validated against a 5% Pydantic/Regex fuzzy-matcher. Hallucinations >2 automatically suppress the AI text.

## 5. Thesis Agent Architecture
-   **Hybrid Agent Model**: Combines DeepSeek R1 (Reasoning) with Llama 3.3 (Sentiment) and Gemini 2.0 (Fallback).
-   **Autonomous Loop (Multi-Agent Debate)**:
    1.  **Monitor**: Scheduled Cloud Run Job triggers event detection (including SPY Macro headwind checks and News Sentiment crashes).
    2.  **Turn 0 (Establish Ground Truth)**: A Neutral Researcher Agent gathers an objective "Fact Dossier" pulling SEC filings and real-time news to prevent redundant or hallucinated parallel searches.
    3.  **Evaluate (The Debate)**: If triggered, a parallel `Bull Agent` and `Bear Agent` independently receive the Fact Dossier and generate targeted web search queries to validate or attack the thesis.
    4.  **Synthesize (The Judge)**: A third `Judge Agent` evaluates the Bull and Bear briefs to issue a final verdict (`INTACT`, `AT_RISK`, `BROKEN`). The debate is strictly capped at a maximum of 2 escalation turns to ensure high quality and bounded cost.
    5.  **Act**: Updates status and sends proactive email alerts.
-   **Pure Text Memory & Safeguards**: Uses SQLite for persistent retrieval of pre-summarized SEC risk data. Strict Hallucination safeguards force agents to cite only verified retrieved contexts.
-   **Documentation**: See [Thesis Agent Docs](../.gemini/antigravity/brain/7cb40b9e-875f-42f5-934b-cc4ffec9e3df/walkthrough.md) for full details on Phase 4 enhancements.

## 6. Model Context Protocol (MCP) Integration
VinSight exposes its internal analysis tools via an MCP Server, allowing external AI agents (like Claude Desktop) to invoke them.
-   **Documentation**: See the [MCP Architecture & Setup Guide](./mcp/MCP_README.md) for full details, token economics, and security rationales.

## 7. Infrastructure & Security
-   **Computing**: Scaling-to-zero Cloud Run containers for cost efficiency.
-   **Secrets**: Zero-knowledge credential storage via Google Secret Manager.
-   **Alerts**: Background cron job (Worker) triggered every 5 minutes during US market hours.

## 7. Detailed Technical Documentation
- **[Security & Compliance](./SECURITY.md)**: OWASP compliance, Encryption audits, and Rotation schedules.
- **[Maintenance & Incident Log](./MAINTENANCE_LOG.md)**: Fix history and Root Cause Analyses.
- **[Deployment Guide](./DEPLOY.md)**: Instructions for pushing to Google Cloud.
- **[Setup Guide](./SETUP.md)**: Local development environment configuration.


