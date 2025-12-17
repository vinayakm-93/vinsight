# VinSight 📈
> **AI-Powered Stock Market Analysis Platform**

![License: Source Available](https://img.shields.io/badge/License-Source%20Available-blue)
![Status: Beta](https://img.shields.io/badge/Status-Beta-orange)

VinSight is a comprehensive financial research tool that combines real-time stock data with AI-driven sentiment analysis to provide actionable insights.

> **⚠️ ATTRIBUTION NOTICE**
> Created by **Vinayak**.
> This software is **Source Available**. You may download and use it, but modification and redistribution of modified versions is prohibited. See [LICENSE](LICENSE) for details.

---

## 🚀 Features

- **Real-Time Dashboard**: Interactive candlestick charts with volume data.
- **AI Sentinel**: Multi-source sentiment analysis (Alpha Vantage → Groq → TextBlob fallback).
- **VinSight Score v2.5**: Industry-aligned scoring with RSI 30/70, Graham P/E, sector-adjusted growth.
- **Smart Alerts**: Email notifications for price targets and major sentiment shifts.
- **Portfolio Tracking**: Watchlist management with daily changelog.

## 🛠️ Tech Stack

- **Frontend**: Next.js 15, TypeScript, TailwindCSS, Lightweight Charts
- **Backend**: FastAPI (Python), SQLAlchemy, Pydantic
- **AI**: Groq (Llama 3), Google Gemini
- **Database**: SQLite (Local) / PostgreSQL (Cloud)

## 🏁 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 20+
- API Keys: [Groq](https://console.groq.com), [Google AI](https://aistudio.google.com), [API Ninjas](https://api-ninjas.com)

### Installation

1.  **Clone the repo**
    ```bash
    git clone https://github.com/vinayakm-93/vinsight.git
    cd vinsight
    ```

2.  **Backend Setup**
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Frontend Setup**
    ```bash
    cd ../frontend
    npm install
    ```

4.  **Environment Setup**
    - Copy `.env.example` to `.env` in the root.
    - Fill in your API keys (`GROQ_API_KEY`, `JWT_SECRET_KEY`, etc).

5.  **Run It**
    - **Backend**: `uvicorn backend.main:app --reload`
    - **Frontend**: `npm run dev`

Visit `http://localhost:3000` to start analyzing!

## 📚 Documentation

- [Setup Guide](docs/SETUP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Features In-Depth](docs/FEATURES.md)
- [Deployment](docs/DEPLOY.md)

## 🤝 Contribution

This project is not open for public modification. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under a custom **Source Available License**.  
© 2024 Vinayak. All Rights Reserved.
