import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from openai import OpenAI
from groq import Groq
from pydantic import BaseModel, Field
from services.vinsight_scorer import StockData, ScoreResult, VinSightScorer
from services.grounding_validator import GroundingValidator

logger = logging.getLogger(__name__)

# Pydantic Schemas for Phase 1 Strict Grounding & Validation
class ComponentScores(BaseModel):
    valuation: int = Field(ge=0, le=10)
    growth: int = Field(ge=0, le=10)
    profitability: int = Field(ge=0, le=10)
    health: int = Field(ge=0, le=10)
    technicals: int = Field(ge=0, le=10)
    momentum: int = Field(ge=0, le=10, default=5)
    volume: int = Field(ge=0, le=10, default=5)

class SummaryDetails(BaseModel):
    verdict: str
    bull_case: str
    bear_case: str
    fundamental_analysis: str
    technical_analysis: str

class AIResponseSchema(BaseModel):
    thought_process: str
    confidence_score: int = Field(ge=0, le=100)  # Metadata only, NOT used in score
    primary_driver: str
    summary: SummaryDetails
    component_scores: ComponentScores  # UI display only, NOT used in score
    risk_factors: List[str]
    opportunities: List[str]
    contextual_adjustment: int = Field(ge=-10, le=10, default=0)
    adjustment_reasoning: str = Field(default="")


# Personas Configuration
PERSONAS = {
    "CFA": {
        "description": "Conservative, balanced institutional analyst. Prioritizes valuation, margins, and steady growth.",
        "focus": "Valuation (PEG, P/E), Profitability (ROE, Margins), Debt Safety.",
        "style": "Skeptical, risk-averse.",
        "scoring_weights": {"Valuation": 30, "Profitability": 30, "Growth": 20, "Health": 20, "Technicals": 0}
    },
    "Momentum": {
        "description": "Aggressive trader focused on price action and trends. Prioritizes RSI, Volume, and strength vs market.",
        "focus": "RSI, Moving Averages, Relative Volume, 52w High proximity.",
        "style": "Decisive, trend-following.",
        "scoring_weights": {"Technicals": 40, "Momentum": 30, "Volume": 20, "Growth": 10, "Valuation": 0}
    },
    "Income": {
        "description": "Dividend-focused investor seeking safety and yield. Prioritizes payout ratio and cash flow.",
        "focus": "Dividend Yield, Payout Ratio, Interest Coverage, Free Cash Flow.",
        "style": "Conservative, safety-first.",
        "scoring_weights": {"Health": 40, "Profitability": 30, "Valuation": 20, "Growth": 10, "Technicals": 0}
    },
    "Value": {
        "description": "Contrarian value investor (Graham/Buffett style). Seeks mispriced assets with margin of safety.",
        "focus": "Price/Book, EV/EBITDA, Low P/E, Insider Buying.",
        "style": "Contrarian, patient.",
        "scoring_weights": {"Valuation": 50, "Health": 20, "Profitability": 20, "Growth": 10, "Technicals": 0}
    },
    "Growth": {
        "description": "Growth-at-any-price investor. Prioritizes revenue acceleration and market size.",
        "focus": "Revenue Growth, Earnings Growth, Future Projections (P90).",
        "style": "Optimistic, future-focused.",
        "scoring_weights": {"Growth": 50, "Technicals": 20, "Profitability": 20, "Valuation": 10, "Health": 0}
    }
}

