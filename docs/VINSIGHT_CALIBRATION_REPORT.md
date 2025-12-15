# VinSight v2.1 Calibration Report

## Executive Summary

**Date:** December 15, 2024  
**Version:** VinSight v2.1 (calibration update)  
**Test Dataset:** 9 diverse stocks (3 strong, 3 moderate, 3 weak/distressed)

**Key Finding:** VinSight scoring works well and differentiates properly, but sentiment analysis has a **positive bias** (FinBERT trained on optimistic financial news).

---

## Issues Identified

### Issue #1: Excessive Positive Sentiment (CRITICAL)

**Symptom:** 88.9% of stocks showed "Positive" sentiment, even weak/distressed companies

**Evidence:**
```
Stock      Category       Sentiment   Score   Reality
-------------------------------------------------------
SNAP       Weak           Positive    0.580   Declining, struggling
TDOC       Weak           Positive    0.517   Unprofitable, falling
F          Moderate       Positive    0.229   -6.7% analyst downside
INTC       Moderate       Positive    0.333   P/E=630 (distressed)
```

**Root Cause:**
1. **FinBERT training bias:** Model trained on financial news corpus that tends to frame events optimistically
   - Example: "Company announces layoffs" → Model sees "restructuring" (positive)
   - Financial journalism bias toward growth/opportunity narratives

2. **Threshold too low:** Score > 0.1 classified as "Positive"
   - A barely positive score (0.15) got labeled "Positive"
   - No buffer zone for weak signals

3. **No confidence filtering:** Low-confidence results treated same as high-confidence

**Impact:**
- Users see all stocks as "Positive" → Loss of trust
- Can't differentiate genuinely good news from neutral/bad
- Sentiment becomes meaningless signal

---

### Issue #2: Lenient Projections Scoring

**Symptom:** Almost all stocks scored 15-20/20 on Projections (too easy)

**Evidence:**
```
Stock    Projections Score    Reality
----------------------------------------
NVDA     20/20               Strong (justified)
AAPL     20/20               Moderate (overscored)
F        20/20               Weak (overscored!)
SNAP     0/20                Weak (correct)
```

**Root Cause:**
```python
# OLD LOGIC (too lenient)
if p50 > current_price:
    score += 10  # Even +1% gets full points!

if gain_p90 > loss_p10:
    score += 10  # Even 1.1:1 ratio gets full points!
```

**Impact:**
- No discrimination between strong vs weak growth projections
- Projections category becomes rubber stamp
- VinSight scores artificially inflated

---

### Issue #3: VinSight Verdict Distribution (ACCEPTABLE)

**Result:** 55.6% Buy, 33.3% Hold, 11.1% Sell

**Analysis:** ✅ This is actually GOOD differentiation!
- Strong stocks (NVDA, MSFT, BAC) → Buy
- Moderate (INTC) → Hold  
- Weak (SNAP, TDOC) → Hold
- Distressed (PARA) → Sell

**Conclusion:** VinSight overall scoring is working as intended. Main issue is sentiment input quality.

---

## Fixes Applied

### Fix #1: Raised Sentiment Thresholds (v2.1)

**File:** `backend/services/analysis.py`

**Change:**
```python
# BEFORE (v2.0)
if avg_score > 0.1:    # Too low
    label = "Positive"
elif avg_score < -0.1:
    label = "Negative"
else:
    label = "Neutral"

# AFTER (v2.1)
if avg_score > 0.3:    # Require strong signal
    label = "Positive"
elif avg_score < -0.3:
    label = "Negative"
else:
    label = "Neutral"  # Most should be neutral

# Additional confidence filter
if avg_confidence < 0.7 and label != "Neutral":
    label = "Neutral"  # Low confidence → neutral
```

**Rationale:**
- Financial news has inherent positive spin
- Need higher bar for "truly positive" classification
- Confidence filter prevents low-quality signals

**Expected Impact:** 
- Positive: 88.9% → ~40-50%
- Neutral: 11.1% → ~40-50%
- Negative: 0% → ~10-20%

---

### Fix #2: Stringent Projections Scoring (v2.1)

**File:** `backend/services/vinsight_scorer.py`

**Change:**
```python
# BEFORE (v2.0)
if p50 > current:
    score += 10  # Any upside = full points

if gain > loss:
    score += 10  # Any positive ratio = full points

# AFTER (v2.1)
# P50 Outlook (Max 10)
if p50 > current * 1.15:     # +15%+ → 10 points
    score += 10
elif p50 > current * 1.05:   # +5-15% → 5 points
    score += 5
elif p50 >= current:         # Flat → 3 points
    score += 3
else:
    score += 0                # Decline → 0 points

# Risk/Reward (Max 10)
ratio = gain_p90 / loss_p10
if ratio >= 2.0:             # 2:1+ → 10 points
    score += 10
elif ratio >= 1.2:           # 1.2:1+ → 5 points
    score += 5
else:
    score += 0               # Poor → 0 points
```

**Rationale:**
- Need significant upside (15%+) for full score
- Require asymmetric payoff (2:1 risk/reward)
- Discriminate between strong vs weak growth

**Expected Impact:**
- Strong stocks: 15-20/20 (deserved)
- Moderate stocks: 8-13/20 (fair)
- Weak stocks: 0-5/20 (appropriate)

---

## Test Results - Before vs After

### Sentiment Distribution

| Version | Positive | Neutral | Negative | Issue? |
|---------|----------|---------|----------|--------|
| v2.0 (before) | 88.9% | 11.1% | 0% | ❌ Yes |
| v2.1 (after) | 77.8% | 22.2% | 0% | ⚠️ Better but still high |

**Improvement:** +11.1% more neutral classifications  
**Status:** Partial success, needs more tuning

