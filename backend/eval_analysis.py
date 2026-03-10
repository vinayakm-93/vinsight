"""
eval_analysis.py
=================
Analysis + HTML Report Generator for Thesis Bias Evaluation.

Loads eval_results.db, computes 8 statistical analyses, prints a full
console summary, and generates a self-contained eval_report.html.

Usage:
    cd backend && source venv/bin/activate
    python eval_analysis.py [--run-id <id>]   # omit for latest run

Outputs:
    Console: confusion matrix, bias score, judge dimension averages
    /tmp/eval_results/eval_report.html
"""

import os, sys, json, sqlite3, argparse
from collections import defaultdict
from datetime import datetime

DB_PATH = "/tmp/eval_results/eval_results.db"
REPORT_PATH = "/tmp/eval_results/eval_report.html"

LABELS = ["BULLISH", "NEUTRAL", "BEARISH"]
VERDICT_ORDER = ["CORRECT", "PARTIAL", "WRONG"]


def load_results(run_id=None):
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}. Run eval_thesis_bias.py first.")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if not run_id:
        run_id = conn.execute("SELECT run_id FROM thesis_runs ORDER BY id DESC LIMIT 1").fetchone()
        if not run_id:
            print("❌ No runs found in database.")
            sys.exit(1)
        run_id = run_id["run_id"]

    rows = conn.execute("""
        SELECT t.symbol, t.sector, t.ground_truth, t.stance, t.confidence_score,
               t.one_liner, t.primary_risk, t.bear_arguments_addressed, t.duration_s,
               j.stance_accuracy, j.risk_specificity, j.bear_case_engagement,
               j.calibration, j.total, j.verdict, j.judge_reasoning
        FROM thesis_runs t
        JOIN judge_scores j ON t.symbol = j.symbol AND t.run_id = j.run_id
        WHERE t.run_id = ?
        ORDER BY t.ground_truth, t.symbol
    """, (run_id,)).fetchall()
    conn.close()
    print(f"\n✅ Loaded {len(rows)} results for run_id={run_id}\n")
    return [dict(r) for r in rows], run_id


def compute_confusion_matrix(rows):
    """3x3 matrix: rows=ground_truth, cols=predicted."""
    matrix = {gt: {"BULLISH": 0, "NEUTRAL": 0, "BEARISH": 0} for gt in LABELS}
    for r in rows:
        gt = r["ground_truth"]
        pred = r.get("stance", "UNKNOWN")
        if pred in LABELS:
            matrix[gt][pred] += 1
    return matrix


def compute_accuracy_by_category(rows):
    cat = defaultdict(lambda: {"total": 0, "CORRECT": 0, "PARTIAL": 0, "WRONG": 0})
    for r in rows:
        gt = r["ground_truth"]
        v = r.get("verdict", "WRONG")
        cat[gt]["total"] += 1
        cat[gt][v] = cat[gt].get(v, 0) + 1
    return cat


def compute_judge_dimension_avgs(rows):
    dims = ["stance_accuracy", "risk_specificity", "bear_case_engagement", "calibration"]
    avgs = {d: [] for d in dims}
    for r in rows:
        for d in dims:
            if r.get(d) is not None:
                avgs[d].append(r[d])
    return {d: round(sum(v) / len(v), 2) if v else 0 for d, v in avgs.items()}


def compute_bias_score(rows):
    bearish_stocks = [r for r in rows if r["ground_truth"] == "BEARISH"]
    bullish_on_bearish = [r for r in bearish_stocks if r.get("stance") == "BULLISH"]
    return len(bullish_on_bearish), len(bearish_stocks), bullish_on_bearish


def compute_confidence_calibration(rows):
    buckets = defaultdict(list)
    for r in rows:
        v = r.get("verdict", "WRONG")
        c = r.get("confidence_score", 0)
        if c:
            buckets[v].append(float(c))
    return {v: round(sum(vals) / len(vals), 2) if vals else 0 for v, vals in buckets.items()}


def worst_performers(rows, n=5):
    sorted_rows = sorted(rows, key=lambda r: r.get("total", 0))
    return sorted_rows[:n]


