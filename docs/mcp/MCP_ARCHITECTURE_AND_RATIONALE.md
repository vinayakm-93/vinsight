# VinSight MCP: Architecture & Rationale

**Date**: February 2026
**Version**: 1.0 (Production)
**Format**: Single-File Implementation Guide

---

## 1. Executive Rationale: Why MCP?

### The Problem
Traditional financial dashboards are **passive**. Users must click, scroll, and interpret data themselves. To answer "Is AAPL a buy?", a user has to check news, look at charts, and read filings separately.

### The Solution: "Agentic Finance"
We transformed VinSight from a passive dashboard into an **Active Agent**.
By implementing the **Model Context Protocol (MCP)**, we allow AI Agents (like Claude, Gemini, or OpenAI) to:
1.  **See** our data (Stock Prices, News, Portfolios).
2.  **Act** on our tools (Run Simulations, Audit Holdings).
3.  **Reason** across multiple sources (Combine Earnings sentiment with Price volatility).

### Why MCP?
We chose MCP over a custom API because it is the **Universal Standard**.
*   **Interoperability**: One server works with Claude Desktop, Cursor, Windsurf, and future interfaces.
*   **Security**: Runs locally (stdio) or securely (SSE), keeping user data private.
*   **Future-Proofing**: As "Omni" models evolve, our data layer remains compatible.

---

## 2. Implementation Overview

We implemented a **Python-based MCP Server** (`backend/mcp_server.py`) that acts as a sidecar to our main application. It exposes **4 High-Value Skills**:

### Skill 1: The News Analyst (`analyze_sentiment`)
*   **Logic**: Fetches last 7 days of news via Finnhub -> Uses Llama 3.3 (Groq) to analyze "Fear vs Greed".
*   **Rationale**: Raw news is noisy. We need *synthesized sentiment* to understand market mood.
*   **Perf**: <2s latency.

### Skill 2: The Risk Quant (`run_monte_carlo`)
*   **Logic**: Fetches 2 years of price history -> Runs 5,000 NumPy simulations.
*   **Output**: P10 (Bad Case), P50 (Expected), P90 (Bull Case).
*   **Rationale**: "Past performance doesn't guarantee future results," but statistical probability gives better bounds than guessing.

### Skill 3: The Insider (`analyze_earnings`)
*   **Logic**: Scrapes the latest earnings call transcript -> Extracts CEO confidence & Forward Guidance.
*   **Rationale**: Management tone often predicts price moves before the numbers do.

### Skill 4: The Wealth Manager (`get_portfolio_summary`)
*   **Logic**: Audits the user's *actual* database portfolio -> Enriches with live prices -> Generates a holistic report.
*   **Rationale**: Personalized advice requires access to private data (Holdings), which public LLMs don't have.

---

## 3. Safety Architecture ("The Fortress")

Giving an AI access to tools is risky. We implemented a **Defense-in-Depth** strategy.

### Layer 1: The Kill Switch
*   **What**: A lock file (`mcp_kill_switch.lock`).
*   **Why**: If the AI enters a loop or spends too much money, we need a "hard physical stop" that works instantly.

### Layer 2: Persistent Rate Limits
*   **Global Cap**: **100 calls/day**.
*   **Hourly Caps**: Conservative limits per tool (e.g., 3 Portfolio audits/hour).
*   **Why**: To prevent "Denial of Wallet" attacks (where an AI loop drains $500 in API credits in an hour). Persistence ensures restarting the server doesn't reset the limits.

### Layer 3: Secure Logging
*   **What**: We log *actions*, not *content*.
*   **Why**: We need an audit trail ("Did the AI check sentiment?"), but we must NEVER log user prompts or API keys.

---

## 4. Economic Analysis

We designed the system to be **Cost-Resilient**.

| Tool | Cost per Call | Worst-Case Daily Burn (100 calls) |
| :--- | :--- | :--- |
| **Earnings Analysis** | ~$0.05 (Long Context) | $5.00 |
| **Portfolio Audit** | ~$0.02 (Reasoning Model) | $2.00 |
| **Sentiment/Sim** | <$0.01 | <$1.00 |

**Conclusion**: Even in a worst-case scenario (maxing out the daily limit on the most expensive tool), the cost is capped at **~$5.00/day**. Normal usage is cents per day.

---

## 5. Summary
VinSight MCP is a **Production-Grade, Safety-First** implementation of Agentic AI. It turns a static financial database into a dynamic, reasoning financial advisor, protected by strict economic and security controls.