class ReasoningScorer:
    """
    AI-Powered Scorer with multi-provider support.
    Fallback chain: OpenRouter → Groq → DeepSeek → Gemini → Formula.
    """
    
    def __init__(self):
        # 1. OpenRouter Setup (Primary — Perplexity Sonar Reasoning Pro)
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if self.openrouter_api_key:
            self.openrouter = OpenAI(
                api_key=self.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=30.0,
                max_retries=0  # FAIL FAST -> Fallback to next provider
            )
        else:
            self.openrouter = None
        logger.info(f"OpenRouter configured: {self.openrouter is not None}")

        # 2. DeepSeek Setup
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if self.deepseek_api_key:
            self.deepseek = OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com",
                timeout=30.0,
                max_retries=0
            )
        else:
            self.deepseek = None
        logger.info(f"DeepSeek configured: {self.deepseek is not None}")

        # 3. Groq Setup (Fast)
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        # Groq client also uses httpx, so max_retries=0 works
        self.groq = Groq(
            api_key=self.groq_api_key, 
            timeout=15.0,
            max_retries=0
        ) if self.groq_api_key else None
        logger.info(f"Groq configured: {self.groq is not None}")
        
        # 4. Gemini Setup (Last Resort — Free)
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('models/gemini-2.0-flash', generation_config={"response_mime_type": "application/json"})
        else:
            self.gemini_model = None
        logger.info(f"Gemini configured: {self.gemini_model is not None}")


        # 5. Provider Config — Priority: groq > openrouter > deepseek > gemini
        if self.groq: default_provider = "groq"
        elif self.openrouter: default_provider = "openrouter"
        elif self.deepseek: default_provider = "deepseek"
        else: default_provider = "gemini"
        # self.provider = os.getenv("AI_PROVIDER", default_provider).lower()
        self.provider = default_provider # FORCE DEFAULT LOGIC (User Request: Llama 3.3) 
        
        self.fallback_scorer = VinSightScorer() # The v9.0 Math Engine
        self.grounding_validator = GroundingValidator(tolerance_pct=0.05) # Phase 2 Validator

    def _get_benchmarks(self, sector: str) -> Dict:
        return self.fallback_scorer._get_benchmarks(sector)

    def evaluate(self, stock: StockData, persona: str = "CFA", earnings_analysis: Optional[Dict] = None) -> Dict:
        """
        Main entry point for generating a hybrid score.
        """
        logger.info(f"Reasoning Scorer: Evaluating {stock.ticker} as {persona} via {self.provider}")

        # 1. Resolve provider availability
        provider = self.provider
        available = {
            "openrouter": self.openrouter is not None,
            "deepseek": self.deepseek is not None,
            "groq": self.groq is not None,
            "gemini": self.gemini_model is not None
        }
        if not available.get(provider, False):
            # Find first available provider (Priority: Groq -> OpenRouter -> DeepSeek -> Gemini)
            provider = next((p for p in ["groq", "openrouter", "deepseek", "gemini"] if available.get(p)), None)
        if not provider:
            return self._fallback_to_formula(stock)

        # 2. Run Algo Scorer First (The Objective Baseline)
        try:
            algo_result = self.fallback_scorer.evaluate(stock)
        except Exception as e:
            logger.error(f"Algo Scorer Pre-calculation failed: {e}")
            return self._fallback_to_formula(stock)

        # 3. Prepare AI Context
        try:
            # We now inject the partitioned news data (if available) into the context builder
            # to feed the dual-period Intelligence Agent 
            news_data = stock.sentiment.news_data if hasattr(stock.sentiment, 'news_data') else {}
            
            # Phase 3 Agent Collaboration: Fetch Guardian Thesis Status
            from services.guardian_client import get_guardian_status
            guardian_status = get_guardian_status(stock.ticker)
            
            # Phase 4 Scoring Memory: Fetch last 3 scores to track trajectory
            from services.score_memory import get_history
            score_history = get_history(stock.ticker, limit=3)
            
            context = self._build_context(stock, persona, earnings_analysis, news_data, algo_result, guardian_status, score_history)
        except Exception as e:
            logger.error(f"Context build failed: {e}")
            return self._fallback_to_formula(stock)

        # 4. Dispatch to LLM with multi-provider fallback chain
        response = None
        source_label = "Unknown"
        
        # All providers with their call functions and labels
        all_providers = [
            ("openrouter", self._call_openrouter, "DeepSeek R1 (OpenRouter)"),
            ("groq", self._call_groq, "Llama 3.3 70B (Groq)"),
            ("deepseek", self._call_deepseek, "DeepSeek R1"),
            ("gemini", self._call_gemini, "Gemini 2.0 Flash"),
        ]
        
        # Build chain: preferred provider first, then the rest in order
        chain = [p for p in all_providers if p[0] == provider]
        chain += [p for p in all_providers if p[0] != provider]

        for prov_name, call_fn, label in chain:
            if not available.get(prov_name): continue
            try:
                response = call_fn(context)
                source_label = label if prov_name == provider else f"{label} (Fallback)"
                logger.info(f"AI call successful via {source_label}")
                break
            except Exception as e:
                logger.warning(f"{label} failed: {e}. Trying next provider...")
                continue

        if response is None:
            logger.error("All AI providers failed. Falling back to formula.")
            return self._fallback_to_formula(stock)

        # 5. Parse and Merge
        try:
            return self._parse_response(response, stock, persona, source_label, algo_result)
        except Exception as e:
            logger.error(f"Response parsing failed: {e}", exc_info=True)
            return self._fallback_to_formula(stock)

    def _build_context(self, stock: StockData, persona: str, earnings_analysis: Optional[Dict], news_data: Optional[Dict] = None, algo_result = None, guardian_status: str = "INTACT", score_history: list = None) -> Dict:
        """Construct the data payload for the AI."""
        benchmarks = self._get_benchmarks(stock.fundamentals.sector_name)
        persona_cfg = PERSONAS.get(persona, PERSONAS["CFA"])
        
        metrics = {
            "Valuation": {
                "P/E": stock.fundamentals.pe_ratio,
                "Forward P/E": stock.fundamentals.forward_pe,
                "PEG": stock.fundamentals.peg_ratio,
                "P/B": getattr(stock.fundamentals, 'price_to_book', "N/A"),
                "EV/EBITDA": getattr(stock.fundamentals, 'ev_to_ebitda', "N/A"),
                "Payout Ratio": getattr(stock.fundamentals, 'payout_ratio', "N/A"),
                "Dividend Yield": f"{stock.dividend_yield:.2f}%" if stock.dividend_yield else "N/A"
            },
            "Profitability": {
                "ROE": f"{stock.fundamentals.roe:.1%}",
                "Net Margin": f"{stock.fundamentals.profit_margin:.1%}",
                "Operating Margin": f"{stock.fundamentals.operating_margin:.1%}",
                "FCF Yield": f"{stock.fundamentals.fcf_yield:.1%}" if stock.fundamentals.fcf_yield else "N/A"
            },
            "Health": {
                "Debt/Equity": stock.fundamentals.debt_to_equity,
                "Interest Coverage": stock.fundamentals.interest_coverage,
                "Current Ratio": stock.fundamentals.current_ratio,
                "Altman Z-Score": getattr(stock.fundamentals, 'altman_z_score', "N/A")
            },
            "Growth": {
                "Revenue Growth (3y)": f"{stock.fundamentals.revenue_growth_3y:.1%}" if stock.fundamentals.revenue_growth_3y else "N/A",
                "Earnings Growth (QoQ)": f"{stock.fundamentals.earnings_growth_qoq:.1%}"
            },
            "Technicals": {
                "Price": stock.technicals.price,
                "vs SMA200": f"{(stock.technicals.price / stock.technicals.sma200 - 1):.1%}" if stock.technicals.sma200 else "N/A",
                "RSI": stock.technicals.rsi,
                "Relative Vol": stock.technicals.relative_volume,
                "Momentum": stock.technicals.momentum_label
            },
            "Conviction Signals": {
                "Short Ratio": getattr(stock.fundamentals, 'short_ratio', "N/A"),
                "Insider Ownership": f"{stock.fundamentals.held_percent_insiders:.1%}" if stock.fundamentals.held_percent_insiders else "N/A"
            }
        }
        
        # Price context for valuation judgment
        # Phase 3: Injecting the baseline algo score into the price context
        algo_score_str = f"{algo_result.total_score}/100" if algo_result else "N/A"
        
        price_context = {
            "Current Price": f"${stock.technicals.price:.2f}",
            "52W Change": f"{stock.fundamentals.fifty_two_week_change:.1%}" if stock.fundamentals.fifty_two_week_change else "N/A",
            "vs SMA50": f"{(stock.technicals.price / stock.technicals.sma50 - 1):.1%}" if stock.technicals.sma50 else "N/A",
            "vs SMA200": f"{(stock.technicals.price / stock.technicals.sma200 - 1):.1%}" if stock.technicals.sma200 else "N/A",
            "Monte Carlo P50 Target": f"${stock.projections.monte_carlo_p50:.2f}",
            "Monte Carlo Upside (P90)": f"${stock.projections.monte_carlo_p90:.2f}",
            "Monte Carlo Downside (P10)": f"${stock.projections.monte_carlo_p10:.2f}",
            "Beta": f"{stock.beta:.2f}",
            "Offline Algo Baseline Score": algo_score_str
        }

        earnings_context = "Not Available (Cache Miss)"
        if earnings_analysis:
            verdict = earnings_analysis.get('summary', {}).get('verdict', {})
            earnings_context = f"Analyst Verdict: {verdict.get('rating')}. Reasoning: {verdict.get('reasoning')}"
        
        # Intelligence Agent (Phase 0): Run dual-period sentiment analysis on Finnhub news
        intelligence_report = "News analysis unavailable."
        try:
            if news_data and (news_data.get('latest') or news_data.get('historical')):
                from services.groq_sentiment import get_groq_analyzer
                groq_agent = get_groq_analyzer()
                latest = news_data.get('latest', [])
                historical = news_data.get('historical', [])
                
                # Fetch distilled dual-period analysis
                ai_sentiment = groq_agent.analyze_dual_period(latest, historical, context=stock.ticker)
                
                reasoning = ai_sentiment.get('reasoning', '')
                drivers = ai_sentiment.get('key_drivers', [])
                
                intelligence_report = f"Distilled Insight: {reasoning}"
                if drivers:
                    intelligence_report += f"\nKey Drivers: {', '.join(drivers)}"
            else:
                # Fallback to the legacy sentiment label if no partitioned data was passed
                intelligence_report = f"Legacy Sentiment: {stock.sentiment.news_sentiment_label} (Score: {stock.sentiment.news_sentiment_score:.2f})"
        except Exception as e:
            logger.error(f"Intelligence Agent failed during context build: {e}")
        
        # News sentiment context
        sentiment_context = {
            "Intelligence Report": intelligence_report,
            "Article Count": stock.sentiment.news_article_count
        }

        market_regime = {
            "Bull Market": stock.market_bull_regime
        }

        # v11.1: Inject Python-computed component scores for LLM transparency
        components = self.fallback_scorer._compute_components(stock)
        persona_base = self.fallback_scorer._apply_persona_weights(components, persona)
        penalties_total, penalties_log = self.fallback_scorer._compute_penalties(stock, persona)
        python_components = {
            "components": components,
            "persona": persona,
            "base_score": persona_base,
            "penalties": penalties_total,
            "penalty_details": [p["detail"] for p in penalties_log],
            "penalized_score": round(max(0, persona_base - penalties_total), 1)
        }

        return {
            "ticker": stock.ticker,
            "sector": stock.fundamentals.sector_name,
            "benchmarks": benchmarks,
            "metrics": metrics,
            "price_context": price_context,
            "sentiment_context": sentiment_context,
            "persona": persona_cfg,
            "earnings_context": earnings_context,
            "market_regime": market_regime,
            "guardian_status": guardian_status,
            "score_history": score_history or [],
            "python_components": python_components  # NEW: v11.1
        }

    def _build_system_prompt(self, context: Dict) -> str:
        weights = context['persona'].get('scoring_weights', {})
        weight_str = "\n".join([f"- {k}: {v}%" for k, v in weights.items()])
        persona_style = context['persona']['style']
        
        # Persona-Specific Sensitivity Logic
        sensitivity_rule = ""
        p_name = context['persona'].get('description', 'Standard')
        if "Conservative" in p_name: # CFA / Income
             sensitivity_rule = "SENSITIVITY: Penalize P/E > sector median by 1.5x. Reward FCF Yield > 5%. Punish dividend cuts severely."
        elif "Aggressive" in p_name: # Momentum
             sensitivity_rule = "SENSITIVITY: Ignore P/E and P/B. Score is 90% Price Action/Volume. If Price < SMA200, Score MUST be < 50."
        elif "Value" in p_name:
             sensitivity_rule = "SENSITIVITY: Reward Low P/B and Insider Buying. Penalize any stock at 52w High. Contrarian bias."
        elif "Growth" in p_name:
             sensitivity_rule = "SENSITIVITY: Forgive negative margins if Revenue Growth > 30%. Penalize growth deceleration heavily."

        # Phase 3 Agent Collaboration
        guardian_status = context.get('guardian_status', 'INTACT')
        guardian_directive = ""
        if guardian_status == "BROKEN":
            guardian_directive = "\n🚨 GUARDIAN ALERT: The quantitative Guardian Agent has marked the thesis for this stock as BROKEN. You MUST acknowledge this risk in your bear case and ensure your final score reflects a broken thesis penalty."

        # Phase 4 Scoring Memory: Format history string
        history = context.get('score_history', [])
        history_str = "No historical AI scores on record."
        if history:
            history_lines = [f"- {h['date']}: {h['score']}/100 ({h['rating']}) at ${h['price']:.2f}" for h in history]
            history_str = "\n".join(history_lines)
        # Pre-extract for f-string safety ({{}} is a set literal inside f-string expressions)
        python_components_json = json.dumps(context.get('python_components', {}), indent=2)
        market_regime_json = json.dumps(context.get('market_regime', {}), indent=2)

        return f"""
You are a expert financial mentor for a Retail Investor.
Your name is VinSight AI. Analyze {context['ticker']} ({context['sector']}).

YOUR ROLE (v11.1):
The Python scoring engine has ALREADY computed the score using quantitative data.
Your job is to provide the NARRATIVE ANALYSIS (bull/bear case, verdict) and, if qualitative
factors justify it, a bounded contextual adjustment (±10 points max).

YOUR AUDIENCE:
- Smart retail investors who want to understand *WHY* a stock is good or bad.
- Avoid jargon. Explain implications (e.g., "High debt means rising rates hurt profits").

STYLE: {persona_style}
FOCUS: {context['persona']['focus']}
{sensitivity_rule}{guardian_directive}

PYTHON ENGINE RESULTS:
{python_components_json}

Persona: {p_name} (Weights: {weight_str})

BENCHMARK CONTEXT ({context['sector']}):
- Median P/E: {context['benchmarks'].get('pe_median', 'N/A')}
- Fair PEG: {context['benchmarks'].get('peg_fair', 'N/A')}
- Healthy Margin: {context['benchmarks'].get('margin_healthy', 'N/A')}

PRICE CONTEXT:
{json.dumps(context['price_context'], indent=2)}

FUNDAMENTAL & TECHNICAL DATA:
{json.dumps(context['metrics'], indent=2)}

NEWS INTELLIGENCE REPORT:
{json.dumps(context['sentiment_context'], indent=2)}

HISTORICAL SCORING TRAJECTORY:
{history_str}
*INSTRUCTION:* If the score is degrading/improving over time, explain *why* in your narrative.

MARKET REGIME:
{market_regime_json}

QUALITATIVE CONTEXT:
- Earnings Call Analysis: {context['earnings_context']}

INSTRUCTIONS:
1. **Thought Process**: Write a 300-400 word analysis using paragraphs.
2. **Retail Reality**: Answer "Can I sleep well owning this?"
3. **Forward Looking**: Focus on what's next (Guidance, Catalysts).
4. **Contextual Adjustment**: If earnings quality, competitive dynamics, management guidance,
   or news catalysts justify adjusting the Python score, specify contextual_adjustment (-10 to +10)
   with detailed reasoning. Only adjust if qualitative signals warrant it. Most stocks need 0.

OUTPUT FORMAT:
You MUST respond with a single valid JSON object. No other text.
{{
  "thought_process": "<string: Detailed reasoning, 300-400 words. Use paragraphs.>",
  "confidence_score": <int 0-100>,
  "primary_driver": "<string: The ONE reason to Buy or Sell>",
  "summary": {{
    "verdict": "<string: Clear, 1-sentence action (e.g., 'Buy on dips due to strong AI demand').>",
    "bull_case": "<string: Detailed paragraph (100-150 words).>",
    "bear_case": "<string: Detailed paragraph (100-150 words).>",
    "fundamental_analysis": "<string: Explain the Python engine's fundamental scores.>",
    "technical_analysis": "<string: Explain the Python engine's technical scores.>"
  }},
  "component_scores": {{
    "valuation": <int 0-10>,
    "growth": <int 0-10>,
    "profitability": <int 0-10>,
    "health": <int 0-10>,
    "technicals": <int 0-10>,
    "momentum": <int 0-10>,
    "volume": <int 0-10>
  }},
  "risk_factors": ["<string>", "<string>"],
  "opportunities": ["<string>", "<string>"],
  "contextual_adjustment": <int -10 to +10, default 0>,
  "adjustment_reasoning": "<string: Why you adjusted. Empty if adjustment is 0.>"
}}
"""

    def _call_openrouter(self, context: Dict) -> Dict:
        """Call OpenRouter API (DeepSeek R1 via OpenRouter). OpenAI-compatible."""
        system_prompt = self._build_system_prompt(context)
        completion = self.openrouter.chat.completions.create(
            model="deepseek/deepseek-r1",
            messages=[
                {"role": "system", "content": "You are a financial analyst. Output valid JSON only."},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.1,  # Lowered for consistency
            max_tokens=2000,
            timeout=25.0,
            extra_headers={
                "HTTP-Referer": "https://vinsight.app",
                "X-Title": "VinSight AI Scorer"
            }
        )
        raw_text = completion.choices[0].message.content
        
        # Strip any <think> reasoning tags (common in reasoning models)
        cleaned = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
        
        # Handle markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        return json.loads(cleaned)

    def _call_gemini(self, context: Dict) -> Dict:
        prompt = self._build_system_prompt(context)
        # Use request_options to set strict execution timeout (Resilience pattern)
        response = self.gemini_model.generate_content(
            prompt, 
            generation_config={"temperature": 0.1}, # Lowered for consistency
            request_options={'timeout': 12}
        )
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        return json.loads(text)

    def _call_deepseek(self, context: Dict) -> Dict:
        """Call DeepSeek R1 API (OpenAI-compatible). Handles <think> tag stripping."""
        system_prompt = self._build_system_prompt(context)
        completion = self.deepseek.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": "You are a financial analyst. Output valid JSON only after your reasoning."},
                {"role": "user", "content": system_prompt}
            ],
            max_tokens=2000,
            temperature=0.0, # DeepSeek supports 0.0 for deterministic output
            timeout=30.0  # R1 is slower but deeper
        )
        raw_text = completion.choices[0].message.content
        
        # DeepSeek R1 outputs <think>...</think> reasoning before the JSON
        # Strip the think tags and extract only the JSON
        cleaned = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
        
        # Handle markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        return json.loads(cleaned)

    def _call_groq(self, context: Dict) -> Dict:
        system_prompt = self._build_system_prompt(context)
        completion = self.groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a financial analyst. Output valid JSON only."},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.1, # Lowered for consistency
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)

    def _parse_response(self, llm_response: Dict, stock: StockData, persona: str, source_label: str, algo_result: Any) -> Dict:
        """v11.1: Python computes score. LLM provides narrative + bounded ±10 adjustment."""
        
        # 1. Pydantic Validation
        parsed_data = AIResponseSchema.model_validate(llm_response)
        
        # 2. PYTHON-COMPUTED BASE SCORE (v11.1 — score authority is Python, not LLM)
        components = self.fallback_scorer._compute_components(stock)
        base_score = self.fallback_scorer._apply_persona_weights(components, persona)
        
        # 3. CONTINUOUS PENALTIES (proportional, persona-weighted)
        deductions, penalty_logs = self.fallback_scorer._compute_penalties(stock, persona)
        penalized_score = max(0, base_score - deductions)
        
        # Format penalty logs for backward compatibility
        kill_switch_logs = [p["detail"] for p in penalty_logs]
        
        # 4. LLM CONTEXTUAL ADJUSTMENT (±10, needs reasoning)
        adjustment = parsed_data.contextual_adjustment
        adjustment_reasoning = parsed_data.adjustment_reasoning
        if adjustment_reasoning and len(adjustment_reasoning) > 20:
            final_score = round(max(0, min(100, penalized_score + adjustment)))
        else:
            final_score = round(penalized_score)
            adjustment = 0  # No reasoning = no adjustment
        
        # REMOVED: confidence discount (was cosmetic 0.8-1.0 multiplier)
        # REMOVED: binary kill switches (replaced by continuous penalties above)
        # REMOVED: LLM component scores determining the score
        
        # 5. GUARDIAN TRIGGER — flag if score changed materially
        guardian_trigger = False
        # (will be populated when score_history is available in calling context)
        
        # 6. Grounding Verification (unchanged)
        hallucination_count = 0
        raw_metrics = algo_result.details
        
        risk_factors = parsed_data.risk_factors + kill_switch_logs
        
        for field in [parsed_data.summary.bull_case, parsed_data.summary.bear_case, 
                      parsed_data.summary.fundamental_analysis, parsed_data.summary.technical_analysis]:
            context_dict = {
                "metrics": [d.get("value") for d in raw_metrics] if algo_result else [],
                "fundamentals": stock.fundamentals.__dict__,
                "technicals": stock.technicals.__dict__,
                "projections": stock.projections.__dict__,
                "sentiment": stock.sentiment.__dict__,
                "python_components": components,  # Includes the 0-10 category scores
                "penalty_logs": kill_switch_logs  # Includes the specific formatting like -6.4%
            }
            hallucination_count += self.grounding_validator.check_hallucinations(field, context_dict)
        
        # 7. Structured Summary
        structured_summary = {
            "verdict": parsed_data.summary.verdict,
            "bull_case": parsed_data.summary.bull_case,
            "bear_case": parsed_data.summary.bear_case,
            "fundamental_analysis": parsed_data.summary.fundamental_analysis,
            "technical_analysis": parsed_data.summary.technical_analysis
        }
        
        structured_summary["verdict"] = f"Rated {final_score}/100. {structured_summary['verdict']}"
        
        if hallucination_count > 2:
            logger.warning(f"Grounding Failure: Detected {hallucination_count} hallucinated numbers.")
            structured_summary["bull_case"] = "AI narrative suppressed due to data grounding mismatch."
            structured_summary["bear_case"] = "Please refer to the raw mathematical scoring breakdowns."
            structured_summary["fundamental_analysis"] = ""
            structured_summary["technical_analysis"] = ""
        
        summary_text = f"VERDICT: {structured_summary['verdict']}\n\nBULL: {structured_summary['bull_case']}\n\nBEAR: {structured_summary['bear_case']}"

        rating = self._score_to_rating(final_score)
        
        # 8. Build response with backward-compatible shape
        # raw_breakdown: Use Python components (0-10 scale × 10 for display)
        quality_score = ((components.get('valuation', 5) + components.get('profitability', 5) + components.get('health', 5) + components.get('growth', 5)) / 4) * 10
        timing_score = components.get('technicals', 5) * 10

        meta = {
            "source": f"AI Model: {source_label}",
            "persona": persona,
            "timestamp_pst": datetime.now().strftime("%Y-%m-%d %H:%M:%S PST"),
            "primary_driver": parsed_data.primary_driver,
            "thought_process": parsed_data.thought_process,
            "engine_version": "v11.1"
        }

        algo_breakdown = algo_result.breakdown
        details = algo_result.details

        return {
            "score": final_score,
            "rating": rating, 
            "color": self._get_color(rating), 
            "justification": summary_text,
            "structured_summary": structured_summary,
            "raw_breakdown": {
                "Quality Score": round(quality_score, 1),
                "Timing Score": round(timing_score, 1)
            },
            "algo_breakdown": algo_breakdown,
            "component_scores": components,  # NEW: 5 Python-computed scores (0-10)
            "score_explanation": { 
                "factors": risk_factors,
                "opportunities": parsed_data.opportunities
            },
            "contextual_adjustment": adjustment,  # NEW
            "adjustment_reasoning": adjustment_reasoning,  # NEW
            "penalty_details": penalty_logs,  # NEW: structured penalty info
            "guardian_trigger": guardian_trigger,  # NEW
            "meta": meta,
            "details": details 
        }

    def _score_to_rating(self, score: int) -> str:
        # Adjusted v10.0 Tiers (Deciles)
        if score >= 90: return "Generational Buy"
        if score >= 85: return "High Conviction"
        if score >= 80: return "Strong Buy"
        if score >= 75: return "Buy"
        if score >= 70: return "Watchlist Buy"
        if score >= 60: return "Speculative Hold"
        if score >= 50: return "Weak Hold"
        if score >= 40: return "Underperform"
        if score >= 20: return "Hard Sell"
        return "Critical Risk"

    def _get_color(self, rating: str) -> str:
        if "Buy" in rating or "High" in rating or "Generational" in rating: return "green"
        if "Sell" in rating or "Risk" in rating or "Underperform" in rating: return "red"
        return "yellow"

    def _fallback_to_formula(self, stock: StockData) -> Dict:
        """Execute the old formula scorer if AI fails or keys are missing."""
        result = self.fallback_scorer.evaluate(stock)
        meta = {
            "source": "Formula Fallback (AI OFFLINE)",
            "timestamp_pst": datetime.now().strftime("%Y-%m-%d %H:%M:%S PST")
        }
        return {
            "score": result.total_score,
            "rating": result.rating,
            "justification": result.verdict_narrative,
            "raw_breakdown": result.breakdown,
            "algo_breakdown": result.breakdown,
            "meta": meta,
            "details": result.details,
            "score_explanation": {
                 "factors": [],
                 "opportunities": []
            }
        }

def clean_thought_process(text: str) -> str:
    """Helper to remove <think>...</think> tags from LLM responses."""
    if not text:
        return ""
    # Remove thought process tags
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    return cleaned