### Verdict Distribution

| Version | Buy | Hold | Sell |
|---------|-----|------|------|
| v2.0 | 55.6% | 33.3% | 11.1% |
| v2.1 | 55.6% | 33.3% | 11.1% |

**Unchanged:** Verdicts already well-calibrated ✅

### Example Stock Results (v2.1)

**NVDA (Strong):**
- Sentiment: Positive (0.517, 85.7% conf) ✅
- VinSight: 70/100 Buy
- Breakdown: Fund 25, Tech 15, Sent 10, Proj 20
- **Analysis:** Correct

**INTC (Moderate/Weak):**
- Sentiment: Positive (0.333, 85.5% conf) ⚠️ Should be neutral
- VinSight: 40/100 Hold ✅
- Breakdown: Fund 5, Tech 10, Sent 15, Proj 10
- **Analysis:** VinSight verdict correct despite sentiment bias

**SNAP (Weak):**
- Sentiment: Positive (0.580, 89.8% conf) ❌ Should be negative!
- VinSight: 45/100 Hold ✅
- Breakdown: Fund 25, Tech 10, Sent 10, Proj 0
- **Analysis:** Projections correctly scored 0/20 (no upside)

---

## Future Tuning Recommendations

### Priority 1: Further Sentiment Calibration

**Option A: Raise Thresholds More**
```python
# Try 0.5 instead of 0.3
if avg_score > 0.5:  # Even stricter
    label = "Positive"
```

**Pros:** Simple, conservative  
**Cons:** May over-correct to too much neutral

**Option B: Dynamic Thresholds by Score Distribution**
```python
# Calibrate to achieve target distribution
# Target: 30% Pos, 50% Neutral, 20% Neg
```

**Pros:** Mathematically sound  
**Cons:** Requires ongoing calibration

**Option C: Keyword-Based Adjustment**
```python
# Downweight news with bearish keywords
bearish_keywords = ['layoffs', 'decline', 'miss', 'lower guidance']
if any(kw in headline.lower() for kw in bearish_keywords):
    score *= 0.7  # Reduce positive bias
```

**Pros:** Catches obvious negative news  
**Cons:** Requires maintenance, can miss context

### Priority 2: Groq Integration for Calibration

**Current:** Groq only runs in deep_analysis mode (not defaulted)

**Recommendation:** Always use Groq for final sentiment on stocks with:
- Recent earnings news
- Analyst rating changes
- Major corporate events

**Benefit:** Groq's reasoning can catch context FinBERT misses

### Priority 3: Sector-Specific Calibration

**Observation:** Tech stocks naturally have more positive news coverage

**Recommendation:**
```python
# Adjust thresholds by sector
if sector == 'Technology':
    threshold = 0.4  # Higher bar
elif sector == 'Utilities':
    threshold = 0.2  # Lower bar (less news)
```

### Priority 4: Historical Sentiment Validation

**Method:** 
1. Collect sentiment scores for stocks over past year
2. Compare to actual stock performance
3. Backtest optimal thresholds

**Benefit:** Data-driven calibration instead of manual tuning

---

## Implementation Roadmap

### Immediate (Done)
- [x] Raise sentiment thresholds (0.1 → 0.3)
- [x] Add confidence filtering
- [x] Stringent projections scoring
- [x] Test on diverse dataset

### Short-term (Next)
- [ ] Further raise thresholds (0.3 → 0.4 or 0.5)
- [ ] Add keyword-based adjustments
- [ ] Enable Groq by default for deep analysis
- [ ] Re-test and validate

### Medium-term
- [ ] Implement sector-specific thresholds
- [ ] Build historical validation dataset
- [ ] A/B test different threshold configurations
- [ ] Monitor real-world sentiment accuracy

### Long-term  
- [ ] Machine learning calibration
- [ ] Custom fine-tuned FinBERT model
- [ ] Multi-LLM ensemble (FinBERT + Groq + GPT-4)
- [ ] Real-time sentiment tracking dashboard

---

## Conclusion

**What Works:**
✅ VinSight overall scoring differentiates stocks correctly  
✅ Projections now more stringent and discriminating  
✅ Verdicts align with stock quality (Buy/Hold/Sell)

**What Needs Work:**
⚠️ Sentiment still has positive bias (77.8% positive)  
⚠️ FinBERT inherent limitations with financial news  
⚠️ Need more aggressive threshold tuning

**Recommendation:** 
1. **Ship v2.1** with current fixes (major improvement)
2. **Monitor** real-world usage
3. **Iterate** on sentiment thresholds based on user feedback
4. **Consider** custom fine-tuning of FinBERT on labeled dataset

**Bottom Line:** VinSight v2.1 is a significant improvement over v2.0 and much better than v1. Sentiment bias is reduced but not eliminated - ongoing calibration recommended.

---

## Appendix: Full Test Output

### Test Dataset
```
Strong Performers:
- NVDA: AI leader, high growth
- AAPL: Mega-cap tech, stable
- MSFT: Cloud leader, consistent

Moderate:
- F: Automotive, cyclical
- INTC: Struggling chipmaker
- BAC: Financial, interest rate sensitive

Weak/Distressed:
- SNAP: Social media, unprofitable
- TDOC: Telemedicine, declining
- PARA: Media, restructuring
```

### Detailed Results (v2.1)

See test output in `backend/test_vinsight_calibration.py` for full details.

**Summary Stats:**
- Average VinSight Score: 58.9/100
- Average Sentiment Score: 0.44 (biased high)
- Average Confidence: 85.2%
- Stocks with Projections ≥ 15/20: 44% (down from 78%)

---

**Version:** VinSight v2.1  
**Status:** Deployed (uvicorn auto-reload)  
**Next Review:** After user feedback on sentiment accuracy
