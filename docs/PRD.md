# VinSight Product Requirements Document (PRD)

**Version:** 2.0 (Post-Cloud Migration)
**Date:** December 16, 2025
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
    *   Ingests news feeds via Google News RSS.
    *   Uses **Groq (Llama 3)** for high-speed headline sentiment scoring.
*   **Earnings Deep Dive**:
    *   Uses **Gemini 1.5 Pro** to analyze financial statements and earnings call transcripts.
    *   Extracts "Bullish" and "Bearish" signals beyond just the numbers.
*   **VinSight Score**: 
    *   Composite metric (0-100) combining Technicals (RSI/MACD) + Fundamentals (P/E) + AI Sentiment.

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
