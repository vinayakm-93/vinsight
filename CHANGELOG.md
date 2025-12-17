# Changelog

## v2.5.0 - AI Score Improvements (2025-12-17)

### 🚀 New Features

#### Alpha Vantage News Integration
- Added `alpha_vantage_news.py` - new service for news with built-in sentiment
- Provides article summaries (not just headlines)
- Pre-calculated sentiment scores from Alpha Vantage
- 15-minute caching to respect rate limits
- Graceful fallback to Groq → TextBlob

#### Enhanced Sentiment Analysis
- Hybrid approach: Alpha Vantage → Groq → TextBlob fallback chain
- Removed redundant bullish keywords (LLM handles this)
- Kept bearish keywords for spin detection safety

### 🔧 Improvements

#### Industry-Standard Benchmarks
- **RSI Thresholds**: Changed from 40/80 to industry-standard 30/70
- **P/E Valuation**: Added Graham threshold (P/E < 15 = value)
- **PEG Ratio**: Peter Lynch thresholds (< 1.0 undervalued)
- **Earnings Growth**: Sector-specific thresholds (Tech needs >15%, Banks >8%)

#### Technical Scoring
- Added oversold turnaround bonus (+3 pts if RSI < 30)
- Added "Price Falling + Vol Rising" scoring
- RSI 50-65 with volume now scores 8 pts (healthy range)

#### Outlook Logic
- Added beta risk assessment for short-term signals
- Added 52-week range positioning
- Added STRONG BUY (score≥4) and WEAK HOLD ratings
- Enhanced signals with emoji indicators

### 🐛 Bug Fixes
- **Cluster Selling**: Now correctly scores 10 (not 0) for positive news + cluster selling
- **No Activity**: Added as valid insider activity type (10 pts)
- Fixed duplicate exception handlers in analysis.py

### 📦 Dependencies
- No new dependencies required

### ⚙️ Configuration
New environment variable:
```
ALPHA_VANTAGE_API_KEY=  # Optional, get free from alphavantage.co
```
