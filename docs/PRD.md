# VinSight Product Requirements Document (PRD)

**Version:** 9.5 (High-Performance Upgrade)
**Status:** Live in Production

## 1. Executive Summary
VinSight is an AI-powered financial analytics platform that democratizes institutional-grade investment research. It combines real-time technical analysis with Large Language Model (LLM) reasoning to provide clear, actionable insights ("VinSight Score") for retail investors.

## 2. Target Audience
- **Self-Directed Investors**: Looking for data-backed conviction without reading 10-Ks for hours.
- **Swing Traders**: Needing quick technical setups and sentiment pulse checks.
- **Financial Analysts**: Seeking an AI-augmented "second opinion" on stock valuations.

## 3. Core Product Pillars

### 3.1 AI-Driven Sentiment
- Multi-source sentiment aggregation (News, SEC Filings, Insider Activity).
- Deep reasoning via LLMs to filter out "market noise" and detect bias/spin.
- Insider conviction scoring (Discretionary vs. Automatic 10b5-1 trades).

### 3.2 Dynamic Scoring (VinSight Score)
- **Quality (70%)**: Industry-relative fundamental health (Margins, ROE, Debt).
- **Timing (30%)**: Technical momentum and risk-adjusted volatility (Trend, RSI, Beta).
- **Veto Logic**: Absolute "Kill Switches" for high-risk flags (Insolvency, Extreme Overvaluation).

### 3.3 Advanced Projections
- **Monte Carlo Engine**: Simulating 10,000+ price paths to define Bull/Base/Bear scenarios.
- **Risk Metrics**: Probability of loss, Value at Risk (VaR), and Analyst Consensus integration.

### 3.4 Institutional UI & High-Performance Core
- **Progressive Hydration Dashboard**: Immediate rendering of core data (Algo Baseline) followed by background hydration of deep AI layers.
- **Institutional Conviction Index**: A tri-layer synthesis of Algo, Smart Money, and Sentiment signals.
- **High-Density Briefing**: Specialized AI-generated briefings for portfolios with premium typography.
- **Global Context Bar**: Persistent real-time market pulse ticker at the application header.

## 4. User Experience Goals
- **High-Density Data**: Dashboard must show critical "at-a-glance" status without overwhelming users.
- **Mobile Responsive**: Full professional analysis available on any device.
- **Minimal Latency**: Core analysis results delivered in < 2 seconds.

## 5. Success Metrics
- **Engagement**: User retention on daily watchlist checks.
- **Accuracy**: Alignment of automated AI analysis with realized market catalysts.
- **Performance**: 99.9% uptime during US market hours.

---
See **[Architecture Overview](./ARCHITECTURE.md)** for technical implementation details.
