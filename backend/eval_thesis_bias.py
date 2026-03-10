"""
eval_thesis_bias.py
====================
Thesis Bias Evaluation — 30-stock LLM-as-a-Judge test.

Runs generate_investment_thesis() on 30 stocks across 3 ground-truth categories
(BULLISH / NEUTRAL / BEARISH), then uses Gemini as a judge to score each output
on 4 dimensions. Results are persisted to SQLite for downstream analysis.

Usage:
    cd backend && source venv/bin/activate
    python eval_thesis_bias.py

Outputs (all in /tmp/eval_results/):
    eval_results.db   — SQLite with thesis_runs + judge_scores tables
    raw_results.json  — full JSON backup
    eval_report.html  — visual report (auto-generated at end)
"""

import os, sys, json, sqlite3, time, uuid, logging
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
try:
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
except Exception:
    pass

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger("eval")

import google.generativeai as genai
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
_judge_model = genai.GenerativeModel('models/gemini-2.0-flash')

OUTPUT_DIR = "/tmp/eval_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)
DB_PATH = os.path.join(OUTPUT_DIR, "eval_results.db")

# ──────────────────────────────────────────────────────────────────────────────
# 30-STOCK TEST SET
# ──────────────────────────────────────────────────────────────────────────────
TEST_STOCKS = {
    "BULLISH": [
        {"symbol": "NVDA",  "sector": "Semiconductors",   "reason": "AI infrastructure dominance, data center hypergrowth"},
        {"symbol": "MSFT",  "sector": "Software",          "reason": "Azure + Copilot, recurring revenue moat"},
        {"symbol": "META",  "sector": "Social Media",      "reason": "Ad recovery, Llama AI, margin expansion"},
        {"symbol": "LLY",   "sector": "Pharma",            "reason": "GLP-1 leadership (Mounjaro/Zepbound), massive TAM"},
        {"symbol": "GE",    "sector": "Industrials",       "reason": "LEAP engine backlog, defense tailwinds"},
        {"symbol": "FICO",  "sector": "FinTech",           "reason": "Pricing power monopoly, B2B subscription growth"},
        {"symbol": "AXON",  "sector": "Defense Tech",      "reason": "Law enforcement platform lock-in, recurring SaaS"},
        {"symbol": "TTD",   "sector": "AdTech",            "reason": "CTV advertising growth, Unified ID 2.0 expansion"},
        {"symbol": "CRWD",  "sector": "Cybersecurity",     "reason": "Platform consolidation, strong NRR post-recovery"},
        {"symbol": "NVO",   "sector": "Pharma",            "reason": "Ozempic/Wegovy global scale, deep pipeline"},
    ],
    "NEUTRAL": [
        {"symbol": "AAPL",  "sector": "Consumer Tech",     "reason": "Slowing iPhone growth vs services ramp"},
        {"symbol": "JPM",   "sector": "Banking",           "reason": "Strong earnings but rate cut uncertainty"},
        {"symbol": "XOM",   "sector": "Energy",            "reason": "Solid FCF but oil price dependent"},
        {"symbol": "DIS",   "sector": "Media",             "reason": "Streaming near breakeven, parks slowing"},
        {"symbol": "AMZN",  "sector": "E-Commerce/Cloud",  "reason": "AWS re-accelerating but retail margin thin"},
        {"symbol": "BA",    "sector": "Aerospace",         "reason": "Production recovery vs massive backlog delays"},
        {"symbol": "KO",    "sector": "Consumer Staples",  "reason": "Defensive but FX and volume headwinds"},
        {"symbol": "WMT",   "sector": "Retail",            "reason": "Strong execution but valuation stretched"},
        {"symbol": "CVS",   "sector": "Healthcare",        "reason": "Diversified but margin pressure across segments"},
        {"symbol": "QCOM",  "sector": "Semiconductors",    "reason": "Mobile recovery but China risk and AI exposure"},
    ],
    "BEARISH": [
        {"symbol": "INTC",  "sector": "Semiconductors",    "reason": "Market share collapse, foundry losses, leadership flux"},
        {"symbol": "PARA",  "sector": "Media",             "reason": "Cord-cutting, streaming losses, M&A uncertainty"},
        {"symbol": "SNAP",  "sector": "Social Media",      "reason": "User stagnation, ad revenue structurally challenged"},
        {"symbol": "TDOC",  "sector": "Telehealth",        "reason": "Goodwill writedowns, profitability elusive"},
        {"symbol": "NYCB",  "sector": "Regional Bank",     "reason": "CRE exposure, deposit outflows, dilution"},
        {"symbol": "MPW",   "sector": "REIT",              "reason": "Tenant defaults, dividend cuts, massive debt"},
        {"symbol": "PFE",   "sector": "Pharma",            "reason": "Post-COVID revenue cliff, pipeline writedowns"},
        {"symbol": "WBD",   "sector": "Media",             "reason": "Cord-cutting + debt mountain, no streaming path"},
        {"symbol": "SMCI",  "sector": "Servers",           "reason": "Audit delays, short-seller reports, governance issues"},
        {"symbol": "AI",    "sector": "AI Software",       "reason": "Persistent losses, revenue growth decelerating"},
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# DATABASE SETUP
# ──────────────────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS thesis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            ts TEXT,
            symbol TEXT,
            sector TEXT,
            ground_truth TEXT,
            stance TEXT,
            confidence_score REAL,
            one_liner TEXT,
            primary_risk TEXT,
            bear_arguments_addressed TEXT,
            duration_s REAL,
            raw_json TEXT
        );
        CREATE TABLE IF NOT EXISTS judge_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            symbol TEXT,
            ground_truth TEXT,
            stance TEXT,
            stance_accuracy INTEGER,
            risk_specificity INTEGER,
            bear_case_engagement INTEGER,
            calibration INTEGER,
            total INTEGER,
            verdict TEXT,
            judge_reasoning TEXT
        );
    """)
    conn.commit()
    return conn

def save_run(conn, run_id, symbol, sector, ground_truth, thesis_data, duration_s):
    conn.execute("""
        INSERT INTO thesis_runs
        (run_id,ts,symbol,sector,ground_truth,stance,confidence_score,one_liner,
         primary_risk,bear_arguments_addressed,duration_s,raw_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        run_id, datetime.utcnow().isoformat(), symbol, sector, ground_truth,
        thesis_data.get('stance', 'UNKNOWN'),
        thesis_data.get('confidence_score', 0.0),
        thesis_data.get('one_liner', ''),
        thesis_data.get('primary_risk', ''),
        thesis_data.get('bear_arguments_addressed', ''),
        duration_s,
        json.dumps(thesis_data)
    ))
    conn.commit()

