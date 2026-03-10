import os
import json
import logging
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
try:
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('OPENROUTER_API_KEY='):
                os.environ['OPENROUTER_API_KEY'] = line.strip().split('=', 1)[1].strip("\"'")
            elif line.startswith('GEMINI_API_KEY='):
                os.environ['GEMINI_API_KEY'] = line.strip().split('=', 1)[1].strip("\"'")
except Exception as e:
    print(f"Failed to load .env: {e}")

# Now import the agent
from services.guardian_agent import evaluate_risk_agentic

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print("\\n--- Phase 3 Local Stability Test ---")
    print(f"Loaded OPENROUTER_API_KEY: {os.environ.get('OPENROUTER_API_KEY')[:10]}...")
    
    mock_symbol = "RDDT"
    mock_thesis = "Long RDDT because of high user engagement, lucrative data licensing deals with AI companies like Google and OpenAI, and strong ad revenue growth."
    
    mock_events = [
        "Price dropped 15% today after the post-IPO insider lockup period expired and massive selling volume occurred."
    ]
    
    mock_evidence = {
        "news": [
            {"title": "Reddit lockup period expires, insider selling tanks stock by 15%."},
            {"title": "Reddit signs new data licensing agreement with major AI firm, but ad revenue growth shows slight deceleration in Q3."}
        ]
    }
    
    print("Agent is evaluating the mock breaking news...")
    
    result = evaluate_risk_agentic(
        symbol=mock_symbol,
        thesis=mock_thesis,
        events=mock_events,
        evidence=mock_evidence
    )
    
    print("\\n--- Final Verdict Output ---")
    print(json.dumps(result, indent=2))
    
    if result.get("thesis_status") in ["AT_RISK", "BROKEN"]:
        print("\\n✅ Passed: Agent correctly identified the thesis threat.")
    else:
        print("\\n❌ Failed: Agent missed the fundamental shift.")
