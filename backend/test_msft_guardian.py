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

from services.guardian_agent import evaluate_risk_agentic

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print("\\n--- MSFT Guardian Test ---")
    print(f"Loaded OPENROUTER_API_KEY: {os.environ.get('OPENROUTER_API_KEY')[:10]}...")
    
    mock_symbol = "MSFT"
    mock_thesis = "Long MSFT due to its undisputed leadership in enterprise AI with Copilot, Azure's strong revenue growth, and robust cloud margins driving the bottom line."
    
    mock_events = [
        "OpenAI reportedly looking to renegotiate its exclusive cloud deal to diversify compute.",
        "Microsoft Azure growth slows to 29%, slightly missing the 30% whisper number."
    ]
    
    mock_evidence = {
        "news": [
            {"title": "OpenAI looking to reduce reliance on Microsoft Azure, seeks alternative compute providers."},
            {"title": "Microsoft beats on top and bottom line, but Azure growth decelerates to 29%."}
        ]
    }
    
    print("Agent is evaluating the mock MSFT news...")
    
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
