import logging
import json
import re
import os
from typing import Dict, Any, Optional
from services import finance, guardian
from services.reasoning_scorer import clean_thought_process
import requests
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guardian_agent")

# --- LLM Configuration ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini as fallback
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def call_deepseek(prompt: str, model: str = "deepseek/deepseek-r1:free") -> str:
    """Calls DeepSeek R1 via OpenRouter."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vinsight.app", 
        "X-Title": "VinSight"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1 # Low temp for analytical tasks
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60 
        )
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        return content
    except Exception as e:
        logger.error(f"DeepSeek call failed: {e}")
        return None

def call_gemini(prompt: str) -> str:
    """Fallback to Gemini 2.0 Flash."""
    try:
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return None

def get_llm_response(prompt: str) -> str:
    """Tries DeepSeek first, then Gemini."""
    response = call_deepseek(prompt)
    if not response and GEMINI_API_KEY:
        logger.warning("Falling back to Gemini...")
        response = call_gemini(prompt)
    
    if not response:
        raise Exception("All LLM providers failed")
        
    return clean_thought_process(response) # Remove <think> tags if present

# --- Core Functions ---

def generate_thesis_detected(symbol: str) -> str:
    """
    Auto-generates an investment thesis for a stock based on available data.
    Used when user clicks "Enable Guardian".
    """
    logger.info(f"Generating thesis for {symbol}...")
    
    # 1. Gather Data
    try:
        info = finance.get_stock_info(symbol)
        name = info.get('shortName', symbol)
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')
        summary = info.get('longBusinessSummary', '')[:500] + "..." # Truncate
        
        # Get AI Strategist summary if available (ideal) via finance/watchlist logic
        # For fast generation, we'll use a prompt with basic data
        
        prompt = f"""
        You are a seasoned Portfolio Manager. 
        Write a concise, 2-sentence investment thesis for {symbol} ({name}), a {sector} company in {industry}.
        
        Context: {summary}
        
The thesis should focus on:
        1. The primary growth driver or competitive advantage.
        2. The key risk factor to watch.
        
        Format: "Long {symbol} based on [driver/advantage]. Key risk is [risk]."
        Keep it under 50 words. Plain text only.
        """
        
        thesis = get_llm_response(prompt)
        return thesis.strip().replace('"', '')

    except Exception as e:
        logger.error(f"Failed to generate thesis for {symbol}: {e}")
        return f"Long {symbol} for exposure to {sector}. (Auto-generation failed, please edit)."


def evaluate_risk(symbol: str, thesis: str, events: list, evidence: dict) -> dict:
    """
    Evaluates if the detected events and evidence break the original thesis.
    """
    logger.info(f"Evaluating risk for {symbol}...")
    
    # Prepare Evidence String
    evidence_str = f"News Headlines:\n" + "\n".join([f"- {n['title']}" for n in evidence.get('news', [])[:3]])
    
    funds = evidence.get('fundamentals', {})
    evidence_str += f"\n\nFundamentals:\n- P/E: {funds.get('peRatio')}\n- Price: {funds.get('price')}\n"
    
    analysts = evidence.get('analyst_ratings', {})
    evidence_str += f"\nAnalyst Consensus: Target {analysts.get('target_mean')}, Rec: {analysts.get('recommendationKey')}"
    
    evidence_str += f"\n\nEvents Detected:\n" + "\n".join([f"- {e}" for e in events])
    
    prompt = f"""
    You are a Portfolio Risk Guardian.
    
    STOCK: {symbol}
    ORIGINAL THESIS: "{thesis}"
    
    NEW DATA & EVENTS:
    {evidence_str}
    
    TASK:
    Analyze if these new events fundamentally BREAK or THREATEN the original thesis.
    ignore minor noise. Focus on structural changes.
    
    OUTPUT JSON ONLY:
    {{
        "thesis_status": "INTACT" | "AT_RISK" | "BROKEN",
        "confidence": <float 0.0-1.0>,
        "reasoning": "<concise explanation, max 2 sentences>",
        "recommended_action": "HOLD" | "REDUCE" | "SELL",
        "key_evidence": ["<fact 1>", "<fact 2>"]
    }}
    """
    
    try:
        raw_response = get_llm_response(prompt)
        
        # Parse JSON
        # DeepSeek R1 might include markdown code blocks
        json_str = raw_response
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
            
        result = json.loads(json_str.strip())
        
        # Default safety checks
        if result['thesis_status'] not in ['INTACT', 'AT_RISK', 'BROKEN']:
            result['thesis_status'] = 'AT_RISK' # Fallback safety
            
        return result

    except Exception as e:
        logger.error(f"Risk evaluation failed: {e}")
        # Fail safe
        return {
            "thesis_status": "AT_RISK",
            "confidence": 0.0,
            "reasoning": "AI analysis failed, flagging for manual review.",
            "recommended_action": "HOLD",
            "key_evidence": ["AI Error"]
        }
