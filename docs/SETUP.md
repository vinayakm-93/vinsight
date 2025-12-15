# VinSight Setup Guide

## Prerequisites

- **Python 3.10+**: [Download](https://www.python.org/downloads/)
- **Node.js 20+**: [Download](https://nodejs.org/en) (LTS version recommended)
- **Git**: [Download](https://git-scm.com/downloads)

## Development Environment Setup

### 1. Database
VinSight uses SQLite for local development. No installation required; the file `backend/finance.db` will be created automatically.

### 2. API Keys
You strictly need these keys for the app to function correctly:
1.  **JWT Secret**: Generate any random string.
2.  **API Ninjas**: For stock price data.
3.  **Groq API**: For fast AI sentiment analysis.
4.  **Google Gemini**: For deep reasoning analysis.

### 3. Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
python main.py  # Or use uvicorn main:app --reload
```
*The server will run on `http://localhost:8000`*

### 4. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```
*The UI will run on `http://localhost:3000`*

## Running Tests
We have moved verification scripts to `scripts/verify/`.
To run them:
```bash
python -m scripts.verify.verify_alert_creation
```
*(Make sure you are in the root directory)*
