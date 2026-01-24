# Performance Optimization: Single Stock Page (v6.3.0)

## Overview
**Date:** 2026-01-23
**Version:** v6.3.0
**Objective:** Reduce the loading time of the Single Stock Details page (`/stock/{ticker}`) to improve user experience and reduce server compute costs.

## 📉 Results Summary
| Metric | Legacy Architecture | Optimized Architecture | Improvement |
| :--- | :--- | :--- | :--- |
| **Total Load Time** | ~2.6s - 3.0s | **~1.2s** | **~55% Faster** |
| **API Calls Details** | 6 Sequential Calls | 1 Consolidated Call | **83% Reduction** |
| **Reliability** | "All or Nothing" (Fragile) | Graceful Degradation (Robust) | **High** |

## 🏗️ Architectural Change

### Legacy Approach (Waterfall)
The frontend made multiple independent, often sequential or racing API calls.
1. `getAnalysis` (Calculated technicals + ran Monte Carlo)
2. `getSimulation` (Ran Monte Carlo *again*)
3. `getInstitutional` (Fetched data separately)
4. `getNews` (Fetched separately)
5. `getHistory` (Fetched separately)

**Issues:**
- **Redundant Compute**: Monte Carlo simulation (CPU heavy) was executed twice per page load.
- **Latency**: Network overhead of multiple TCP connections.
- **Race/Wait**: Visual UI "pop-in" as different sections loaded at different times.

### Optimized Approach (Parallel & Consolidated)
We consolidated all non-chart data into a single endpoint: `GET /api/data/analysis/{ticker}`.

```mermaid
graph TD
    Client[Frontend Client] -->|GET /analysis/AAPL| Backend[Backend API]
    
    subgraph "Backend Parallel Execution (ThreadPoolExecutor)"
        Backend -->|Thread A| History[Fetch Price History]
        Backend -->|Thread B| Profile[Fetch Stock Profile]
        Backend -->|Thread C| News[Fetch News w/ Sentiment]
        Backend -->|Thread D| Inst[Fetch Institutional Data]
    end
    
    History --> Calc[Run Technical Analysis]
    History --> Sim[Run Monte Carlo (One Time)]
    
    Calc --> Response
    Sim --> Response
    Profile --> Response
    News --> Response
    Inst --> Response
    
    Response -->|Single JSON Payload| Client
```

## 🛡️ Robustness & Graceful Degradation
To prevent the "Single Point of Failure" risk associated with consolidated APIs, we implemented a robust error handling strategy.

- **Wrapper**: Each sub-task (News, Institutional) is wrapped in a `try-except` block within its thread.
- **Outcome**:
    - **News API Down?** → Returns `200 OK` with `news: []`. Dashboard shows "No News Found" instead of crashing.
    - **History API Down?** → Returns `404 Not Found` (Correct, as analysis is impossible without price data).
- **Verification**: Verified via `backend/tests/test_optimization_robustness.py`.

## 💰 Cost & Infrastructure
- **Compute Efficiency**: Eliminated 50% of Monte Carlo executions.
- **Memory**: Backend configured with `2Gi` memory on cloud Run, sufficient to handle `ThreadPoolExecutor` overhead.
- **Billable Time**: Reduced request duration directly lowers Cloud Run billable CPU-seconds.

## 🧪 Verification Scripts
- `scripts/benchmark_single_stock_optimization.py`: Validates performance and response structure.
- `backend/tests/test_optimization_robustness.py`: Unit tests for failure scenarios.