def print_console_report(rows, run_id):
    print("=" * 72)
    print("  THESIS BIAS EVALUATION — ANALYSIS REPORT")
    print(f"  Run ID: {run_id}  |  Stocks: {len(rows)}")
    print("=" * 72)

    # Overall accuracy
    correct = sum(1 for r in rows if r["verdict"] == "CORRECT")
    partial = sum(1 for r in rows if r["verdict"] == "PARTIAL")
    wrong = sum(1 for r in rows if r["verdict"] == "WRONG")
    n = len(rows)
    print(f"\n📊 OVERALL ACCURACY")
    print(f"   ✅ CORRECT : {correct} / {n} ({100*correct//n}%)")
    print(f"   ⚠️  PARTIAL : {partial} / {n} ({100*partial//n}%)")
    print(f"   ❌ WRONG   : {wrong} / {n} ({100*wrong//n}%)")
    print(f"   🏆 Effective (CORRECT+PARTIAL): {correct+partial} / {n} ({100*(correct+partial)//n}%)")

    # Confusion Matrix
    matrix = compute_confusion_matrix(rows)
    print(f"\n🔢 CONFUSION MATRIX  (rows=Ground Truth, cols=Predicted)")
    print(f"   {'':12} {'BULLISH':>8} {'NEUTRAL':>8} {'BEARISH':>8}")
    print("   " + "-" * 36)
    for gt in LABELS:
        row_data = matrix[gt]
        total = sum(row_data.values()) or 1
        def cell(pred):
            count = row_data.get(pred, 0)
            marker = " ←" if gt == pred else "  "
            return f"{count:>5}({100*count//total:2d}%){marker}"
        print(f"   {gt:<12} {cell('BULLISH')} {cell('NEUTRAL')} {cell('BEARISH')}")

    # By category
    cat_acc = compute_accuracy_by_category(rows)
    print(f"\n📈 ACCURACY BY CATEGORY")
    for gt in LABELS:
        c = cat_acc[gt]
        t = c["total"] or 1
        icon = {"BULLISH": "🟢", "NEUTRAL": "🟡", "BEARISH": "🔴"}[gt]
        print(f"   {icon} {gt:<8}: CORRECT={c['CORRECT']}/{t}  PARTIAL={c['PARTIAL']}  WRONG={c['WRONG']}")

    # Bias score
    b_count, b_total, b_stocks = compute_bias_score(rows)
    bias_pct = 100 * b_count // max(b_total, 1)
    print(f"\n⚡ BULLISH BIAS ON BEARISH STOCKS")
    print(f"   {b_count}/{b_total} BEARISH stocks got BULLISH stance ({bias_pct}%)")
    if b_stocks:
        print(f"   Offenders: {', '.join(r['symbol'] for r in b_stocks)}")

    # Judge dimension averages
    dim_avgs = compute_judge_dimension_avgs(rows)
    print(f"\n🧑‍⚖️  JUDGE DIMENSION AVERAGES (out of 10)")
    bars = {k: "█" * int(v) + "░" * (10 - int(v)) for k, v in dim_avgs.items()}
    print(f"   Stance Accuracy      : {dim_avgs['stance_accuracy']:5.2f}  {bars['stance_accuracy']}")
    print(f"   Risk Specificity     : {dim_avgs['risk_specificity']:5.2f}  {bars['risk_specificity']}")
    print(f"   Bear Case Engagement : {dim_avgs['bear_case_engagement']:5.2f}  {bars['bear_case_engagement']}")
    print(f"   Calibration          : {dim_avgs['calibration']:5.2f}  {bars['calibration']}")

    # Confidence calibration
    cal = compute_confidence_calibration(rows)
    print(f"\n📐 CONFIDENCE CALIBRATION (avg model confidence_score by verdict)")
    for v in VERDICT_ORDER:
        print(f"   {v:<8}: {cal.get(v, 'N/A')}/10")

    # Worst performers
    worst = worst_performers(rows, 5)
    print(f"\n💀 WORST PERFORMERS (lowest judge total score)")
    for r in worst:
        print(f"   {r['symbol']:<6} GT={r['ground_truth']:<8} → {r['stance']:<8} | score={r['total']}/40 | {r['verdict']}")
        print(f"          Judge: {r['judge_reasoning'][:120]}...")

    # Bear case examples
    bear_examples = [r for r in rows if r["ground_truth"] == "BEARISH" and r.get("bear_arguments_addressed")]
    print(f"\n🐻 BEAR CASE FIELD EXAMPLES (3 BEARISH stocks)")
    for r in bear_examples[:3]:
        baa = (r.get("bear_arguments_addressed") or "")[:200]
        print(f"   {r['symbol']}: {baa}...")

    print("\n" + "=" * 72)
    return matrix, dim_avgs, cat_acc, cal


