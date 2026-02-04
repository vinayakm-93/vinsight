import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from groq import Groq
from services.vinsight_scorer import StockData, ScoreResult, VinSightScorer

logger = logging.getLogger(__name__)

# Personas Configuration
PERSONAS = {
    "CFA": {
        "description": "Conservative, balanced institutional analyst. Prioritizes valuation, margins, and steady growth.",
        "focus": "Valuation (PEG, P/E), Profitability (ROE, Margins), Debt Safety.",
        "style": "Skeptical, risk-averse."
    },
    "Momentum": {
        "description": "Aggressive trader focused on price action and trends. Prioritizes RSI, Volume, and strength vs market.",
        "focus": "RSI, Moving Averages, Relative Volume, 52w High proximity.",
        "style": "Decisive, trend-following."
    },
    "Income": {
        "description": "Dividend-focused investor seeking safety and yield. Prioritizes payout ratio and cash flow.",
        "focus": "Dividend Yield, Payout Ratio, Interest Coverage, Free Cash Flow.",
        "style": "Conservative, safety-first."
    },
    "Value": {
        "description": "Contrarian value investor (Graham/Buffett style). Seeks mispriced assets with margin of safety.",
        "focus": "Price/Book, EV/EBITDA, Low P/E, Insider Buying.",
        "style": "Contrarian, patient."
    },
    "Growth": {
        "description": "Growth-at-any-price investor. Prioritizes revenue acceleration and market size.",
        "focus": "Revenue Growth, Earnings Growth, Future Projections (P90).",
        "style": "Optimistic, future-focused."
    }
}

