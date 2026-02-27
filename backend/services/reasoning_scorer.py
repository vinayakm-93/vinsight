import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from groq import Groq
from openai import OpenAI
from services.vinsight_scorer import StockData, ScoreResult, VinSightScorer

logger = logging.getLogger(__name__)

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
            context = self._build_context(stock, persona, earnings_analysis)
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
        price_context = {
            "Current Price": f"${stock.technicals.price:.2f}",
            "52W Change": f"{stock.fundamentals.fifty_two_week_change:.1%}" if stock.fundamentals.fifty_two_week_change else "N/A",
            "vs SMA50": f"{(stock.technicals.price / stock.technicals.sma50 - 1):.1%}" if stock.technicals.sma50 else "N/A",
            "vs SMA200": f"{(stock.technicals.price / stock.technicals.sma200 - 1):.1%}" if stock.technicals.sma200 else "N/A",
            "Monte Carlo P50 Target": f"${stock.projections.monte_carlo_p50:.2f}",
            "Monte Carlo Upside (P90)": f"${stock.projections.monte_carlo_p90:.2f}",
            "Monte Carlo Downside (P10)": f"${stock.projections.monte_carlo_p10:.2f}",
            "Beta": f"{stock.beta:.2f}"
        }

        earnings_context = "Not Available (Cache Miss)"
        if earnings_analysis:
            verdict = earnings_analysis.get('summary', {}).get('verdict', {})
            earnings_context = f"Analyst Verdict: {verdict.get('rating')}. Reasoning: {verdict.get('reasoning')}"
        
        # News sentiment context
        sentiment_context = {
            "News Sentiment": stock.sentiment.news_sentiment_label,
            "Sentiment Score": f"{stock.sentiment.news_sentiment_score:.2f}",
            "Article Count": stock.sentiment.news_article_count
        }

        market_regime = {
            "Bull Market": stock.market_bull_regime
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
            "market_regime": market_regime
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

        return f"""
You are a expert financial mentor for a Retail Investor.
Your name is VinSight AI. Evaluate {context['ticker']} ({context['sector']}) and assign a conviction score (0-100).

YOUR AUDIENCE:
- Smart retail investors who want to understand *WHY* a stock is good or bad.
- Avoid excessive jargon. Explain implications (e.g., "High Debt means rising rates will hurt profits").

STYLE: {persona_style}
FOCUS: {context['persona']['focus']}
{sensitivity_rule}

SCORING RUBRIC ({p_name}):
The Final Score MUST be a weighted average based on the following priorities:
{weight_str}

SCORE CALIBRATION (10-Tier Precision Deciles):
- 0-19: ☠️ **Bankruptcy Risk**. (Solvency failure likely).
- 20-39: 🛑 **Hard Sell**. (Broken thesis / Exit now).
- 40-49: ⚠️ **Underperform**. (Deteriorating fundamentals, sell into strength).
- 50-59: 📉 **Weak Hold**. (Dead money / Value Trap).
- 60-69: 🤞 **Speculative**. (Turnaround play / 50-50 odds).
- 70-74: ✅ **Watchlist Buy**. (Good company, wait for better price).
- 75-79: 📈 **Buy**. (Solid compounder, start position).
- 80-84: 🚀 **Strong Buy**. (Beating expectations, add aggressively).
- 85-89: 💎 **High Conviction**. (Institutional quality, rare).
- 90-100: 🦄 **Generational**. (Perfect storm of Value + Growth + Momentum).

ANTI-CLUSTERING DISCIPLINE:
- Scores 80+ are RARE. Require exceptional quality AND discounted price.
- Scores below 40 are EXPECTED for companies with broken fundamentals.
- The MEDIAN stock should score 55-65. If you rate everything 65-75, you are being lazy.
- Be ruthless.

CRITICAL KILL SWITCHES (Apply these Point Deductions EXPLICITLY):
1. **Solvency Risk**: Debt/Equity > 2.0 OR Negative FCF -> **DEDUCT 20 POINTS** (Unless 'Growth' persona & Growth > 30%).
2. **Valuation Trap**: P/E > 50 AND Growth < 10% -> **DEDUCT 15 POINTS** (Unless 'Momentum' persona).
3. **Broken Trend**: Price < SMA200 -> **DEDUCT 10 POINTS** (Unless 'Value' persona).
4. **Revenue Collapse**: Revenue Growth < -10% -> **DEDUCT 15 POINTS**.
5. **Bearish News**: Sentiment is "Bearish" -> **DEDUCT 10 POINTS**.

BENCHMARK CONTEXT ({context['sector']}):
- Median P/E: {context['benchmarks'].get('pe_median', 'N/A')}
- Fair PEG: {context['benchmarks'].get('peg_fair', 'N/A')}
- Healthy Margin: {context['benchmarks'].get('margin_healthy', 'N/A')}

PRICE CONTEXT:
{json.dumps(context['price_context'], indent=2)}

FUNDAMENTAL & TECHNICAL DATA:
{json.dumps(context['metrics'], indent=2)}

NEWS SENTIMENT:
{json.dumps(context['sentiment_context'], indent=2)}

MARKET REGIME:
{json.dumps(context.get('market_regime', {}), indent=2)}

QUALITATIVE CONTEXT:
- Earnings Call Analysis: {context['earnings_context']}

INSTRUCTIONS:
1. **Chain of Thought (The "Why")**: Write a 300-400 word deep-dive using paragraphs.
2. **The "Retail Reality"**: Answer: "Can I sleep well owning this?"
3. **Forward Looking**: Focus on what's next (Guidance, Catalysts).
4. **VERDICT FORMAT**: The 'verdict' field MUST start with "Rated [Score]/100 because..." followed by the single most important reason.

COMPONENT SCORE GUIDE (0-10):
- <4: Weak / Risky.
- 5-6: Average / Fair.
- 7-8: Strong / Outperforming.
- 9-10: Best in Class.

OUTPUT FORMAT:
You MUST respond with a single valid JSON object. No other text.
{{
  "thought_process": "<string: Detailed reasoning chain, 300-400 words. Use paragraphs.>",
  "total_score": <int 0-100>,
  "confidence_score": <int 0-100>,
  "primary_driver": "<string: The ONE reason to Buy or Sell>",
  "summary": {{
    "verdict": "<string: Clear, 1-sentence action (e.g., 'Buy on dips due to strong AI demand').>",
    "bull_case": "<string: Detailed paragraph (100-150 words) focusing on upside drivers.>",
    "bear_case": "<string: Detailed paragraph (100-150 words) focusing on downside risks.>",
    "fundamental_analysis": "<string: Specific explanation of Valuation/Growth/Profitability scores (e.g., 'High P/E is justified by 40% growth').>",
    "technical_analysis": "<string: Specific explanation of Momentum/Trend/Volume (e.g., 'RSI is overbought, expect pullback').>"
  }},
  "component_scores": {{
    "valuation": <int 0-10>,
    "growth": <int 0-10>,
    "profitability": <int 0-10>,
    "momentum": <int 0-10>,
    "trend": <int 0-10>,
    "volume": <int 0-10>
  }},
  "risk_factors": ["<string: e.g. 'SOLVENCY RISK: -20 pts (Debt/Equity > 2.0)'>", "<string>"],
  "opportunities": ["<string>", "<string>"]
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
        """Merge AI conviction with algo metrics."""
        raw_score = llm_response.get("total_score", 50)
        confidence = llm_response.get("confidence_score", 70) # Default to 70 if missing
        
        # CONFIDENCE-WEIGHTED SCORING (New v10.0 Logic)
        # Apply score 'haircut' if confidence is low.
        # Discount factor: ranges from 0.8 (0% confidence) to 1.0 (100% confidence).
        # We don't want to crush the score too hard, but soft-penalize uncertainty.
        discount_factor = 0.8 + 0.2 * (confidence / 100)
        final_score = round(raw_score * discount_factor)
        
        # New Summary Structure Parsing
        summary_obj = llm_response.get("summary", {})
        structured_summary = {
            "verdict": "N/A",
            "bull_case": "N/A",
            "bear_case": "N/A",
            "fundamental_analysis": "",
            "technical_analysis": ""
        }

        if isinstance(summary_obj, str): # Handle legacy string summaries (fallback)
            structured_summary["bull_case"] = summary_obj
            summary_text = summary_obj
        else:
            # Parse new structured fields
            structured_summary["verdict"] = summary_obj.get("verdict", "No verdict provided.")
            
            # Fix dynamic score mismatch (Replace the AI's raw score with the confidence-discounted score)
            structured_summary["verdict"] = re.sub(r"Rated \d+/100", f"Rated {final_score}/100", structured_summary["verdict"])

            structured_summary["bull_case"] = summary_obj.get("bull_case", "No bull case provided.")
            structured_summary["bear_case"] = summary_obj.get("bear_case", "No bear case provided.")
            structured_summary["fundamental_analysis"] = summary_obj.get("fundamental_analysis", "")
            structured_summary["technical_analysis"] = summary_obj.get("technical_analysis", "")
            
            # Legacy fallback for justification
            summary_text = f"VERDICT: {structured_summary['verdict']}\n\nBULL: {structured_summary['bull_case']}\n\nBEAR: {structured_summary['bear_case']}"

        primary_driver = llm_response.get("primary_driver", "N/A")
        thought_process = llm_response.get("thought_process", "")
            
        risks = llm_response.get("risk_factors", [])
        opps = llm_response.get("opportunities", [])
        rating = self._score_to_rating(final_score)
        
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
            "timestamp_pst": datetime.now().strftime("%Y-%m-%d %H:%M:%S PST"),
            "confidence": confidence,
            "primary_driver": primary_driver,
            "thought_process": thought_process
        }

        # algo_result is the v9.0 Math Engine result
        algo_breakdown = algo_result.breakdown # {'Quality Score': X, 'Timing Score': Y}
        details = algo_result.details

        return {
            "score": final_score,
            "rating": rating, 
            "color": self._get_color(rating), 
            "justification": summary_text,
            "structured_summary": structured_summary, # Pass this deeply structured obj
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
        return "Bankruptcy Risk"

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