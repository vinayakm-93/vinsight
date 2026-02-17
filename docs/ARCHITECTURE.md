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
- **[VinSight Scoring Engine](./SCORING_ENGINE.md)**: Detailed breakdown of the Dynamic Benchmark Model (v9.0).
- **Persona-Based AI Scoring (v9.7)**:
    - **Determinism**: Zero-temperature (`0.0`-`0.1`) usage across all models ensures reproducible scores.
    - **Persona Weights**: Distinct scoring rubrics for **CFA** (Valuation/Profitability), **Momentum** (Technicals/Trend), **Growth** (Revenue/Future), **Value** (Margins/Safety), and **Income** (Yield/Health).
    - **Strict Formatting**: Verdicts are enforced to explain the "Why" immediately.
- **Tri-Layer Signal Synthesis**:
    - **1. AI Strategist**: DeepSeek R1 (via OpenRouter) provides "Thinking" capabilities for portfolio-level synthesis (Fallback: Gemini 2.0).
    - **2. AI Conviction**: Llama 3.3 (via Groq) provides instant stock-level scoring.
    - **3. Algo Baseline**: Mathematical ground truth (70% Fundamental / 30% Technical).
- **Progressive Hydration Pattern**: Dual-engine fetch strategy. Light Algo data renders first; AI Reasoning lazy-loads.

## 5. Thesis Agent Architecture
-   **Hybrid Agent Model**: Combines DeepSeek R1 (Reasoning) with Llama 3.3 (Sentiment) and Gemini 2.0 (Fallback).
-   **Autonomous Loop**:
    1.  **Monitor**: Scheduled Cloud Run Job triggers event detection.
    2.  **Evaluate**: Specialized prompts determine if an event breaks the user's specific thesis.
    3.  **Act**: Updates status and sends proactive email alerts.
-   **Documentation**: See [Thesis Agent Docs](../.gemini/antigravity/brain/797d5707-6eeb-42e7-9505-2b09f8dbab87/THESIS_AGENT.md) for full details.

## 6. Infrastructure & Security
-   **Computing**: Scaling-to-zero Cloud Run containers for cost efficiency.
-   **Secrets**: Zero-knowledge credential storage via Google Secret Manager.
-   **Alerts**: Background cron job (Worker) triggered every 5 minutes during US market hours.

## 7. Detailed Technical Documentation
- **[Security & Compliance](./SECURITY.md)**: OWASP compliance, Encryption audits, and Rotation schedules.
- **[Maintenance & Incident Log](./MAINTENANCE_LOG.md)**: Fix history and Root Cause Analyses.
- **[Deployment Guide](./DEPLOY.md)**: Instructions for pushing to Google Cloud.
- **[Setup Guide](./SETUP.md)**: Local development environment configuration.


