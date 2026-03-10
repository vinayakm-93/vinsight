import os
import json
import pytest
import logging
from typing import List, Dict
from dotenv import load_dotenv

# Set up logging to see errors
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = os.path.join(os.getcwd(), '.env')
print(f"Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path)

print(f"GROQ_API_KEY present: {bool(os.getenv('GROQ_API_KEY'))}")
print(f"GEMINI_API_KEY present: {bool(os.getenv('GEMINI_API_KEY'))}")

from services.groq_sentiment import get_groq_analyzer

# The Golden Dataset: Adversarial PR Spin Cases
GOLDEN_DATASET = [
    {
        "ticker": "TECH1",
        "text": "TechCorp reports record revenue of $10B, but warns that 2026 growth will decelerate due to shifting macro conditions and rising R&D costs.",
        "expected_label": "negative",
        "expected_score_max": -0.1,
        "type": "Hidden Guidance Cut"
    },
    {
        "ticker": "AUTO1",
        "text": "AutoGiant announces a $5B share buyback program. Simultaneously, the company filed a 10-K indicating it will issue $7B in new debt at 8% interest to cover pension liabilities.",
        "expected_label": "negative",
        "expected_score_max": -0.1,
        "type": "Toxic Buyback"
    }
]

@pytest.fixture
def analyzer():
    a = get_groq_analyzer()
    if not a.is_available:
        print("Analyzer NOT available - checking keys...")
        # Force re-init if singleton was created without keys
        from services.groq_sentiment import GroqSentimentAnalyzer
        return GroqSentimentAnalyzer()
    return a

def test_adversarial_spin_filtering(analyzer):
    print("\n" + "="*80)
    print("SENTIMENT ENGINE ADVERSARIAL EVALUATION")
    print("="*80)
    
    passes = 0
    total = len(GOLDEN_DATASET)
    
    for case in GOLDEN_DATASET:
        print(f"\nEvaluating Type: {case['type']}")
        
        result = analyzer.analyze(case['text'], context=case['ticker'])
        
        actual_label = result['label']
        actual_score = result['score']
        reasoning = result['reasoning']
        
        is_success = actual_label == case['expected_label']
        if is_success: passes += 1
        
        print(f"Status: {'✅ PASS' if is_success else '❌ FAIL'}")
        print(f"Expected: {case['expected_label']} | Actual: {actual_label} (Score: {actual_score})")
        print(f"Reasoning: {reasoning}")
    
    print(f"\nFINAL RESULT: {passes}/{total}")
    assert passes >= 1
