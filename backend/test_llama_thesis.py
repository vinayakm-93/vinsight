"""
Quick smoke test: Verify Llama 3.3 (Groq) can generate a thesis via guardian_agent.
Tests the LLM provider chain and basic JSON parsing.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from services.guardian_agent import call_groq, call_gemini, get_llm_response

print("=" * 60)
print("TEST 1: Groq/Llama direct call")
print("=" * 60)

test_prompt = """
You are a financial analyst. Write a 2-sentence investment thesis for TSLA (Tesla).
Format: "[BULLISH/BEARISH/NEUTRAL] on TSLA based on [reason]. Key risk is [risk]."
"""

result = call_groq(test_prompt)
if result:
    print(f"✅ Groq/Llama responded ({len(result)} chars):")
    print(f"   {result[:200]}")
else:
    print("❌ Groq/Llama returned None (check GROQ_API_KEY)")

print()
print("=" * 60)
print("TEST 2: get_llm_response (full fallback chain)")
print("=" * 60)

try:
    result2 = get_llm_response(test_prompt)
    print(f"✅ LLM chain responded ({len(result2)} chars):")
    print(f"   {result2[:200]}")
except Exception as e:
    print(f"❌ All providers failed: {e}")

print()
print("=" * 60)
print("TEST 3: Full thesis generation (JSON output)")
print("=" * 60)

json_prompt = """
Generate a brief investment thesis for AAPL. Output valid JSON only:
{
    "stance": "BULLISH" | "BEARISH" | "NEUTRAL",
    "one_liner": "<1 sentence>",
    "key_drivers": ["<driver 1>", "<driver 2>"],
    "primary_risk": "<risk>",
    "confidence_score": <float 1.0-10.0>
}
"""

import json
try:
    raw = get_llm_response(json_prompt)
    # Strip code fences
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    data = json.loads(raw.strip(), strict=False)
    print(f"✅ Valid JSON parsed:")
    print(f"   Stance: {data.get('stance')}")
    print(f"   One-liner: {data.get('one_liner')}")
    print(f"   Confidence: {data.get('confidence_score')}")
except json.JSONDecodeError as e:
    print(f"❌ JSON parse failed: {e}")
    print(f"   Raw: {raw[:300]}")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("All tests complete.")