def save_judge(conn, run_id, symbol, ground_truth, stance, scores):
    conn.execute("""
        INSERT INTO judge_scores
        (run_id,symbol,ground_truth,stance,stance_accuracy,risk_specificity,
         bear_case_engagement,calibration,total,verdict,judge_reasoning)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        run_id, symbol, ground_truth, stance,
        scores.get('stance_accuracy', 0),
        scores.get('risk_specificity', 0),
        scores.get('bear_case_engagement', 0),
        scores.get('calibration', 0),
        scores.get('total', 0),
        scores.get('verdict', 'WRONG'),
        scores.get('judge_reasoning', '')
    ))
    conn.commit()

# ──────────────────────────────────────────────────────────────────────────────
# THESIS RUNNER
# ──────────────────────────────────────────────────────────────────────────────
def run_thesis(symbol: str) -> tuple[Optional[dict], float]:
    """Call generate_investment_thesis and time it."""
    from services.guardian_agent import generate_investment_thesis
    t0 = time.time()
    try:
        result = generate_investment_thesis(symbol)
        return result, round(time.time() - t0, 2)
    except Exception as e:
        logger.error(f"Thesis generation failed for {symbol}: {e}")
        return None, round(time.time() - t0, 2)

# ──────────────────────────────────────────────────────────────────────────────
# LLM JUDGE
# ──────────────────────────────────────────────────────────────────────────────
JUDGE_PROMPT_TEMPLATE = """
You are an expert evaluator of AI-generated investment theses. You will score a thesis output against ground truth.

STOCK: {symbol}
SECTOR: {sector}
GROUND TRUTH CATEGORY: {ground_truth}
  (This reflects publicly known market consensus based on: {reason})

MODEL OUTPUT:
  Stance:    {stance}
  Confidence Score: {confidence}/10
  One-Liner: {one_liner}
  Primary Risk: {primary_risk}
  Bear Case Addressed: {bear_arguments_addressed}
  Content Excerpt (first 400 chars): {content_excerpt}

SCORING INSTRUCTIONS — grade each dimension 0–10:

1. STANCE_ACCURACY (0–10):
   - 10: Stance exactly matches ground truth
   - 6–9: Adjacent miss (NEUTRAL for BULLISH/BEARISH, or BULLISH for NEUTRAL)
   - 0–4: Opposite direction (BULLISH for BEARISH stock, or BEARISH for BULLISH stock)
   Note: A BULLISH rating on a known BEARISH stock is a serious failure (score 0–2).

2. RISK_SPECIFICITY (0–10):
   - 10: Identifies a concrete, company-specific risk with actual data points
   - 5–7: Names a real risk category but remains generic  
   - 0–4: Boilerplate ("competition", "macro uncertainty", "regulatory risk") with no specifics

3. BEAR_CASE_ENGAGEMENT (0–10):
   - 10: bear_arguments_addressed shows it found real, specific bearish arguments AND made a clear decision to accept/reject them
   - 5–7: Mentions bear case but hand-waves with vague optimism
   - 0–4: Empty, "No bear case" placeholder, or the field is missing/trivial

4. CALIBRATION (0–10):
   - 10: Confidence score is appropriate for the stock's true uncertainty
     (High confidence ~8–10 for unambiguous BULLISH/BEARISH makes sense; 
      High confidence for a NEUTRAL/mixed stock is WRONG)
   - 5–7: Slight miscalibration
   - 0–4: Highly overconfident on an uncertain stock, or underconfident on a clear case

VERDICT:
- CORRECT: stance exactly matches ground truth
- PARTIAL: one category off (e.g., NEUTRAL when truth is BULLISH, or NEUTRAL when truth is BEARISH)
- WRONG: directly opposite (BULLISH when truth is BEARISH, or vice versa)

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "stance_accuracy": <int 0-10>,
  "risk_specificity": <int 0-10>,
  "bear_case_engagement": <int 0-10>,
  "calibration": <int 0-10>,
  "total": <sum of above, 0-40>,
  "verdict": "CORRECT|PARTIAL|WRONG",
  "judge_reasoning": "<2-3 sentences explaining your verdict and key weaknesses found>"
}}
"""

def llm_judge(symbol: str, sector: str, ground_truth: str, reason: str, thesis: dict) -> dict:
    """Use Gemini to score a thesis output against its ground truth."""
    content = thesis.get('content', '') or ''
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        symbol=symbol,
        sector=sector,
        ground_truth=ground_truth,
        reason=reason,
        stance=thesis.get('stance', 'UNKNOWN'),
        confidence=thesis.get('confidence_score', '?'),
        one_liner=thesis.get('one_liner', ''),
        primary_risk=thesis.get('primary_risk', ''),
        bear_arguments_addressed=thesis.get('bear_arguments_addressed', '[NOT PRESENT]'),
        content_excerpt=content[:400].replace('\n', ' ')
    )
    try:
        resp = _judge_model.generate_content(prompt)
        raw = resp.text.strip()
        if '```' in raw:
            raw = raw.split('```')[1].split('```')[0]
            if raw.startswith('json'):
                raw = raw[4:]
        scores = json.loads(raw.strip())
        # Clamp and validate
        for k in ['stance_accuracy', 'risk_specificity', 'bear_case_engagement', 'calibration']:
            scores[k] = max(0, min(10, int(scores.get(k, 0))))
        scores['total'] = sum(scores[k] for k in ['stance_accuracy', 'risk_specificity', 'bear_case_engagement', 'calibration'])
        if scores.get('verdict') not in ['CORRECT', 'PARTIAL', 'WRONG']:
            scores['verdict'] = 'WRONG'
        return scores
    except Exception as e:
        logger.error(f"Judge failed for {symbol}: {e}")
        return {
            "stance_accuracy": 0, "risk_specificity": 0,
            "bear_case_engagement": 0, "calibration": 0,
            "total": 0, "verdict": "WRONG",
            "judge_reasoning": f"Judge call failed: {e}"
        }

# ──────────────────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────────────
def main():
    run_id = str(uuid.uuid4())[:8]
    conn = init_db()
    all_results = []

    print(f"\n{'='*72}")
    print(f"  THESIS BIAS EVALUATION  |  run_id={run_id}  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  30 stocks × 2 LLM calls each. Expected ~10–12 min.")
    print(f"{'='*72}\n")

    total = sum(len(v) for v in TEST_STOCKS.values())
    idx = 0

    for ground_truth, stocks in TEST_STOCKS.items():
        gt_icon = {"BULLISH": "🟢", "NEUTRAL": "🟡", "BEARISH": "🔴"}[ground_truth]
        print(f"\n{gt_icon}  Ground Truth: {ground_truth}")
        print(f"{'─'*60}")

        for stock in stocks:
            idx += 1
            symbol = stock["symbol"]
            sector = stock["sector"]
            reason = stock["reason"]

            print(f"  [{idx:02d}/{total}] {symbol:<6} ({sector})", end=" ", flush=True)

            # Step 1: Generate thesis
            thesis, duration = run_thesis(symbol)

            if thesis is None:
                print("❌ THESIS FAILED")
                result = {
                    "symbol": symbol, "sector": sector,
                    "ground_truth": ground_truth, "reason": reason,
                    "thesis": None, "duration_s": duration,
                    "judge": None, "error": True
                }
                all_results.append(result)
                continue

            stance = thesis.get('stance', 'UNKNOWN')
            conf = thesis.get('confidence_score', 0)

            # Step 2: Judge it
            judge_scores = llm_judge(symbol, sector, ground_truth, reason, thesis)
            verdict = judge_scores.get('verdict', 'WRONG')
            verdict_icon = {"CORRECT": "✅", "PARTIAL": "⚠️", "WRONG": "❌"}[verdict]

            print(f"→ {stance:<8} ({conf:.1f}/10 conf)  {verdict_icon} {verdict}  [{judge_scores['total']}/40]")

            # Save to DB
            save_run(conn, run_id, symbol, sector, ground_truth, thesis, duration)
            save_judge(conn, run_id, symbol, ground_truth, stance, judge_scores)

            all_results.append({
                "symbol": symbol, "sector": sector,
                "ground_truth": ground_truth, "reason": reason,
                "thesis": thesis, "duration_s": duration,
                "judge": judge_scores, "error": False
            })

            time.sleep(0.5)  # Gentle rate limiting

    # Save JSON backup
    json_path = os.path.join(OUTPUT_DIR, "raw_results.json")
    with open(json_path, 'w') as f:
        json.dump({"run_id": run_id, "timestamp": datetime.utcnow().isoformat(), "results": all_results}, f, indent=2)

    # Quick summary
    valid = [r for r in all_results if not r.get('error') and r.get('judge')]
    correct = sum(1 for r in valid if r['judge']['verdict'] == 'CORRECT')
    partial = sum(1 for r in valid if r['judge']['verdict'] == 'PARTIAL')
    wrong = sum(1 for r in valid if r['judge']['verdict'] == 'WRONG')

    print(f"\n{'='*72}")
    print(f"  QUICK SUMMARY")
    print(f"{'─'*72}")
    print(f"  Evaluated: {len(valid)}/{total} stocks")
    print(f"  ✅ CORRECT:  {correct} ({100*correct//max(len(valid),1)}%)")
    print(f"  ⚠️  PARTIAL:  {partial} ({100*partial//max(len(valid),1)}%)")
    print(f"  ❌ WRONG:    {wrong} ({100*wrong//max(len(valid),1)}%)")

    # Bias check — BULLISH outputs on BEARISH stocks
    bearish_stocks = [r for r in valid if r['ground_truth'] == 'BEARISH']
    bullish_on_bearish = sum(1 for r in bearish_stocks if r['thesis'] and r['thesis'].get('stance') == 'BULLISH')
    print(f"\n  🎯 Bias Score: {bullish_on_bearish}/10 BEARISH stocks got BULLISH stance")
    print(f"  📁 DB saved to: {DB_PATH}")
    print(f"  📄 JSON saved to: {json_path}")
    print(f"{'='*72}\n")
    print("  Run `python eval_analysis.py` for full analysis + HTML report.\n")

    conn.close()
    return run_id

if __name__ == "__main__":
    main()
