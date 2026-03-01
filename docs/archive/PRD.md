# VinSight Product Requirements Document (PRD)

**Version:** 10.0 (Dumb AI, Smart Python Redesign)
**Status:** Live in Production

## 1. Executive Summary
VinSight is an AI-powered financial analytics platform that democratizes institutional-grade investment research. It combines deterministic Python math with Large Language Model (LLM) narrative reasoning to provide clear, actionable and hallucination-free insights ("VinSight Score") for retail investors.

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
- **Deterministic Baseline**: Base scores bounded by rigid Python mathematics, multiplied by selected persona weights.
- **Kill Switches**: Absolute logic penalties applied in Python for high-risk flags (Insolvency, Extreme Overvaluation).
- **Grounding Validation**: Real-time LLM narrative sanitation. Any generated text hallucinating beyond a 5% margin of the true financial data is instantly suppressed to protect the user.

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
