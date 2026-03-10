import logging
import json
import re
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Explicitly load .env from project root or backend dir
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

from services import finance, guardian
from services.reasoning_scorer import clean_thought_process
from services.sec_summarizer import get_sec_summaries
from services.web_search import WebSearchBackend
from database import SessionLocal
import google.generativeai as genai
import requests
from groq import Groq

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guardian_agent")

# Agent Thinking Log — multi-tenant structured trace of every step the agent takes
active_scan_logs: Dict[str, list] = {}

def log_agent_thought(stage: str, content: str, scan_id: str = None):
    """Append a structured entry to the agent's thinking log for a specific scan."""
    import time
    entry = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "stage": stage, "content": content}
    
    if scan_id:
        if scan_id not in active_scan_logs:
            active_scan_logs[scan_id] = []
        active_scan_logs[scan_id].append(entry)
        
    logger.info(f"[AGENT THOUGHT] [{stage}] {content[:200]}")

def ground_evidence(key_evidence: list, research_history: list, scan_id: str = None) -> list:
    """
    Evidence Grounding Guardrail.
    Cross-checks each piece of key_evidence against the actual research_history.
    Marks ungrounded evidence with a [UNVERIFIED] tag.
    """
    if not research_history:
        return [f"[UNVERIFIED] {e}" for e in key_evidence]
    
    history_blob = " ".join(research_history).lower()
    grounded = []
    for evidence in key_evidence:
        # Check if any significant words from the evidence appear in research
        words = [w.lower() for w in evidence.split() if len(w) > 4]
        match_count = sum(1 for w in words if w in history_blob)
        match_ratio = match_count / max(len(words), 1)
        
        if match_ratio >= 0.3:  # At least 30% of meaningful words found
            grounded.append(evidence)
        else:
            grounded.append(f"[UNVERIFIED] {evidence}")
            log_agent_thought("GROUNDING", f"Evidence NOT grounded: '{evidence}'", scan_id=scan_id)
    
    return grounded

# --- LLM Functions ---

# Groq Client Initialization (Llama 3.3 — Primary for thesis generation)
_groq_client = None
def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            _groq_client = Groq(api_key=api_key, timeout=30.0, max_retries=0)
    return _groq_client

def call_groq(prompt: str) -> str:
    """Primary LLM: Llama 3.3 70B via Groq (fast, reliable)."""
    client = _get_groq_client()
    if not client:
        logger.warning("GROQ_API_KEY not configured. Skipping Groq/Llama.")
        return None
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an elite hedge fund analyst. Output only what is requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2500,
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq/Llama call failed: {e}")
        return None

def call_deepseek(prompt: str, model: str = "deepseek/deepseek-r1:free") -> str:
    """Secondary LLM: DeepSeek R1 via OpenRouter (deep reasoning)."""
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.env')
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('OPENROUTER_API_KEY='):
                        api_key = line.strip().split('=', 1)[1]
                        os.environ['OPENROUTER_API_KEY'] = api_key
        except:
            pass
            
    if not api_key:
        logger.warning(f"OPENROUTER_API_KEY NOT FOUND. Skipping DeepSeek.")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vinsight.app", 
        "X-Title": "VinSight"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
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
    """Tertiary fallback: Gemini 2.0 Flash."""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return None

def get_llm_response(prompt: str) -> str:
    """Tries Groq/Llama first, then DeepSeek, then Gemini."""
    # 1. Groq / Llama 3.3 (Primary — fast, reliable)
    response = call_groq(prompt)
    if response:
        return clean_thought_process(response)
    
    # 2. DeepSeek R1 (Secondary — deep reasoning)
    logger.warning("Groq/Llama unavailable, falling back to DeepSeek...")
    response = call_deepseek(prompt)
    if response:
        return clean_thought_process(response)
    
    # 3. Gemini 2.0 Flash (Tertiary — free fallback)
    if os.getenv("GEMINI_API_KEY"):
        logger.warning("DeepSeek unavailable, falling back to Gemini...")
        response = call_gemini(prompt)
        if response:
            return clean_thought_process(response)
    
    logger.error(f"CRITICAL: All LLM providers (Groq, DeepSeek, Gemini) failed.")
    raise Exception("All LLM providers failed")

