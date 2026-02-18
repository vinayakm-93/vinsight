# VinSight MCP: As-Built Specification & Future Plans

## 1. Core Implementation Capabilities (Implemented)
We have successfully deployed a **Model Context Protocol (MCP)** server that gives AI Agents the following skills:

### 🧠 The "Brain" (AI Analysis)
| Tool | Function | Status | Limit |
| :--- | :--- | :--- | :--- |
| **`analyze_sentiment`** | Reads 7-days of news -> Quantifies Fear/Greed. | ✅ Live | 60/hr |
| **`analyze_earnings`** | Scrapes transcripts -> Extracts CEO Confidence. | ✅ Live | 10/hr |
| **`get_portfolio_summary`** | Audits user portfolio -> Acts as Wealth Manager. | ✅ Live | 3/hr |
| **`run_monte_carlo`** | Projects 5,000 price paths -> Calculates VaR. | ✅ Live | 100/hr |

### 🛡️ The "Shield" (Safety Layer)
- **Global Limit**: Max **100 calls/day** across all tools.
- **Kill Switch**: `mcp_kill_switch.lock` halts all operations instantly.
- **Persistence**: Usage counters saved to `logs/mcp_limits.json` to prevent restart-bypass.
- **Privacy**: No user prompts or API keys are ever logged.

---

## 2. Test Plan (Verification Strategy)
This plan ensures reliability and safety.

### 2.1 Automated Unit Tests
Run via `python3 backend/tests/test_mcp_safety.py`.
- [x] **Kill Switch Test**: Force-create lock file -> Verify tools return "SERVICE SUSPENDED".
- [x] **Rate Limit Test**: Spam calls > Limit -> Verify `RuntimeError` (Blocked).
- [x] **Persistence Test**: Restart mock server -> Verify limit counters remain high.

### 2.2 Functional Manual Tests (Claude Desktop)
- [x] **Sentiment**: Ask "What is the sentiment for AAPL?" -> Verify JSON response.
- [x] **Simulation**: Ask "Run a risk simulation for TSLA" -> Verify P50/P90 output.
- [x] **Earnings**: Ask "Analyze the latest earnings for NVDA" -> Verify transcript summary.
- [x] **Portfolio**: Ask "Audit my portfolio (vinayak@email)" -> Verify Wealth Manager report.

### 2.3 Connectivity Tests
- [x] **Stdio**: Verify Claude Desktop connects via `python mcp_server.py`.
- [ ] **SSE (Remote)**: Verify remote agent connects via SSE (Requires `mcp run --transport sse`).

---

## 3. Documentation Plan
Strategy for maintaining and distributing knowledge.

| Document | Audience | Purpose | Update Frequency |
| :--- | :--- | :--- | :--- |
| **`docs/MCP_README.md`** | **End Users** | Quick Start & Troubleshooting. | On new feature release. |
| **`docs/MCP_TECHNICAL_REF.md`** | **Engineers/CTO** | Architecture, Security, Protocol Specs. | On arch change. |
| **`docs/MCP_ROADMAP.md`** | **Product Managers** | Status tracking & Future Phases. | Weekly / Sprint start. |
| **`walkthrough.md`** | **Team** | Proof of Work & Demo. | After major milestones. |

### Distribution Strategy
1.  **Repo Root**: `docs/` folder kept in sync with code.
2.  **Onboarding**: New devs play `walkthrough.md`.
3.  **Governance**: Security and Limits changes MUST update `MCP_TECHNICAL_REF.md`.

---

## 4. Next Steps (Phase 3: Autonomy)
*Target: Q3 2026*
1.  **Transactional Tools**: Allow `place_order` (requires 2FA prompt).
2.  **Notification Tools**: Allow `set_price_alert`.
3.  **Multi-User Auth**: Pass user session JWT from Client to MCP Server (currently relies on email arg).
