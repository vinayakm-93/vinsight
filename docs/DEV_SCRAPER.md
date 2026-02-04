# Developer Guide: DIY Earnings Scraper

## Overview
The earnings service (`backend/services/earnings.py`) uses a "Search -> Scrape -> Analyze" pipeline to fetch transcripts without paid financial APIs.

## Architecture

### 1. Search Strategy
The scraper uses a fallback mechanism to find the transcript URL on Motley Fool:
1.  **Serper API** (`SERPER_API_KEY`): Most reliable (Google Search API).
2.  **DuckDuckGo** (`duckduckgo-search`): Free, but rate-limited.
3.  **Google Search** (`googlesearch-python`): Last resort fallback.

### 2. Scraping & Parsing
- **Target**: `fool.com`
- **Library**: `BeautifulSoup4` + `fake-useragent`
- **Logic**: Extracts text from `div.article-body` or paragraphs.

### 3. AI Analysis
- **Model**: Groq (Llama 3.3 70B)
- **Prompt**: "Senior CFA Analyst" persona.
- **Output**: JSON with `prepared_remarks`, `qa_session`, and `verdict`.

### 4. Caching (Perpetual)
Transcripts are static. Once analyzed, we store the result forever in `finance.db` (`earnings_analysis` table).
- **Staleness**: We only re-check if the data is older than 60 days AND potentially incomplete.

## Troubleshooting
- **"Scraper Error"**: Usually means the search failed to find a URL.
    - **Fix**: Add `SERPER_API_KEY` to `.env`.
- **"AI Error"**: Check `GROQ_API_KEY`.