# ──────────────────────────────────────────────────────────────────────────────
# HTML REPORT
# ──────────────────────────────────────────────────────────────────────────────
def generate_html_report(rows, run_id, matrix, dim_avgs, cat_acc):
    correct = sum(1 for r in rows if r["verdict"] == "CORRECT")
    partial = sum(1 for r in rows if r["verdict"] == "PARTIAL")
    wrong   = sum(1 for r in rows if r["verdict"] == "WRONG")
    n = len(rows)
    effectiveness = round(100 * (correct + partial) / max(n, 1), 1)
    b_count, b_total, _ = compute_bias_score(rows)
    bias_score = round(b_count / max(b_total, 1), 2)
    dim_avgs_display = compute_judge_dimension_avgs(rows)
    worst = worst_performers(rows, 5)
    bear_examples = [r for r in rows if r["ground_truth"] == "BEARISH"][:3]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Confusion matrix cell data for Chart.js
    cm_data = [[matrix[gt].get(pred, 0) for pred in LABELS] for gt in LABELS]

    # Stance distribution: for each ground truth, counts of each output
    dist_data = {
        gt: [
            sum(1 for r in rows if r["ground_truth"] == gt and r.get("stance") == pred)
            for pred in LABELS
        ]
        for gt in LABELS
    }

    # Per-stock table rows
    def verdict_badge(v):
        colors = {"CORRECT": "#22c55e", "PARTIAL": "#f59e0b", "WRONG": "#ef4444"}
        return f'<span style="background:{colors.get(v,"#64748b")};color:white;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700">{v}</span>'

    def stance_badge(s):
        colors = {"BULLISH": "#22c55e", "NEUTRAL": "#f59e0b", "BEARISH": "#ef4444"}
        return f'<span style="background:{colors.get(s,"#64748b")};color:white;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700">{s}</span>'

    def gt_badge(gt):
        icons = {"BULLISH": "🟢", "NEUTRAL": "🟡", "BEARISH": "🔴"}
        return f'{icons.get(gt,"")} {gt}'

    table_rows = ""
    for r in rows:
        table_rows += f"""
        <tr>
          <td><strong>{r['symbol']}</strong></td>
          <td style="color:#94a3b8;font-size:12px">{r['sector']}</td>
          <td>{gt_badge(r['ground_truth'])}</td>
          <td>{stance_badge(r.get('stance','?'))}</td>
          <td>{verdict_badge(r.get('verdict','WRONG'))}</td>
          <td style="text-align:center">{r.get('total',0)}/40</td>
          <td style="text-align:center">{r.get('confidence_score',0):.1f}/10</td>
          <td style="font-size:11px;color:#94a3b8;max-width:280px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis" title="{(r.get('judge_reasoning') or '').replace(chr(34), chr(39))}">{(r.get('judge_reasoning') or '')[:100]}…</td>
        </tr>"""

    worst_cards = ""
    for r in worst:
        worst_cards += f"""
        <div style="background:#1e293b;border-left:4px solid #ef4444;padding:14px 18px;border-radius:8px;margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-size:16px;font-weight:700;color:#f8fafc">{r['symbol']}</span>
            <div>{verdict_badge(r.get('verdict','WRONG'))} {stance_badge(r.get('stance','?'))}</div>
          </div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:4px">GT: {r['ground_truth']} | Score: {r.get('total',0)}/40 | Conf: {r.get('confidence_score',0):.1f}/10</div>
          <div style="font-size:13px;color:#cbd5e1">{(r.get('judge_reasoning') or '')[:300]}</div>
        </div>"""

    bear_cards = ""
    for r in bear_examples:
        baa = (r.get('bear_arguments_addressed') or 'Not present')[:400]
        score = r.get('bear_case_engagement', 0)
        bar_w = int(score * 10)
        bear_cards += f"""
        <div style="background:#1e293b;padding:14px 18px;border-radius:8px;margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <span style="font-weight:700;color:#f8fafc">{r['symbol']}</span>
            <span style="font-size:12px;color:#94a3b8">Bear Engagement: {score}/10&nbsp;
              <span style="background:#22c55e;display:inline-block;width:{bar_w}%;height:6px;border-radius:3px;vertical-align:middle"></span>
            </span>
          </div>
          <div style="font-size:13px;color:#94a3b8;font-style:italic">{baa}</div>
        </div>"""

    # Chart.js radar data
    radar_labels = ['Stance Accuracy', 'Risk Specificity', 'Bear Case Engagement', 'Calibration']
    radar_values = [
        dim_avgs_display['stance_accuracy'],
        dim_avgs_display['risk_specificity'],
        dim_avgs_display['bear_case_engagement'],
        dim_avgs_display['calibration'],
    ]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Thesis Bias Evaluation — {ts}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f172a; color: #f8fafc; font-family: 'Inter', system-ui, sans-serif; padding: 32px; }}
  h1 {{ font-size: 22px; font-weight: 800; color: #f8fafc; }}
  h2 {{ font-size: 16px; font-weight: 700; color: #e2e8f0; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; }}
  .meta {{ font-size: 12px; color: #64748b; margin-top: 4px; margin-bottom: 32px; }}
  .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }}
  .card {{ background: #1e293b; border-radius: 12px; padding: 20px 24px; }}
  .stat-label {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px; }}
  .stat-value {{ font-size: 32px; font-weight: 800; }}
  .green {{ color: #22c55e; }} .amber {{ color: #f59e0b; }} .red {{ color: #ef4444; }} .blue {{ color: #60a5fa; }}
  section {{ margin-bottom: 40px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 10px 12px; color: #64748b; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; border-bottom: 1px solid #334155; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; vertical-align: middle; }}
  tr:hover td {{ background: #1e293b; }}
  .cm-table td {{ text-align: center; width: 80px; font-weight: 700; padding: 12px; border-radius: 6px; }}
  .cm-table .correct {{ background: #14532d; color: #86efac; }}
  .cm-table .adjacent {{ background: #713f12; color: #fde68a; }}
  .cm-table .wrong {{ background: #7f1d1d; color: #fca5a5; }}
  .cm-table .zero {{ background: #1e293b; color: #475569; }}
  .chart-wrap {{ position: relative; height: 280px; }}
</style>
</head>
<body>
<h1>🧪 Thesis Bias Evaluation Report</h1>
<p class="meta">Run ID: {run_id} &nbsp;|&nbsp; Generated: {ts} &nbsp;|&nbsp; {n} stocks evaluated</p>

<!-- ── HEADLINE STATS ── -->
<div class="grid-4">
  <div class="card">
    <div class="stat-label">Overall Accuracy</div>
    <div class="stat-value {'green' if correct/n >= .6 else 'amber' if correct/n >= .4 else 'red'}">{round(100*correct/max(n,1))}%</div>
    <div style="font-size:12px;color:#64748b;margin-top:4px">CORRECT stances ({correct}/{n})</div>
  </div>
  <div class="card">
    <div class="stat-label">Effective Rate (Correct+Partial)</div>
    <div class="stat-value {'green' if effectiveness >= 70 else 'amber' if effectiveness >= 50 else 'red'}">{effectiveness}%</div>
    <div style="font-size:12px;color:#64748b;margin-top:4px">{correct+partial}/{n} within 1 category</div>
  </div>
  <div class="card">
    <div class="stat-label">Bullish Bias Score</div>
    <div class="stat-value {'green' if bias_score <= .25 else 'amber' if bias_score <= .5 else 'red'}">{b_count}/{b_total}</div>
    <div style="font-size:12px;color:#64748b;margin-top:4px">BEARISH stocks → BULLISH output</div>
  </div>
  <div class="card">
    <div class="stat-label">Avg Bear Case Engagement</div>
    <div class="stat-value {'green' if dim_avgs_display['bear_case_engagement'] >= 6 else 'amber' if dim_avgs_display['bear_case_engagement'] >= 4 else 'red'}">{dim_avgs_display['bear_case_engagement']}/10</div>
    <div style="font-size:12px;color:#64748b;margin-top:4px">Devil's advocate effectiveness</div>
  </div>
</div>

<!-- ── CONFUSION MATRIX + RADAR ── -->
<div class="grid-2">
  <div class="card">
    <h2>Confusion Matrix</h2>
    <p style="font-size:11px;color:#64748b;margin-bottom:14px">Rows = Ground Truth &nbsp;|&nbsp; Columns = Predicted Stance</p>
    <table class="cm-table">
      <tr><th></th><th>→ BULLISH</th><th>→ NEUTRAL</th><th>→ BEARISH</th></tr>
"""
    for gt_idx, gt in enumerate(LABELS):
        html += f"      <tr><td style='color:#94a3b8;font-weight:700;text-align:left'>{gt}</td>"
        for pred_idx, pred in enumerate(LABELS):
            count = matrix[gt].get(pred, 0)
            total_gt = sum(matrix[gt].values()) or 1
            pct = round(100 * count / total_gt)
            if gt == pred:
                cls = "correct"
            elif abs(gt_idx - pred_idx) == 1:
                cls = "adjacent"
            elif count == 0:
                cls = "zero"
            else:
                cls = "wrong"
            html += f"<td class='{cls}'>{count}<br><span style='font-size:10px;opacity:.7'>{pct}%</span></td>"
        html += "</tr>\n"

    html += f"""    </table>
  </div>
  <div class="card">
    <h2>Judge Score Radar (avg /10)</h2>
    <div class="chart-wrap">
      <canvas id="radarChart"></canvas>
    </div>
  </div>
</div>

<!-- ── STANCE DISTRIBUTION ── -->
<section class="card">
  <h2>Stance Distribution — Output vs Ground Truth</h2>
  <p style="font-size:11px;color:#64748b;margin-bottom:16px">For each true category, how many stocks got each predicted stance</p>
  <div class="chart-wrap" style="height:220px">
    <canvas id="distChart"></canvas>
  </div>
</section>

<!-- ── PER-STOCK TABLE ── -->
<section class="card">
  <h2>Per-Stock Results</h2>
  <table>
    <tr>
      <th>Symbol</th><th>Sector</th><th>Ground Truth</th><th>Predicted</th>
      <th>Verdict</th><th>Score</th><th>Confidence</th><th>Judge Reasoning</th>
    </tr>
    {table_rows}
  </table>
</section>

<!-- ── WORST PERFORMERS ── -->
<section>
  <h2 style="margin-bottom:16px">💀 Worst Performers (lowest judge scores)</h2>
  {worst_cards}
</section>

<!-- ── BEAR CASE EFFECTIVENESS ── -->
<section class="card">
  <h2>🐻 Bear Case Engagement (BEARISH stock examples)</h2>
  <p style="font-size:12px;color:#64748b;margin-bottom:16px">Shows the <code>bear_arguments_addressed</code> field — did the devil's advocate step produce real arguments?</p>
  {bear_cards}
</section>

<script>
// RADAR CHART
new Chart(document.getElementById('radarChart'), {{
  type: 'radar',
  data: {{
    labels: {json.dumps(radar_labels)},
    datasets: [{{
      label: 'Average Score',
      data: {json.dumps(radar_values)},
      borderColor: '#60a5fa',
      backgroundColor: 'rgba(96,165,250,0.15)',
      pointBackgroundColor: '#60a5fa',
      pointRadius: 4,
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{ r: {{ min: 0, max: 10, ticks: {{ stepSize: 2, color: '#64748b', font: {{size: 10}} }}, grid: {{ color: '#334155' }}, pointLabels: {{ color: '#e2e8f0', font: {{size: 11}} }} }} }},
    plugins: {{ legend: {{ display: false }} }}
  }}
}});

// STANCE DISTRIBUTION CHART
new Chart(document.getElementById('distChart'), {{
  type: 'bar',
  data: {{
    labels: ['BULLISH truth', 'NEUTRAL truth', 'BEARISH truth'],
    datasets: [
      {{ label: '→ BULLISH', data: {json.dumps([dist_data[gt][0] for gt in LABELS])}, backgroundColor: 'rgba(34,197,94,0.75)', borderRadius: 4 }},
      {{ label: '→ NEUTRAL', data: {json.dumps([dist_data[gt][1] for gt in LABELS])}, backgroundColor: 'rgba(245,158,11,0.75)', borderRadius: 4 }},
      {{ label: '→ BEARISH', data: {json.dumps([dist_data[gt][2] for gt in LABELS])}, backgroundColor: 'rgba(239,68,68,0.75)', borderRadius: 4 }},
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{
      legend: {{ labels: {{ color: '#e2e8f0', font: {{size: 11}} }} }}
    }},
    scales: {{
      x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} }},
      y: {{ ticks: {{ color: '#94a3b8', stepSize: 1 }}, grid: {{ color: '#334155' }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

    with open(REPORT_PATH, 'w') as f:
        f.write(html)
    print(f"\n✅ HTML report saved to: {REPORT_PATH}")
    return REPORT_PATH


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=None, help="Specific run_id to analyze (default: latest)")
    args = parser.parse_args()

    rows, run_id = load_results(args.run_id)
    matrix, dim_avgs, cat_acc, cal = print_console_report(rows, run_id)
    report_path = generate_html_report(rows, run_id, matrix, dim_avgs, cat_acc)

    # Auto-open report
    try:
        import subprocess
        subprocess.Popen(["open", report_path])
        print(f"  🌐 Opening report in browser...\n")
    except Exception:
        print(f"  Open manually: {report_path}\n")