class ReasoningScorer:
    """
    AI-Powered Scorer using Groq Llama 3.3 or Gemini 1.5 Flash.
    Decouples qualitative reasoning from algorithmic ground truth.
    """
    
    def __init__(self):
        # 1. Groq Setup
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq = Groq(api_key=self.groq_api_key) if self.groq_api_key else None
        logger.info(f"Groq configured: {self.groq is not None}")
        
        # 2. Gemini Setup
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            # Use gemini-2.0-flash for speed and reliability in JSON mode
            self.gemini_model = genai.GenerativeModel('models/gemini-2.0-flash', generation_config={"response_mime_type": "application/json"})
        else:
            self.gemini_model = None
        logger.info(f"Gemini configured: {self.gemini_model is not None}")

        # 3. Provider Config
        # Default to Gemini if keys are present, otherwise Groq
        default_provider = "gemini" if self.gemini_model else "groq"
        self.provider = os.getenv("AI_PROVIDER", default_provider).lower()
        
        self.fallback_scorer = VinSightScorer() # The v9.0 Math Engine

    def _get_benchmarks(self, sector: str) -> Dict:
        return self.fallback_scorer._get_benchmarks(sector)

    def evaluate(self, stock: StockData, persona: str = "CFA", earnings_analysis: Optional[Dict] = None) -> Dict:
        """
        Main entry point for generating a hybrid score.
        """
        logger.info(f"Reasoning Scorer: Evaluating {stock.ticker} as {persona} via {self.provider}")

        # 1. Validation: Verify chosen provider is available
        if self.provider == "gemini" and not self.gemini_model:
            logger.warning("Gemini requested but not configured. Checking Groq...")
            if self.groq: self.provider = "groq"
            else: return self._fallback_to_formula(stock)
            
        if self.provider == "groq" and not self.groq:
            logger.warning("Groq requested but not configured. Checking Gemini...")
            if self.gemini_model: self.provider = "gemini"
            else: return self._fallback_to_formula(stock)

        # 2. Run Algo Scorer First (The Objective Baseline)
        try:
            algo_result = self.fallback_scorer.evaluate(stock)
        except Exception as e:
            logger.error(f"Algo Scorer Pre-calculation failed: {e}")
            return self._fallback_to_formula(stock)

        # 3. Prepare AI Context
        try:
            context = self._build_context(stock, persona, earnings_analysis)
        except Exception as e:
            logger.error(f"Context build failed: {e}")
            return self._fallback_to_formula(stock)

        # 4. Dispatch to LLM
        try:
            response = None
            source_label = "Unknown"

            if self.provider == "gemini":
                try:
                    response = self._call_gemini(context)
                    source_label = "Gemini 2.0 Flash"
                except Exception as e:
                    logger.warning(f"Gemini failed: {e}. Falling back to Groq...")
                    if self.groq:
                        response = self._call_groq(context)
                        source_label = "Llama 3.3 (Groq Fallback)"
                    else: raise e
            else:
                try:
                    response = self._call_groq(context)
                    source_label = "Llama 3.3 70B"
                except Exception as e:
                    logger.warning(f"Groq failed: {e}. Falling back to Gemini...")
                    if self.gemini_model:
                        response = self._call_gemini(context)
                        source_label = "Gemini 2.0 Flash (Fallback)"
                    else: raise e

            # 5. Parse and Merge
            return self._parse_response(response, stock, persona, source_label, algo_result)

        except Exception as e:
            logger.error(f"AI Reasoning Scorer failed completely: {e}", exc_info=True)
            return self._fallback_to_formula(stock)

    def _build_context(self, stock: StockData, persona: str, earnings_analysis: Optional[Dict]) -> Dict:
        """Construct the data payload for the AI."""
        benchmarks = self._get_benchmarks(stock.fundamentals.sector_name)
        persona_cfg = PERSONAS.get(persona, PERSONAS["CFA"])
        
        metrics = {
            "Valuation": {
                "P/E": stock.fundamentals.pe_ratio,
                "Forward P/E": stock.fundamentals.forward_pe,
                "PEG": stock.fundamentals.peg_ratio,
                "P/B": getattr(stock.fundamentals, 'price_to_book', "N/A"),
                "EV/EBITDA": getattr(stock.fundamentals, 'ev_to_ebitda', "N/A")
            },
            "Profitability": {
                "ROE": f"{stock.fundamentals.roe:.1%}",
                "Net Margin": f"{stock.fundamentals.profit_margin:.1%}",
                "Operating Margin": f"{stock.fundamentals.operating_margin:.1%}"
            },
            "Health": {
                "Debt/Equity": stock.fundamentals.debt_to_equity,
                "Interest Coverage": stock.fundamentals.interest_coverage,
                "Current Ratio": stock.fundamentals.current_ratio
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
            }
        }
        
        earnings_context = "Not Available (Cache Miss)"
        if earnings_analysis:
            verdict = earnings_analysis.get('summary', {}).get('verdict', {})
            earnings_context = f"Analyst Verdict: {verdict.get('rating')}. Reasoning: {verdict.get('reasoning')}"

        return {
            "ticker": stock.ticker,
            "sector": stock.fundamentals.sector_name,
            "benchmarks": benchmarks,
            "metrics": metrics,
            "persona": persona_cfg,
            "earnings_context": earnings_context
        }

    def _build_system_prompt(self, context: Dict) -> str:
        return f"""
You are a {context['persona']['description']}
Your name is VinSight AI. Evaluate {context['ticker']} ({context['sector']}) and assign a conviction score (0-100).

STYLE: {context['persona']['style']}
FOCUS: {context['persona']['focus']}

BENCHMARK CONTEXT ({context['sector']}):
- Median P/E: {context['benchmarks'].get('pe_median', 'N/A')}
- Fair PEG: {context['benchmarks'].get('peg_fair', 'N/A')}
- Healthy Margin: {context['benchmarks'].get('margin_healthy', 'N/A')}

DATA INPUTS:
{json.dumps(context['metrics'], indent=2)}

QUALITATIVE CONTEXT:
- Earnings Call Analysis: {context['earnings_context']}

OUTPUT FORMAT:
You MUST respond with a single valid JSON object.
{{
  "total_score": <int 0-100>,
  "summary": "<string executive summary>",
  "component_scores": {{
    "valuation": <int 0-10>,
    "growth": <int 0-10>,
    "profitability": <int 0-10>,
    "momentum": <int 0-10>,
    "trend": <int 0-10>,
    "volume": <int 0-10>
  }},
  "risk_factors": ["<string>", "<string>"],
  "opportunities": ["<string>", "<string>"]
}}
"""

    def _call_gemini(self, context: Dict) -> Dict:
        prompt = self._build_system_prompt(context)
        response = self.gemini_model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        return json.loads(text)

    def _call_groq(self, context: Dict) -> Dict:
        system_prompt = self._build_system_prompt(context)
        completion = self.groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a financial analyst. Output valid JSON only."},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)

    def _parse_response(self, llm_response: Dict, stock: StockData, persona: str, source_label: str, algo_result: Any) -> Dict:
        """Merge AI conviction with algo metrics."""
        score = llm_response.get("total_score", 50)
        summary = llm_response.get("summary") or llm_response.get("reasoning_summary")
        risks = llm_response.get("risk_factors", [])
        opps = llm_response.get("opportunities", [])
        rating = self._score_to_rating(score)
        
        comps = llm_response.get("component_scores", {})
        
        # Calculate derived aggregates from AI's 0-10 ratings
        q_val = comps.get("valuation", 5)
        q_gro = comps.get("growth", 5)
        q_pro = comps.get("profitability", 5)
        quality_score = ((q_val + q_gro + q_pro) / 3) * 10

        t_mom = comps.get("momentum", 5)
        t_tre = comps.get("trend", 5)
        t_vol = comps.get("volume", 5)
        timing_score = ((t_mom + t_tre + t_vol) / 3) * 10

        meta = {
            "source": f"AI Model: {source_label}",
            "persona": persona,
            "timestamp_pst": datetime.now().strftime("%Y-%m-%d %H:%M:%S PST")
        }

        # algo_result is the v9.0 Math Engine result
        algo_breakdown = algo_result.breakdown # {'Quality Score': X, 'Timing Score': Y}
        details = algo_result.details

        return {
            "score": score,
            "rating": rating, 
            "color": self._get_color(rating), 
            "justification": summary,
            "raw_breakdown": {
                "Quality Score": quality_score,
                "Timing Score": timing_score
            },
            "algo_breakdown": algo_breakdown,
            "score_explanation": { 
                "factors": risks,
                "opportunities": opps
            },
            "meta": meta,
            "details": details 
        }

    def _score_to_rating(self, score: int) -> str:
        if score >= 80: return "Strong Buy"
        if score >= 60: return "Buy"
        if score >= 40: return "Hold"
        if score >= 20: return "Sell"
        return "Strong Sell"

    def _get_color(self, rating: str) -> str:
        if "Buy" in rating: return "green"
        if "Sell" in rating: return "red"
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
