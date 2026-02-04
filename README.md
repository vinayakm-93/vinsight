# VinSight 📈
> **AI-Powered Stock Market Analysis Platform**

![License: Source Available](https://img.shields.io/badge/License-Source%20Available-blue)
![Status: Production](https://img.shields.io/badge/Status-Production-green)

VinSight is a comprehensive financial research tool that combines real-time stock data with AI-driven sentiment analysis to provide institutional-grade insights for the retail investor.

---

## 🚀 Key Features

- **Dual-Layer Search Engine**: Institutional-grade 70/30 composite score (Algo Baseline) paired with AI Reasoning (LLM Thesis).
- **AI Sentinel**: Multi-source news sentiment with Groq-powered reasoning, spin detection, and DIY earnings scraper.
- **Monte Carlo Projections**: 10,000+ simulated price paths with Risk Analytics (VaR, Volatility).
- **Insider Intelligence**: Discretionary trade filtering and coordinated "Cluster Selling" detection.
- **Confirmed Alerts**: Real-time price triggers delivered via authenticated SMTP.

## 🏁 Quick Start

### 1. Prerequisites
- Python 3.10+, Node.js 20+
- API Keys: [Groq](https://console.groq.com), [Google AI](https://aistudio.google.com), [Alpha Vantage](https://www.alphavantage.co), [Serper](https://serper.dev)

### 2. Setup
```bash
# Clone the repo
git clone https://github.com/vinayakm-93/vinsight.git && cd vinsight

# Backend Setup
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python main.py

# Frontend Setup (New Terminal)
cd frontend && npm install && npm run dev
```

## 📚 Documentation

The project documentation is organized for clarity:

- **[Product Requirements (PRD)](docs/PRD.md)**: Vision, target audience, and core pillars.
- **[Full Feature List](docs/FEATURES.md)**: Detailed catalog of all application features.
- **[Architecture Overview](docs/ARCHITECTURE.md)**: Technical stack, system diagrams, and data flow.
- **[Scoring Engine Logic](docs/SCORING_ENGINE.md)**: Deep dive into the v9.0 Dynamic Benchmark Model.
- **[Security & Compliance](docs/SECURITY.md)**: Security audits and rotation protocols.
- **[Maintenance Log](docs/MAINTENANCE_LOG.md)**: Bug fix history and performance RCAs.
- **[Setup & Deployment](docs/SETUP.md)**: Detailed environment and Google Cloud setup.
  > **Note**: On Google Cloud Run, the first request may take 5-10s (Cold Start) to initialize the AI engine. A dedicated loading screen handles this interaction.

---

## 📄 License
© 2024-2026 Vinayak. This project is licensed under a custom **Source Available License**.
Modification and redistribution are prohibited. See [LICENSE](LICENSE) for details.

