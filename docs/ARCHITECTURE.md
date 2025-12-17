# Architecture Overview

VinSight follows a modern **Client-Server Architecture** with a **Proxy Layer** for cookie handling.

## Diagram

```mermaid
graph TD
    User[User Browser]
    FE[Next.js Frontend]
    Proxy[Next.js Rewrites Proxy]
    BE[FastAPI Backend]
    DB[(PostgreSQL / SQLite)]
    AI1[Groq API]
    AI2[Gemini API]
    AV[Alpha Vantage API]
    Data[yfinance]

    User -->|HTTP| FE
    FE -->|/api/* requests| Proxy
    Proxy -->|Forward + Cookies| BE
    BE -->|SQLAlchemy| DB
    BE -->|Sentiment| AI1
    BE -->|Earnings| AI2
    BE -->|News + Sentiment| AV
    BE -->|Stock Data| Data
```

## Components

### Frontend (`/frontend`)
- **Framework**: Next.js 16 (App Router)
- **Styling**: TailwindCSS
- **State**: React Context (AuthContext, ThemeContext)
- **Charts**: Lightweight-charts
- **Proxy**: `next.config.js` rewrites `/api/*` to backend

### Backend (`/backend`)
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Validation**: Pydantic models
- **Config**: `redirect_slashes=False` for proxy compatibility

### AI Services (v2.5)
| Service | Purpose | Fallback |
|---------|---------|----------|
| **Alpha Vantage** | News sentiment (pre-scored) | Groq |
| **Groq (Llama 3.3 70B)** | Deep headline analysis | TextBlob |
| **Gemini** | Earnings report analysis | - |

### Database
- **Users Table**: Stores user info, hashed passwords, alert limits.
- **Watchlists Table**: User watchlists with comma-separated tickers.
- **Alerts Table**: Price alert triggers configured by users.
- **Stocks Table**: Metadata about symbols.
