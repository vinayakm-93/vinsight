# VinSight 📈 | Autonomous AI Financial Analyst

<div align="center">
  
![License: Source Available](https://img.shields.io/badge/License-Source%20Available-blue)
![Status: Production](https://img.shields.io/badge/Status-Production-green)
![Version](https://img.shields.io/badge/Version-v13.0-orange)
![Tech Stack](https://img.shields.io/badge/Tech-Next.js%20%7C%20Python%20%7C%20DeepSeek%20%7C%20Llama%203.3-black)

**Institutional-grade quantitative scoring meets multi-agent AI debate.**  
VinSight strips away corporate PR spin to give retail investors ruthless, empirical truth.

![VinSight Dashboard Demo](docs/assets/vinsight_demo.webp)

</div>

---

## 🛑 The Problem: Information Asymmetry
Retail investors operate at a massive disadvantage. They are bombarded with corporate PR spin, overwhelmed by dense 10-K SEC filings, and lack access to the rigorous quantitative models used by hedge funds. Standard AI tools fail here—they suffer from confirmation bias and hallucinate financial math.

## 💡 The Solution: VinSight v13
VinSight is an **Agentic Financial Ecosystem**. It doesn't just fetch stock prices; it actively debates them. By combining a deterministic **Three-Axis Quant Engine** with a **Multi-Agent Debate Scaffolding** powered by DeepSeek R1, VinSight acts as an uncompromised, fiduciary co-pilot.

---

## 🚀 Core Pillars

### 🧠 1. The Intelligence Layer (Agent Scaffolding)
VinSight eliminates AI confirmation bias through structured adversarial debate.
*   **The Guardian Agent (Debate Model)**: Before a thesis is generated, VinSight spawns parallel **Bull** and **Bear** AI agents. They independently search the web, debate thesis weaknesses, and present findings to a Judge LLM (DeepSeek R1). 
*   **Spin Detection**: A proprietary bearish-keyword heuristic mathematically flags and penalizes corporate PR "spin," successfully dropping the platform's positive sentiment bias from 89% to 33%.
*   **Zero-Cost SEC RAG**: We bypass expensive vector databases. Using Gemini 2.0 Flash, VinSight pre-summarizes 10-K/10-Q risk factors into pure text blocks cached in SQLite, guaranteeing 100% recall of corporate risks without hallucination.

### 📐 2. The Quant Engine (Ruthless Objectivity)
Python math is the sole authority for scoring; the LLM merely provides narrative.
*   **Three-Axis Framework**: Stocks are evaluated independently on **Quality** (Health), **Value** (Cheapness), and **Timing** (Momentum), ensuring a high-quality but overvalued stock isn't blindly recommended.
*   **Residual Income Model (RIM)**: Intrinsic valuation is calculated using RIM and WACC estimations to determine a true **Margin of Safety**.
*   **Persona Conviction Matrix**: The final 0-100 score is dynamically weighted based on user profiles (CFA, Momentum, Value, Growth).
*   **Fiduciary Data Refusal (The 50% Rule)**: If upstream APIs are starved of data (e.g., recent IPOs), the engine aborts the calculation and explicitly neutralizes the score to prevent bizarre edge-case inflations.

### 📊 3. Empirical Validation (Backtested Results)
VinSight isn't just theoretical. The v13 engine has been rigorously backtested over 12-month historical point-in-time snapshots to validate predictive power.
*   🏆 **Elite Tier (80-100 Score)**: Empirically achieves a **72% win-rate at 3 months** and a **100% win-rate at 12 months**.
*   📈 **Alpha Generation**: Delivers **+7.4% excess return** over the S&P 500 benchmark.
*   🛑 **Avoid Tier (0-49 Score)**: Achieves a 0% hit rate at 12 months, validating the continuous outlier penalty logic.

---

## 🏗️ Technical Architecture
VinSight is built for speed and resilience, utilizing progressive hydration to instantly render quantitative math while background agents process deep reasoning.

| Component | Technology Stack | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Next.js 14, Tailwind CSS, Lightweight-Charts | High-performance progressive hydration dashboard |
| **Backend** | Python 3.10+, FastAPI | High-concurrency quantitative engine & orchestration |
| **Data Layer** | SQLite, PostgreSQL, Secret Manager | Pure Text RAG context caching & User profiles |
| **LLM Routing** | Llama 3.3 (Groq), DeepSeek R1, Gemini 2.0 | Multi-provider cognitive routing based on latency/reasoning needs |
| **Infrastructure** | Google Cloud Run, Cloud Scheduler | Serverless scaling and background Guardian jobs |

👉 **Deep Dive:** Read the [Technical System Design (v13.0)](docs/SYSTEM_DESIGN.md) document for a complete architectural breakdown.

---

## 🏁 Developer Quick Start

### 1. Prerequisites
- Python 3.10+, Node.js 20+
- API Keys: [Groq](https://console.groq.com), [Google AI](https://aistudio.google.com), [Alpha Vantage](https://www.alphavantage.co), [Serper](https://serper.dev)

### 2. Local Setup
```bash
# Clone the repository
git clone https://github.com/vinayakm-93/vinsight.git && cd vinsight

# Terminal 1: Start Backend Engine
cd backend 
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py

# Terminal 2: Start Frontend Dashboard
cd frontend 
npm install 
npm run dev
```
*Note: On first run, the AI engine requires 5-10s to hydrate initial SEC contexts.*

---

## 📚 Project Documentation

- **[Technical System Design](docs/SYSTEM_DESIGN.md)**: Deep dive into Agent Scaffolding, LLM Routing, and the Quant Engine.
- **[Full Feature Catalog](docs/FEATURES.md)**: Comprehensive list of all dashboard and API features.
- **[Architecture & Flow](docs/ARCHITECTURE.md)**: Cloud topology and deployment architecture diagrams.
- **[Scoring Engine Math](docs/SCORING_ENGINE.md)**: The explicit formulas driving the Three-Axis scores and outlier penalties.
- **[Security & Setup](docs/SETUP.md)**: Environment configuration and OWASP compliance protocols.
- **[Maintenance Log](docs/ADR/MAINTENANCE_LOG.md)**: Root Cause Analyses and architectural decision records.

---

## 📄 License
© 2024-2026 Vinayak. This project is licensed under a custom **Source Available License**. Modification and redistribution are prohibited. See [LICENSE](LICENSE) for details.
