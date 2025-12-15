# Architecture Overview

VinSight follows a modern **Client-Server Architecture**.

## Diagram

```mermaid
graph TD
    User[User Browser]
    FE[Next.js Frontend]
    BE[FastAPI Backend]
    DB[(SQLite/Postgres)]
    AI1[Groq API]
    AI2[Gemini API]
    Data[API Ninjas]

    User -->|HTTP| FE
    FE -->|REST API| BE
    BE -->|SQLAlchemy| DB
    BE -->|JSON| AI1
    BE -->|JSON| AI2
    BE -->|REST| Data
```

## Components

### Frontend (`/frontend`)
- **Framework**: Next.js 14 (App Router)
- **Styling**: TailwindCSS
- **State**: React Context (AuthContext, ThemeContext)
- **Charts**: Lightweight-charts

### Backend (`/backend`)
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Validation**: Pydantic models
- **Scheduler**: Apscheduler (for background stock checks)

### Database
- **Users Table**: Stores generic user info and hashed passwords.
- **Stocks Table**: Metadata about symbols.
- **Alerts Table**: Triggers configured by users.
- **Prices Table**: Historical cache.
