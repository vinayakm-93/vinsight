# VinSight Product Requirements Document (PRD)

**Version:** 3.0 (v6.1 Scoring Engine)
**Date:** December 17, 2025
**Status:** Live in Production

## 1. Executive Summary
VinSight is an AI-powered financial analytics platform that democratizes institutional-grade investment research. It combines real-time technical analysis with Large Language Model (LLM) reasoning to provide clear, actionable insights ("VinSight Score") for retail investors.

## 2. Core Features

### 2.1 Authentication & User Management
*   **Sign Up/Login**: Email & Password based authentication.
*   **Verification**: 6-digit email verification code (stored in Cloud SQL).
*   **Session Management**: Secure, HTTP-only persistent cookies.
*   **Security**: Rate-limiting (SlowAPI) and password hashing (PBKDF2).

### 2.2 Dashboard & Visualization
*   **Interactive Charts**: Real-time candlestick charts (TradingView/Lightweight Charts) with volume overlays.
*   **Timeframes**: Support for 1D, 1W, 1M, and Intraday periods.
*   **Watchlists**: Create, rename, and manage multiple portfolios of stocks.

### 2.3 AI Analysis Engine
*   **Sentiment Analysis**: 
    *   **Alpha Vantage** (Primary): Pre-scored sentiment with article summaries.
    *   **Groq (Llama 3.3 70B)** (Fallback): Deep headline analysis with spin detection.
    *   **Finnhub**: Insider sentiment via MSPR (Monthly Share Purchase Ratio).
*   **Earnings Deep Dive**:
    *   Uses **Gemini 1.5 Pro** to analyze financial statements and earnings call transcripts.
    *   Extracts "Bullish" and "Bearish" signals beyond just the numbers.
*   **VinSight Score v6.1**: 
    *   **Fundamentals (60 pts)**: Valuation (16), Growth (14), Margins (14), Debt (8), Institutional (4), Flow (4).
    *   **Sentiment (15 pts)**: News sentiment (10) + Insider MSPR (5).
    *   **Projections (15 pts)**: Monte Carlo upside (9) + Risk/Reward (6).
    *   **Technicals (10 pts)**: SMA distance (4), RSI zone (3), Volume (3).
*   **Sector Override**: 29 industry-specific benchmarks (P/E median 8-80 across sectors).
*   **Outlooks**: 3m (Technical), 6m (Valuation), 12m (Quality) time horizons.

### 2.4 Smart Alerts
*   **Market Watcher**: A background job that monitors prices against user targets.
*   **Conditional Trigger**: Runs only during US Market Hours (9:30 AM - 4:00 PM ET).
*   **Notification**: Email delivery for triggered events.

## 3. Technical Architecture

### 3.1 Infrastructure (Google Cloud)
*   **Compute**: 
    *   **Backend**: Google Cloud Run (Containerized FastAPI).
    *   **Frontend**: Google Cloud Run (Containerized Next.js).
    *   **Jobs**: Cloud Run Jobs (Market Watcher).
*   **Database**: 
    *   **Primary**: Cloud SQL (Managed PostgreSQL 15).
    *   **Connection**: SQLAlchemy + Psycopg2 (Connection Pooled).
*   **Scheduling**: 
    *   Cloud Scheduler triggers the Market Watcher job every 5 minutes.
*   **Security**: 
    *   **Secret Manager**: Stores all keys (DB_PASS, OPENAI_KEY, JWT_SECRET).

### 3.2 Tech Stack
*   **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion.
*   **Backend**: Python 3.11, FastAPI, Pydantic, SQLAlchemy.
*   **AI Models**: 
    *   Llama-3 (Groq) for Speed.
    *   Gemini-1.5-Pro (Vertex AI) for Reasoning.

## 4. Data Requirements
*   **Persistence**: User data and Analysis history MUST survive container restarts (Solved via Cloud SQL).
*   **Privacy**: User emails and passwords are PII and must be handled per GDPR/CCPA standards (Hashed/Salted).

## 5. Success Metrics
*   **Uptime**: 99.9% availability during market hours.
*   **Latency**: Dashboard load < 2s; AI Analysis < 10s.
*   **Cost**: Optimized for Free Tier compatibility (Cloud Run scale-to-zero).