def extract_json(text: str) -> dict:
    """Safely extract JSON from LLM output, handling markdown and common escaping errors."""
    if not text:
        raise ValueError("Empty response from LLM")
    
    # Try regex first to find a markdown block
    import re
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        cln = match.group(1)
    else:
        # Fallback to sweeping for structural braces
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            cln = text[start_idx:end_idx+1]
        else:
            logger.error(f"No JSON object found. Raw LLM output: \n{text}\n")
            raise ValueError("No JSON object found in output")
            
    try:
        return json.loads(cln, strict=False)
    except json.JSONDecodeError as e:
        logger.error(f"JSON extraction failed. Raw LLM output: \n{text}\n")
        raise ValueError(f"Invalid JSON string format: {e}")

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
        You are a seasoned Portfolio Manager conducting a balanced assessment.
        Write a concise, 2-sentence investment thesis for {symbol} ({name}), a {sector} company in {industry}.
        
        Context: {summary}

        CRITICAL RULES:
        1. Your stance MUST reflect the actual fundamentals. Do NOT default to bullish.
        2. If the evidence suggests risks outweigh opportunities, the thesis MUST be BEARISH or NEUTRAL.
        3. The format below shows placeholders — use your own judgment for the stance word.
        
        Format: "[BULLISH/BEARISH/NEUTRAL] on {symbol} based on [primary driver or risk]. Key risk/opportunity is [specific factor]."
        Keep it under 60 words. Plain text only.
        """
        
        thesis = get_llm_response(prompt)
        return thesis.strip().replace('"', '')

    except Exception as e:
        logger.error(f"Failed to generate thesis for {symbol}: {e}")
        return f"Long {symbol} for exposure to {sector}. (Auto-generation failed, please edit)."

def generate_investment_thesis(symbol: str, user_profile: Optional[Dict] = None) -> dict:
    """
    Generates a deep-dive Investment Thesis (used by the Thesis Library).
    Outputs JSON containing stance, one_liner, key_drivers, primary_risk, confidence_score, and content.
    """
    logger.info(f"Generating full Investment Thesis for {symbol}...")
    try:
        info = finance.get_stock_info(symbol)
        name = info.get('shortName', symbol)
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')
        summary = info.get('longBusinessSummary', '')[:800] + "..."
        current_price = info.get('currentPrice', 'N/A')
        
        # Fast-Path SEC Text Context Extraction (Fallback to none if it fails or timeouts)
        sec_info_block = "No SEC Context available. Rely on general knowledge and business summary."
        db = None
        try:
            logger.info(f"Attempting to fetch SEC context for {symbol} during thesis generation...")
            db = SessionLocal()
            sec_context = get_sec_summaries(symbol, db)
            if sec_context:
                sec_info_block = f"""
                [SEC 10-K BUSINESS PROFILE]: {sec_context.get('business_description', 'N/A')}
                [SEC 10-K BASELINE RISKS]: {sec_context.get('risk_factors_10k', 'N/A')}
                [SEC 10-Q RECENT RISK UPDATES]: {sec_context.get('latest_10q_delta', 'N/A')}
                [SEC MATERIAL LAWSUITS]: {sec_context.get('legal_proceedings', 'N/A')}
                [SEC MANAGEMENT DISCUSSION (MD&A)]: {sec_context.get('mda', 'N/A')}
                """
            logger.info(f"Successfully loaded SEC context for {symbol}.")
        except Exception as e:
            logger.warning(f"Failed to load pure text SEC context during generation. Falling back to base context: {e}")
        finally:
            if db:
                db.close()
        
        # Format User Profile for LLM context
        user_context_block = ""
        if user_profile:
            goals_list = user_profile.get('goals', [])
            goals_str = "No specific goals set."
            if goals_list:
                goals_str = "\n".join([f"- {g['name']} (Target: ${g['target_amount']:,} by {g['target_date']}) - Priority: {g['priority']}" for g in goals_list])
                
            user_context_block = f"""
            [USER INVESTMENT PROFILE]
            - Risk Appetite: {user_profile.get('risk_appetite', 'Unknown')}
            - Monthly Budget: ${user_profile.get('monthly_budget', 0):,}
            - Experience: {user_profile.get('investment_experience', 'Unknown')}
            - Specific Goals:
            {goals_str}
            """
            
        # ── STEP 1: Generate Devil's Advocate Bear Case ────────────────────────────
        # Always generate the bear case first, independently, before writing the thesis.
        # This forces the main thesis to explicitly confront counter-arguments.
        
        bear_instruction = "Your ONLY job is to find the 3 strongest reasons to SHORT this stock."
        if user_profile:
            bear_instruction = "Your ONLY job is to find the 3 strongest reasons this stock could JEOPARDIZE THE USER'S SPECIFIC GOALS listed below, acting as a strict risk manager."

        bear_prompt = f"""
        You are a short-seller and forensic analyst with a strong bearish disposition.
        {bear_instruction}

        STOCK: {symbol} ({name})
        BUSINESS SUMMARY: {summary}
        SEC RISK FACTORS: {sec_info_block[:1500]}
        {user_context_block}

        Output exactly 3 concrete, specific bearish arguments as bullet points.
        Each must be grounded in the SEC data, business fundamentals, or DIRECT CONFLICT with the user's goals — NO vague generalities.
        Examples of acceptable arguments: valuation excess, deteriorating margins, competition moat erosion,
        regulatory headwinds, insider selling, debt concerns, governance issues, OR extreme volatility threatening a short-term downpayment goal.
        Format: bullet points only, no preamble.
        """
        bear_case = "No bear case available."
        try:
            raw_bear = get_llm_response(bear_prompt)
            bear_case = raw_bear.strip()
            logger.info(f"Bear case generated for {symbol}: {bear_case[:200]}")
        except Exception as bear_e:
            logger.warning(f"Bear case generation failed for {symbol}: {bear_e}")

        # ── STEP 2: Main Thesis Prompt (must rebut the bear case) ─────────────────
        prompt = f"""
        You are an elite financial advisor writing a highly personalized Investment Thesis for a specific retail client.
        Your analysis MUST be rigorously balanced. A BULLISH rating requires explicitly defeating the bear case AND aligning with the client's goals.
        
        STOCK: {symbol} ({name})
        SECTOR/INDUSTRY: {sector} / {industry}
        PRICE (approx): ${current_price}
        BUSINESS SUMMARY: {summary}
        
        {user_context_block}
        
        CORPORATE SEC RISK CONTEXT (READ THIS CAREFULLY):
        {sec_info_block}

        ── MANDATORY: DEVIL'S ADVOCATE BEAR CASE (independently generated) ──
        The following bearish arguments MUST be directly addressed in your thesis.
        If you cannot convincingly rebut them, your stance MUST be BEARISH or NEUTRAL:
        {bear_case}
        ────────────────────────────────────────────────────────────────────────
        
        STANCE SELECTION RULES (follow strictly):
        - BULLISH: Only if the bull case clearly outweighs ALL three bear arguments AND it is suitable for the User's Risk Profile/Goals.
        - BEARISH: If the bear arguments are more compelling, unresolvable, OR the stock is too risky/unsuitable for the user's specific goals.
        - NEUTRAL: If evidence is mixed or you cannot decisively favor one side.
        - Do NOT default to BULLISH out of convention. Ensure strict fiduciary alignment with the user's time horizons.
        
        TASK:
        Generate a highly professional, well-reasoned investment thesis.
        - Directly synthesize the provided SEC Risk Factors into the `primary_risk` section.
        - The `key_drivers` field MUST include both upside catalysts AND a rebuttal to the bear case.
        - Integrate the SEC Business Profile, MD&A, and Legal Proceedings into the `content` section.
        
        Your output MUST be valid JSON EXACTLY matching this schema:
        {{
            "stance": "BULLISH" | "BEARISH" | "NEUTRAL",
            "one_liner": "<A single concise sentence summarizing the core thesis>",
            "key_drivers": ["<driver 1>", "<driver 2>", "<bear rebuttal or concession>"],
            "primary_risk": "<The #1 biggest risk to this thesis based directly on the SEC Risk Factors context.>",
            "confidence_score": <float 1.0-10.0>,
            "bear_arguments_addressed": "<1-2 sentences explaining why the bear case was accepted or rejected>",
            "content": "<A comprehensive markdown-formatted deep dive explaining the thesis, market positioning, moat, and triggers. Synthesize MD&A, bear case rebuttal, and business profile here. Use headings and bullet points.>"
        }}
        
        CRITICAL JSON RULES:
        1. Escape ALL internal double quotes (\") inside strings.
        2. Escape ALL newlines (\\n) inside the markdown content string.
        3. Do NOT use literal newlines inside JSON string values.
        """
        
        raw = get_llm_response(prompt)
        data = extract_json(raw)
        
        # Ensure stance is valid
        if data.get('stance') not in ['BULLISH', 'BEARISH', 'NEUTRAL']:
            data['stance'] = 'NEUTRAL'
            
        return data
    except Exception as e:
        logger.error(f"Failed to generate investment thesis for {symbol}: {e}")
        return {
            "stance": "NEUTRAL",
            "one_liner": f"Auto-generated analysis for {symbol} failed.",
            "key_drivers": ["Data unavailable"],
            "primary_risk": "Generation timeout",
            "confidence_score": 5.0,
            "content": "The AI agent encountered an error while generating the deep-dive analysis. Please try regenerating."
        }

def distill_snippets(symbol: str, thesis: str, event: str, raw_snippets: list) -> str:
    """
    Fast LLM distillation pass: given raw web search snippets, extract only the
    2-3 most investment-relevant sentences and tag whether each supports or refutes the thesis.
    This keeps research_history clean and token-efficient.
    """
    if not raw_snippets:
        return "No relevant web results retrieved."
    
    snippets_block = "\n\n".join(
        [f"[{i+1}] {s['title']}\n{s['snippet'][:500]}" for i, s in enumerate(raw_snippets)]
    )
    
    distill_prompt = f"""
    You are a financial analyst extracting signal from raw web search results.

    STOCK: {symbol}
    ORIGINAL THESIS: "{thesis[:200]}"
    TRIGGERING EVENT: {event}

    RAW SEARCH RESULTS:
    {snippets_block}

    TASK: Extract the 2-3 most investment-relevant sentences from the above snippets.
    For each sentence, tag it as [SUPPORTS THESIS], [REFUTES THESIS], or [NEUTRAL].
    Discard any boilerplate, ads, or content unrelated to the thesis or event.
    Use this format for each bullet (plain text, no JSON):
    • [TAG] <1 specific factual sentence with all numbers and names preserved>

    Keep total output under 6 bullets. Be ruthlessly specific and factual.
    """
    try:
        return get_llm_response(distill_prompt)
    except Exception as e:
        logger.warning(f"Snippet distillation failed, using raw dump: {e}")
        return "\n".join([f"[Web] {s['title']}: {s['snippet'][:200]}" for s in raw_snippets])

def evaluate_risk_agentic(symbol: str, thesis: str, events: list, evidence: dict, scan_id: str = None) -> dict:
    """
    Agentic 3-Stage Continuous Reasoning Loop.
    1. Plan: Analyze the trigger and decide what questions to ask.
    2. Retrieve: Hit SEC Vector DB or DuckDuckGo Web Search.
    3. Reflect & Decide: Grade the thesis based on the accumulated context.
    """
    logger.info(f"Starting Agentic Risk Evaluation for {symbol}...")
    
    # Initialize the thinking log for this evaluation if scan_id provided
    if scan_id and scan_id not in active_scan_logs:
        active_scan_logs[scan_id] = []
        
    log_agent_thought("INIT", f"Starting evaluation for {symbol}. Thesis: {thesis[:100]}", scan_id=scan_id)
    
    # Initialize Tools
    web_search = WebSearchBackend()
    
    # 0. Fast-Path SEC Text Context Extraction
    sec_info_block = "No SEC Context available."
    db = None
    try:
        db = SessionLocal()
        sec_context = get_sec_summaries(symbol, db)
        if sec_context:
            sec_info_block = f"""
            [SEC 10-K BUSINESS PROFILE]: {sec_context.get('business_description', 'N/A')}
            [SEC 10-K BASELINE RISKS]: {sec_context.get('risk_factors_10k', 'N/A')}
            [SEC 10-Q RECENT RISK UPDATES]: {sec_context.get('latest_10q_delta', 'N/A')}
            [SEC MATERIAL LAWSUITS]: {sec_context.get('legal_proceedings', 'N/A')}
            [SEC MANAGEMENT DISCUSSION (MD&A)]: {sec_context.get('mda', 'N/A')}
            """
    except Exception as e:
        logger.error(f"Failed to load pure text SEC context: {e}")
    finally:
        if db:
            db.close()
    
    # Prepare the initial environment — include full quantitative context from evidence
    fund = evidence.get('fundamentals', {})
    techs = evidence.get('technicals', {})
    analyst = evidence.get('analyst_ratings', {})
    news_with_snippets = evidence.get('news', [])
    
    # Format quantitative snapshot for query anchoring
    quant_block = (
        f"Price: ${fund.get('price', 'N/A')} | "
        f"P/E: {fund.get('peRatio', 'N/A')} | "
        f"52W H/L: {fund.get('52WeekHigh', 'N/A')}/{fund.get('52WeekLow', 'N/A')} | "
        f"RSI: {techs.get('rsi', 'N/A')} | "
        f"MACD: {techs.get('macd', 'N/A')} | "
        f"Analyst rec: {analyst.get('recommendationKey', 'N/A')} "
        f"@ target ${analyst.get('targetMeanPrice', 'N/A')}"
    )
    
    # Format news with full snippets (not just titles)
    news_block = "\n".join(
        [f"  [{i+1}] {n.get('title', '')} — {n.get('summary', n.get('body', ''))[:250]}" 
         for i, n in enumerate(news_with_snippets[:4])]
    ) or "  No recent news available."
    
    trigger_context = (
        f"TRIGGERING EVENTS:\n" + "\n".join([f"  - {e}" for e in events]) +
        f"\n\nQUANTITATIVE CONTEXT:\n  {quant_block}" +
        f"\n\nRECENT NEWS (with excerpts):\n{news_block}"
    )
    
    research_history = []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: FACT COLLECTOR (Turn 0) — Neutral baseline fact-gathering
    # Runs BEFORE the BULL/BEAR debate so both sides argue over the same facts.
    # ═══════════════════════════════════════════════════════════════════════════
    log_agent_thought("RETRIEVE", "Starting FACT COLLECTOR (Turn 0) — gathering neutral baseline facts...", scan_id=scan_id)
    
    fact_dossier = "No baseline facts collected."
    try:
        # Generate neutral, objective search queries
        fact_query_prompt = f"""
        You are a neutral financial researcher. Your job is to collect OBJECTIVE FACTS only — no opinions, no bias.
        STOCK: {symbol}
        ORIGINAL THESIS: "{thesis}"
        TRIGGERING EVENTS: {trigger_context}
        
        Generate exactly 2 fact-finding search queries to establish the ground truth.
        Focus on: recent earnings/revenue numbers, regulatory actions, executive changes, 
        product launches, market share data, or material business developments.
        Do NOT search for opinions, analyst ratings, or bull/bear cases.
        
        OUTPUT JSON ONLY:
        {{
            "cot_reasoning": "<1 sentence on what baseline facts are needed>",
            "queries": ["<query 1>", "<query 2>"]
        }}
        """
        raw_fq = get_llm_response(fact_query_prompt)
        fq_data = extract_json(raw_fq)
        fact_queries = fq_data.get("queries", [])[:2]
    except Exception as e:
        logger.warning(f"Fact Collector query generation failed: {e}")
        fact_queries = [f"{symbol} latest earnings results 2026", f"{symbol} recent news developments"]
    
    # Execute fact searches
    fact_results = []
    for q in fact_queries:
        results = web_search.search(q, top_k=3)
        fact_results.extend(results)
    
    log_agent_thought("RETRIEVE", f"FACT COLLECTOR ran searches: {fact_queries}. Found {len(fact_results)} snippets.", scan_id=scan_id)
    
    if fact_results:
        # Distill into a clean, neutral fact dossier
        raw_facts = "\n\n".join(
            [f"[{i+1}] {s['title']}\n{s.get('snippet', s.get('summary', ''))[:300]}" for i, s in enumerate(fact_results)]
        )
        distill_fact_prompt = f"""
        You are a neutral fact-checker. Extract ONLY verified, objective facts from these search results.
        STOCK: {symbol}
        
        RAW SEARCH RESULTS:
        {raw_facts}
        
        TASK: Extract 4-6 key objective facts. Each must be a specific, verifiable claim with numbers/dates.
        NO opinions, NO predictions, NO analyst sentiment. Only hard facts.
        Format as bullet points:
        • <fact with specific numbers/dates>
        """
        try:
            fact_dossier = get_llm_response(distill_fact_prompt)
            research_history.append(f"--- NEUTRAL FACT DOSSIER (Turn 0) ---\nQueries: {fact_queries}\n{fact_dossier}")
            log_agent_thought("ANALYZE", f"FACT COLLECTOR dossier compiled: {fact_dossier[:200]}...", scan_id=scan_id)
        except Exception as e:
            logger.warning(f"Fact distillation failed: {e}")
            fact_dossier = raw_facts[:1000]
            research_history.append(f"--- RAW FACTS (Turn 0) ---\n{fact_dossier}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: Parallel BULL/BEAR Discovery & Brief Generation
    # Both analysts receive the shared fact dossier as common ground.
    # ═══════════════════════════════════════════════════════════════════════════
    import concurrent.futures
    
    def run_analyst(persona: str) -> dict:
        # --- MULTI-TURN SEARCH LOOP ---
        all_queries = []
        all_search_results = []
        snippets_block = "No previous search results."
        
        for turn in range(2):
            log_agent_thought("RETRIEVE", f"Starting {persona} analysis (Turn {turn+1}/2)...", scan_id=scan_id)
            
            # Step 2A: Generate Search Queries
            query_prompt = f"""
            You are the {persona} Analyst evaluating an investment thesis.
            STOCK: {symbol}
            ORIGINAL THESIS: "{thesis}"
            TRIGGERING EVENTS: {trigger_context}
            
            SHARED FACT DOSSIER (collected by neutral researcher — use these as your starting evidence):
            {fact_dossier}
            
            As the {persona}, you must find evidence specifically to {'SUPPORT' if persona == 'BULL' else 'ATTACK'} the thesis.
            You already have the shared facts above. Now search for ADDITIONAL evidence that the neutral researcher missed.
            
            PREVIOUS SEARCH RESULTS (from your earlier turns):
            {snippets_block}
            
            CONSTRAINTS: You are on Turn {turn+1} of 2.
            Based on the shared facts and your previous results (if any), output EXACTLY 2 specific, targeted web search queries to find the most high-impact, specific missing evidence immediately. Do not waste searches on generic queries or re-searching facts already in the dossier.
            
            OUTPUT JSON ONLY:
            {{
                "cot_reasoning": "<1 sentence explaining why you need to run these specific searches>",
                "queries": ["<query 1>", "<query 2>"]
            }}
            """
            try:
                raw_q = get_llm_response(query_prompt)
                q_data = extract_json(raw_q)
                queries = q_data.get("queries", [])[:2]
            except Exception as e:
                logger.warning(f"Failed to generate queries for {persona} turn {turn+1}: {e}")
                queries = [f"{symbol} {persona.lower()} case news", f"{symbol} earnings"][:2]

            all_queries.extend(queries)

            # Step 2B: Execute Search
            turn_results = []
            for q in queries:
                results = web_search.search(q, top_k=3)
                turn_results.extend(results)
                
            all_search_results.extend(turn_results)
            
            # Update snippets block for the next turn / final brief
            snippets_block = "\n".join([f"[{i+1}] {s['title']} - {s.get('snippet', s.get('summary', ''))[:200]}" for i, s in enumerate(all_search_results)])
            log_agent_thought("RETRIEVE", f"{persona} Turn {turn+1} ran searches: {queries}. Found {len(turn_results)} snippets.", scan_id=scan_id)
        
        # Step 2C: Generate Brief (After 2 turns are complete)
        brief_prompt = f"""
        You are the {persona} Analyst.
        STOCK: {symbol}
        ORIGINAL THESIS: "{thesis}"
        TRIGGERING EVENTS: {trigger_context}
        
        BASE SEC FACTS:
        {sec_info_block}
        
        SHARED FACT DOSSIER (neutral baseline — you MUST reference these facts):
        {fact_dossier}
        
        INDEPENDENT SEARCH RESULTS (Aggregated from 2 turns):
        {snippets_block}
        
        TASK:
        Write your strongest 3-bullet {'defense of' if persona == 'BULL' else 'attack on'} the thesis.
        
        CRITICAL SAFEGUARDS & CONSTRAINTS:
        1. HALLUCINATION CHECK: You MUST explicitly cite facts from the Shared Fact Dossier, SEC Facts, or your Search Results. Do NOT invent numbers, dates, or events.
        2. SHARED FACTS FIRST: At least 1 of your 3 bullets MUST reference a fact from the Shared Fact Dossier, interpreting it through your {persona} lens.
        3. FINAL ANALYSIS: You have completed your 2 search turns. This is your final and only brief. You must present your strongest argument now to convince the Judge.
        4. Even if the evidence is weak, you must present the strongest possible interpretation for your side.
        
        OUTPUT JSON ONLY:
        {{
            "cot_analysis": "<1 sentence analyzing how the search results impact your case>",
            "argument": ["<bullet 1>", "<bullet 2>", "<bullet 3>"],
            "citations_used": ["<exact title from search result or SEC section>"],
            "hallucination_safeguard_passed": true
        }}
        
        CRITICAL JSON RULES:
        1. Ensure your JSON is completely valid. There must be no other text output.
        2. Escape ALL internal double quotes (\\") inside strings.
        3. Do NOT use literal newlines inside JSON string values.
        """
        try:
            raw_b = get_llm_response(brief_prompt)
            brief_data = extract_json(raw_b)
            brief_data["queries_run"] = all_queries
            cot = brief_data.get('cot_analysis', 'No CoT provided.')
            argument_preview = " ".join(brief_data.get('argument', []))[:150]
            log_agent_thought("ANALYZE", f"{persona} completed brief after 2 turns. CoT: {cot} | Arg: {argument_preview}...", scan_id=scan_id)
            return brief_data
        except Exception as e:
            logger.error(f"{persona} brief failed: {e}")
            log_agent_thought("ERROR", f"{persona} failed to generate brief: {e}", scan_id=scan_id)
            return {"argument": [f"Failed to generate {persona} brief."], "citations_used": [], "queries_run": all_queries}

    log_agent_thought("INIT", "Dispatching parallel Bull and Bear agents (with shared fact dossier)...", scan_id=scan_id)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        bull_future = executor.submit(run_analyst, "BULL")
        bear_future = executor.submit(run_analyst, "BEAR")
        bull_result = bull_future.result()
        bear_result = bear_future.result()
        
    research_history = [
        f"--- BULL'S INDEPENDENT RESEARCH ---\nQueries: {bull_result.get('queries_run', [])}\nBrief:\n" + "\n".join(bull_result.get('argument', [])),
        f"--- BEAR'S INDEPENDENT RESEARCH ---\nQueries: {bear_result.get('queries_run', [])}\nBrief:\n" + "\n".join(bear_result.get('argument', []))
    ]
            
    # --- Final Verdict Stage ---
    logger.info("Agent Parallel Generation finished. Issuing Final Verdict.")
    
    final_history_str = "\n\n".join(research_history)
        
    verdict_prompt = f"""
    You are the Thesis Supreme Court — a skeptical, independent adjudicator.
    You will evaluate a thesis based on the conflicting arguments from a Bull and Bear analyst.

    STOCK: {symbol}
    ORIGINAL THESIS: "{thesis}"
    TRIGGERING EVENTS: {trigger_context}
    
    DEBATE BRIEFS:
    {final_history_str}

    ── RULING STANDARDS ──
    - BROKEN: The Bear's evidence directly invalidates core thesis assumptions and outweighs the Bull's defense.
    - AT_RISK: The core thesis still holds but faces a credible, material headwind exposed by the Bear.
    - INTACT: The Bull's defense successfully neutralizes the Bear's attacks using verified evidence.

    TASK:
    Based on the Bull and Bear briefs, make a final, definitive ruling.
    Find the crux of the disagreement. Who had the better facts?
    
    OUTPUT JSON ONLY:
    {{
        "thesis_status": "INTACT" | "AT_RISK" | "BROKEN",
        "confidence": <float 0.0-1.0>,
        "reasoning": "<thorough explanation analyzing the Bull vs Bear briefs, max 3 sentences>",
        "recommended_action": "HOLD" | "REDUCE" | "SELL",
        "key_evidence": ["<fact 1 from briefs>", "<fact 2 from briefs>"],
        "refuting_evidence_addressed": "<How did you resolve the conflict between the Bull and Bear? Who won the core argument and why?>"
    }}
    """
    
    try:
        raw_final = get_llm_response(verdict_prompt)
        result = extract_json(raw_final)
        
        # Default safety checks
        if result.get('thesis_status') not in ['INTACT', 'AT_RISK', 'BROKEN']:
            result['thesis_status'] = 'AT_RISK'
        
        # Evidence Grounding Guardrail
        result['key_evidence'] = ground_evidence(result.get('key_evidence', []), research_history, scan_id=scan_id)
        
        # Reasoning: keep full for email, cap for DB
        result['reasoning_full'] = result.get('reasoning', '')
        result['reasoning'] = result['reasoning_full'][:100]
        
        # Attach the full research trail + thinking log for audit
        result['research_history'] = research_history
        result['agent_thinking_log'] = active_scan_logs.get(scan_id, []) if scan_id else []
        
        log_agent_thought("VERDICT", f"Status={result['thesis_status']}, Confidence={result.get('confidence')} | Rule: {result['reasoning_full'][:200]}...", scan_id=scan_id)
        return result

    except Exception as e:
        logger.error(f"Final Verdict evaluation failed: {e}")
        log_agent_thought("ERROR", f"Final Verdict failed: {e}", scan_id=scan_id)
        return {
            "thesis_status": "AT_RISK",
            "confidence": 0.0,
            "reasoning": "Agentic analysis failed, flagging for manual review.",
            "reasoning_full": "Agentic analysis failed at the Final Verdict stage, flagging for manual review.",
            "recommended_action": "HOLD",
            "key_evidence": ["AI Error"],
            "research_history": research_history,
            "agent_thinking_log": active_scan_logs.get(scan_id, []) if scan_id else []
        }
