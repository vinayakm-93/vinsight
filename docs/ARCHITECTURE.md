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
| **Database** | Cloud SQL (PostgreSQL 15) for Prod; SQLite for Local |
| **AI Models** | Groq (Llama 3.3 70B), Gemini 1.5 Pro, Alpha Vantage |
| **Email** | FAST-Mail (SMTP/Gmail) |
| **Infrastructure** | Google Cloud Run, Cloud Scheduler, Secret Manager |

## 3. Core Engine Logic
- **[VinSight Scoring Engine](./SCORING_ENGINE.md)**: Detailed breakdown of the "Dumb AI, Smart Python" Re-architecture (v11.0).
- **Persona-Based Deterministic Scoring**:
    - **Algorithmic Math**: 0-100 baseline scores are calculated deterministically in Python using strict persona-weighted multipliers (Value, Growth, CFA, Momentum).
    - **Python Guardrails (Kill Switches)**: Extreme fundamental flaws (e.g., negative FCF, debt traps) trigger absolute point penalties injected into the AI context *before* the narrative is generated.
- **Agent Collaboration & Grounding Validation**:
    - **1. Tri-Layer Synthesis**: DeepSeek R1/Llama 3.3 handles qualitative synthesis, anchored to the offline `VinSightScorer` algorithmic baseline score.
    - **2. Guardian Integration**: `ReasoningScorer` queries the `GuardianAlert` module via Postgres. If a thesis is "BROKEN", the reasoning engine is forced to aggressively address the risks.
    - **3. Scoring Memory**: AI fetches the last 3 score outputs from Postgres (throttled locally by volatility) to evaluate temporal momentum rather than scoring in a vacuum.
    - **4. Strict Grounding Layer**: All generated numbers and quotes are validated against a 5% Pydantic/Regex fuzzy-matcher. Hallucinations >2 automatically suppress the AI text.

## 5. Thesis Agent Architecture
-   **Hybrid Agent Model**: Combines DeepSeek R1 (Reasoning) with Llama 3.3 (Sentiment) and Gemini 2.0 (Fallback).
-   **Autonomous Loop**:
    1.  **Monitor**: Scheduled Cloud Run Job triggers event detection.
    2.  **Evaluate**: Specialized prompts determine if an event breaks the user's specific thesis.
    3.  **Act**: Updates status and sends proactive email alerts.
-   **Documentation**: See [Thesis Agent Docs](../.gemini/antigravity/brain/797d5707-6eeb-42e7-9505-2b09f8dbab87/THESIS_AGENT.md) for full details.

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


