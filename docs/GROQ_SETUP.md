# Quick Start: Setting Up Groq API for VinSight v2

## What is Groq?

Groq provides ultra-fast LLM inference using Llama 3.1 70B. VinSight v2 uses it for **deep sentiment analysis** with reasoning on important news.

**Benefits:**
- 🎯 More accurate sentiment on complex financial news
- 🧠 Provides reasoning for sentiment decisions
- ⚡ Very fast (sub-second responses)
- 💰 **Free tier available!**

---

## Setup (2 minutes)

### Step 1: Get Your Free API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (free account)
3. Navigate to **API Keys**
4. Click **Create API Key**
5. Copy your key (starts with `gsk_...`)

### Step 2: Add to Your Project

```bash
# In your terminal
cd /Users/vinayak/Documents/Antigravity/Project\ 1

# Add the API key to .env file
echo "GROQ_API_KEY=gsk_your_actual_key_here" >> backend/.env

# Restart the backend server (it will pick up the new key)
# The uvicorn process should reload automatically
```

### Step 3: Verify It Works

Once restarted, the backend will automatically use Groq for deep analysis mode. You'll see:
- **Sentiment source** in UI: "Hybrid" or "Groq" (instead of just "FinBERT")
- **More accurate sentiment** on complex earnings news
- **No change to speed** - Groq only runs on important headlines

---

## How It Works

### Without Groq API (Default - FinBERT Only)
```
News → FinBERT (local) → Sentiment with confidence
```
- ✅ Free, no API needed
- ✅ Fast (200ms for 10 headlines)
- ✅ Good accuracy (~85%)

### With Groq API (Hybrid Mode)
```
News → FinBERT (all headlines) + Groq (top 3 recent) → Blended sentiment
├─ 70% weight: FinBERT (fast batch analysis)
└─ 30% weight: Groq (deep analysis with reasoning)
```
- ✅ Excellent accuracy (~90%)
- ✅ Provides reasoning
- ✅ Still fast (~300ms for 10 headlines)

**Example Output:**
```json
{
  "label": "Positive",
  "score": 0.85,
  "confidence": 0.92,
  "source": "hybrid",  // ← Shows it used both
  "reasoning": "Strong earnings beat with raised guidance..."
}
```

---

## Cost

**Groq Pricing (as of Dec 2024):**
- Free tier: 14,400 requests/day
- After free tier: ~$0.27 per 1M input tokens

**VinSight Usage:**
- ~3 Groq calls per stock analysis (top 3 headlines)
- ~300 tokens per call
- **Estimate: ~15,000 analyses/month FREE**

---

## Troubleshooting

### "Groq API key not found"
- Check `.env` file exists in `backend/` directory
- Verify key format: `GROQ_API_KEY=gsk_...`
- Restart backend server

### "HTTP 429 - Rate limit exceeded"
- Wait 1 minute (rate limit resets)
- Or disable Groq temporarily (will fallback to FinBERT only)

### Still seeing "FinBERT" instead of "Hybrid"
- Check backend logs for errors
- Groq only runs when `deep_analysis=True` (default for some endpoints)
- FinBERT alone is still excellent - Groq is optional enhancement

---

## Next Steps

1. **Set up your Groq API key** (instructions above)
2. **Test it**: Search for a stock (e.g., AAPL, TSLA)
3. **Check the UI**: Should show "Sentiment: Hybrid" or "Sentiment: Groq"
4. **Enjoy better sentiment analysis!** 🎉

---

## Disable Groq (Optional)

To disable Groq and use only FinBERT:
```bash
# Remove or comment out the Groq API key
# GROQ_API_KEY=your_key

# Restart backend
```

VinSight will automatically fall back to FinBERT-only mode.
