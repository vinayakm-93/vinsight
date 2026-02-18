# VinSight MCP Server: Roadmap & Status

This document tracks the strategic direction and current status of the VinSight MCP Integration.

## ✅ Phase 1: Foundation & Safety (COMPLETED)
**Goal:** Establish a secure, monitored bridge for external AI agents.
- [x] **MCP Server Core**: Implemented using `FastMCP` on stdio.
- [x] **Kill Switch**: Global administrative override (`manage_kill_switch.py`).
- [x] **Secure Logging**: Audit trail with privacy safeguards (no prompt leakage).
- [x] **Enhanced Safety**: Global Daily Limits (100/day) & Hourly Persistence.
- [x] **Documentation**: User Guide (`MCP_README.md`) + Tech Spec (`MCP_TECHNICAL_REF.md`).

## 🔄 Phase 2: Analyst Capabilities (Current Focus)
**Goal:** Expose high-value financial reasoning tools.
- [x] **Sentiment Analysis**: `analyze_sentiment` (Dual-Period Logic).
- [x] **Risk Simulation**: `run_monte_carlo` (5,000 path simulation).
- [x] **Earnings Research**: `analyze_earnings` (Scraper + Deep Analysis).
- [ ] **Portfolio Management**: (Planned) `get_portfolio_summary` - *Requires Auth Strategy*.

## 🔜 Phase 3: Agentic Autonomy (Future)
**Goal:** Allow the agent to take actions, not just read data.
*Estimated Timeline: Q3 2026*

| Feature | Description | Status |
| :--- | :--- | :--- |
| **Auth Gateway** | Securely passing user session tokens to MCP. | 🚧 Research |
| **Trade Execution** | `place_order(ticker, qty)` tool with 2FA requirement. | 🔒 Locked |
| **Alert Management** | `create_price_alert(ticker)` tool. | 📋 Backlog |

## 📊 Feature Matrix (Current Release v1.0)

| Tool | Status | Cost Tier | Latency |
| :--- | :--- | :--- | :--- |
| **Sentiment** | 🟢 Live | Low | < 2s |
| **Monte Carlo** | 🟢 Live | Free | < 1s |
| **Earnings** | 🟢 Live | High | ~15s |
