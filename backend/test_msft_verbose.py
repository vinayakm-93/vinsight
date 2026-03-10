"""
Verbose MSFT forced-trigger test.
Captures the full AI agent conversation, article count, and final verdict.
"""
import os, sys, json, logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load real keys
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
try:
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip("\"'"))
except:
    pass

logging.basicConfig(level=logging.INFO)

from services.guardian_agent import evaluate_risk_agentic

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  MSFT VERBOSE AGENTIC TEST")
    print("="*70)

    symbol = "MSFT"
    thesis = "Long MSFT because of Azure cloud dominance, AI integration via Copilot across Office 365, and strong enterprise subscription revenue."

    events = [
        "Price dropped 15% today on heavier than average volume after reports of major cloud contract losses."
    ]

    evidence = {
        "news": [
            {"title": "Microsoft loses multi-billion dollar Pentagon cloud contract to AWS."},
            {"title": "Azure growth decelerates to 26% YoY, missing analyst expectations of 30%."},
            {"title": "Google Cloud gains enterprise market share at Microsoft's expense, report says."}
        ]
    }

    print(f"\n📊 Symbol: {symbol}")
    print(f"📝 Thesis: {thesis}")
    print(f"⚡ Events: {events}")
    print(f"📰 News Articles Provided: {len(evidence['news'])}")
    for i, n in enumerate(evidence['news'], 1):
        print(f"   {i}. {n['title']}")

    print("\n" + "-"*70)
    print("  STARTING AGENTIC LOOP...")
    print("-"*70 + "\n")

    result = evaluate_risk_agentic(
        symbol=symbol,
        thesis=thesis,
        events=events,
        evidence=evidence
    )

    print("\n" + "="*70)
    print("  FINAL VERDICT")
    print("="*70)
    print(json.dumps(result, indent=2))

    print(f"\n📊 Thesis Status: {result.get('thesis_status')}")
    print(f"🎯 Confidence: {result.get('confidence')}")
    print(f"💡 Recommended Action: {result.get('recommended_action')}")
    print(f"\n🧠 AI Reasoning:")
    print(f"   {result.get('reasoning')}")
    print(f"\n📋 Key Evidence:")
    for i, ev in enumerate(result.get('key_evidence', []), 1):
        print(f"   {i}. {ev}")
