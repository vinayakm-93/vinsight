"""
Groq Sentiment Analyzer using Llama 3.1 70B
Uses Groq API for deep financial sentiment analysis with reasoning.
"""

import os
from groq import Groq
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


import google.generativeai as genai

class GroqSentimentAnalyzer:
    """
    Dual-Provider Sentiment Analyzer (Groq Llama 3.3 + Gemini 1.5 Flash).
    Primary: Groq (Llama 3.3 70B)
    Fallback: Gemini 2.0 Flash
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq analyzer.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
        """
        # 1. Groq Setup
        self.groq_api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            logger.warning("No Groq API key found. Groq client will not be initialized.")
            self.groq_client = None
        else:
            self.groq_client = Groq(api_key=self.groq_api_key)
        
        # Updated to latest Groq model (llama-3.1-70b-versatile was decommissioned)
        # See: https://console.groq.com/docs/models
        self.model = "llama-3.3-70b-versatile"  # Latest as of Dec 2024

        # 2. Gemini Setup
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('models/gemini-2.0-flash', generation_config={"response_mime_type": "application/json"})
                logger.info("Gemini 2.0 Flash configured for fallback.")
            except Exception as e:
                logger.error(f"Failed to configure Gemini API: {e}. Gemini fallback will not be available.")
                self.gemini_model = None
        else:
            logger.warning("No Gemini API key found. Gemini fallback will not be available.")
            self.gemini_model = None
    
    @property
    def is_available(self) -> bool:
        """Check if at least one LLM provider is available."""
        return self.groq_client is not None or self.gemini_model is not None

    def _call_groq(self, messages: list, temperature: float, max_tokens: int, response_format: Optional[Dict] = None):
        """Helper to call Groq API."""
        if not self.groq_client:
            raise ConnectionError("Groq client not initialized.")
        
        return self.groq_client.chat.completions.create(
            messages=messages,
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=5.0,
            response_format=response_format
        )

    def _call_gemini(self, system_instruction: str, user_prompt: str, temperature: float, max_tokens: int):
        """Helper to call Gemini API."""
        if not self.gemini_model:
            raise ConnectionError("Gemini model not initialized.")
        
        # Gemini 1.5 Flash with response_mime_type="application/json" handles JSON output directly.
        # System instructions are passed as part of the prompt for older Gemini versions or if not using the specific generation_config.
        # For gemini-1.5-flash with response_mime_type, the system instruction is less critical as the model is constrained to JSON.
        # However, for consistency and clarity, we can still include it in the prompt.
        
        # The user's provided `_call_gemini` was `self.gemini_model.generate_content(prompt)`.
        # I need to adapt it to take system_instruction and user_prompt.
        # For Gemini, the system instruction is often prepended to the user prompt or handled via tools/functions.
        # Given the `response_mime_type` is set in `__init__`, the model is already primed for JSON.
        # I will pass the system instruction as part of the user prompt for clarity, or just the user prompt.
        # Let's stick to the user's provided `_call_gemini` signature for now, which takes a single `prompt`.
        # The `analyze` method will construct the full prompt.
        
        # Re-evaluating the user's `_call_gemini` and `analyze` method:
        # `_call_gemini(self, prompt, max_tokens=300)`
        # `analyze` calls `_call_gemini(prompt_content)`
        # This means `prompt_content` should contain the system instruction.
        
        # The `generation_config={"response_mime_type": "application/json"}` is set in `__init__`.
        # This means Gemini will attempt to return JSON directly.
        # The `max_tokens` and `temperature` can be passed in `generate_content`.
        
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        return self.gemini_model.generate_content(user_prompt, generation_config=generation_config)

    def analyze(self, text: str, context: str = "") -> Dict:
        """
        Analyze sentiment using Groq/Llama 3.1 with Gemini fallback.
        
        Args:
            text: Text to analyze
            context: Optional context (e.g., company name, sector)
        
        Returns:
            {
                'label': 'positive' | 'negative' | 'neutral',
                'score': float (-1 to 1),
                'confidence': float (0 to 1),
                'reasoning': str (explanation of the sentiment)
            }
        """
        if not self.is_available:
            logger.error("No LLM client initialized (missing API keys for both Groq and Gemini)")
            return self._empty_result()
        
        if not text or not text.strip():
            return self._empty_result()
        
        # Build prompt with few-shot examples
        prompt_content = self._build_prompt(text, context)
        
        # Groq messages format
        groq_messages = [
            {
                "role": "system",
                "content": "You are a financial sentiment analysis expert. Analyze the sentiment of financial news and provide a JSON response."
            },
            {
                "role": "user",
                "content": prompt_content
            }
        ]
        
        response_content = None
        
        # --- FALLBACK CHAIN ---
        try:
            if self.groq_client:
                try:
                    logger.debug("Attempting sentiment analysis with Groq...")
                    completion = self._call_groq(groq_messages, temperature=0.3, max_tokens=200, response_format={"type": "json_object"})
                    response_content = completion.choices[0].message.content
                    logger.debug("Groq sentiment analysis successful.")
                except Exception as e:
                    logger.warning(f"Groq Sentiment Analysis Failed: {e}. Falling back to Gemini 2.0 Flash...")
                    if self.gemini_model:
                        try:
                            # For Gemini, the system instruction is often part of the prompt or handled by model config.
                            # Since `response_mime_type` is set, we just need the user prompt.
                            completion = self._call_gemini(
                                system_instruction="You are a financial sentiment analysis expert. Analyze the sentiment of financial news and provide a JSON response.",
                                user_prompt=prompt_content,
                                temperature=0.3,
                                max_tokens=200
                            )
                            response_content = completion.text
                            logger.debug("Gemini sentiment analysis successful.")
                        except Exception as gemini_e:
                            logger.error(f"Gemini Sentiment Failed: {gemini_e}. No fallback available.")
                            raise gemini_e # Re-raise to be caught by outer except
                    else:
                        raise e # Re-raise original Groq error if no Gemini fallback
            elif self.gemini_model:
                logger.debug("Attempting sentiment analysis with Gemini (Groq not available)...")
                completion = self._call_gemini(
                    system_instruction="You are a financial sentiment analysis expert. Analyze the sentiment of financial news and provide a JSON response.",
                    user_prompt=prompt_content,
                    temperature=0.3,
                    max_tokens=200
                )
                response_content = completion.text
                logger.debug("Gemini sentiment analysis successful.")
            else:
                 logger.error("No LLM client available for sentiment analysis.")
                 return self._empty_result()
                 
            return self._parse_response(response_content)
            
        except Exception as e:
            logger.error(f"Sentiment Analysis Failed: {e}")
            return self._empty_result()
    
    def _build_prompt(self, text: str, context: str) -> str:
        """Build few-shot prompt for sentiment analysis."""
        context_info = f" (Context: {context})" if context else ""
        
        prompt = f"""Analyze the sentiment of this financial text{context_info}:

"{text}"

Classify the sentiment as:
- positive (bullish, good news for investors)
- negative (bearish, bad news for investors)  
- neutral (mixed or unclear sentiment)

Provide your analysis in this EXACT JSON format:
{{
  "label": "positive|negative|neutral",
  "score": <number between -1.0 and 1.0>,
  "confidence": <number between 0.0 and 1.0>,
  "reasoning": "<brief explanation>"
}}

Examples:

Text: "Apple exceeds earnings expectations, beats on revenue and EPS"
{{
  "label": "positive",
  "score": 0.85,
  "confidence": 0.95,
  "reasoning": "Strong earnings beat indicates solid business performance, typically bullish for stock"
}}

Text: "Company announces layoffs affecting 15% of workforce amid revenue decline"
{{
  "label": "negative",
  "score": -0.75,
  "confidence": 0.90,
  "reasoning": "Layoffs and revenue decline are clear negative signals for the company's financial health"
}}

Text: "Merger talks ongoing, outcome uncertain"
{{
  "label": "neutral",
  "score": 0.0,
  "confidence": 0.65,
  "reasoning": "Uncertain outcome makes sentiment unclear, could go either way"
}}

Now analyze the given text and respond ONLY with the JSON, no other text:"""
        
        return prompt
    
    def analyze_batch(self, items: list[str], context: str = "") -> Dict:
        """
        Analyze multiple news items together for a holistic sentiment.
        
        Args:
            items: List of text items (headlines + summaries)
            context: Context (e.g. "Apple Inc. (AAPL)")
            
        Returns:
            Dict with label, score, confidence, reasoning
        """
        if not self.is_available:
            logger.error("No LLM client initialized for batch analysis.")
            return self._empty_result()
            
        if not items:
            return self._empty_result()
            
        # Limit to top 15 items to fit in context window and avoid noise
        items = items[:15]
        
        joined_text = "\n\n".join([f"- {item}" for item in items])
        
        prompt_content = f"""You are a cynical, sophisticated financial analyst. Analyze the sentiment of these news items for {context}:

{joined_text}

Instructions:
1. Ignore generic PR fluff (e.g. "Company announces new vice president", "Stock alerts").
2. Focus on MATERIAL impact: Earnings, Guidance, Lawsuits, Layoffs, Product Launches, Regulatory issues.
3. Be skeptical. "Restructuring" often means problems. "Strategic alternatives" means for sale.
4. "Beat earnings" is good, but check the guidance. If guidance is weak, sentiment is NEGATIVE.
5. If news is mixed, weigh the most recent and most material news heavier.
6. If the news is old or irrelevant, return NEUTRAL.

Classify sentiment as:
- positive (clear bullish signal, material good news)
- negative (clear bearish signal, material bad news, lawsuits, poor guidance)
- neutral (noise, mixed signals, or no material information)

Provide analysis in this EXACT JSON format:
{{
  "label": "positive|negative|neutral",
  "score": <float between -1.0 and 1.0 (0.0 is neutral, >0.5 is strong buy, <-0.5 is strong sell)>,
  "confidence": <float 0.0 to 1.0>,
  "reasoning": "<concise explanation of the verdict>"
}}

Respond ONLY with the JSON.
"""
        groq_messages = [
            {
                "role": "system",
                "content": "You are a senior financial analyst. You are skeptical, fact-based, and immune to corporate spin. You analyze aggregate news to determine true market sentiment."
            },
            {
                "role": "user",
                "content": prompt_content
            }
        ]

        response_content = None
        try:
            if self.groq_client:
                try:
                    logger.debug("Attempting batch analysis with Groq...")
                    completion = self._call_groq(groq_messages, temperature=0.2, max_tokens=300, response_format={"type": "json_object"})
                    response_content = completion.choices[0].message.content
                    logger.debug("Groq batch analysis successful.")
                except Exception as e:
                    logger.warning(f"Groq Batch Analysis Failed: {e}. Trying Gemini...")
                    if self.gemini_model:
                        try:
                            completion = self._call_gemini(
                                system_instruction="You are a senior financial analyst. You are skeptical, fact-based, and immune to corporate spin. You analyze aggregate news to determine true market sentiment.",
                                user_prompt=prompt_content,
                                temperature=0.2,
                                max_tokens=300
                            )
                            response_content = completion.text
                            logger.debug("Gemini batch analysis successful.")
                        except Exception as gemini_e:
                            logger.error(f"Gemini Batch Analysis Failed: {gemini_e}. No fallback available.")
                            raise gemini_e
                    else:
                        raise e
            elif self.gemini_model:
                logger.debug("Attempting batch analysis with Gemini (Groq not available)...")
                completion = self._call_gemini(
                    system_instruction="You are a senior financial analyst. You are skeptical, fact-based, and immune to corporate spin. You analyze aggregate news to determine true market sentiment.",
                    user_prompt=prompt_content,
                    temperature=0.2,
                    max_tokens=300
                )
                response_content = completion.text
                logger.debug("Gemini batch analysis successful.")
            else:
                logger.error("No LLM client available for batch analysis.")
                return self._empty_result()
            
            return self._parse_response(response_content)
            
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}")
            return self._empty_result()

    def analyze_dual_period(self, latest_items: list, historical_items: list, context: str = "") -> Dict:
        """
        Analyze 'Today' vs 'Weekly' news separately in one prompt.
        
        Args:
            latest_items: List of news items from last 24h
            historical_items: List of news items from last 7 days (excluding last 24h)
            context: Ticker/Company name
            
        Returns:
            Dict with 'score_today', 'score_weekly', 'reasoning', 'key_drivers'
        """
        if not self.is_available:
            logger.error("No LLM client initialized for dual-period analysis.")
            return self._empty_result()
            
        # Format lists
        latest_text_joined = "\n".join([f"- {item.get('title')} ({item.get('summary', '')[:600]}...)" for item in latest_items[:10]])
        if not latest_text_joined:
            latest_text_joined = "No significant news in the last 24 hours."
            
        historical_text_joined = "\n".join([f"- {item.get('title')} ({item.get('summary', '')[:600]}...)" for item in historical_items[:15]])
        if not historical_text_joined:
            historical_text_joined = "No significant news in the last week."
            
        prompt_content = f"""You are a sophisticated financial analyst. Analyze the dual-period sentiment for {context}.

PERIOD 1: LAST 24 HOURS (Immediate Pulse)
{latest_text_joined}

PERIOD 2: LAST 7 DAYS (Weekly Context)
{historical_text_joined}

Analyze the sentiment for BOTH periods separately.
- "Today's Score": Reaction to the immediate news.
- "Weekly Score": The broader trend including the context.

Instructions:
1. If "No news", semtiment is NEUTRAL (0.0).
2. Weight MATERIAL news (Earnings, Regulatory, M&A) heavily.
3. Be skeptical of PR fluff.

Provide specific "Key Drivers" (bullet points) that justify your scores.

Output EXACT JSON:
{{
  "score_today": <float -1.0 to 1.0>,
  "score_weekly": <float -1.0 to 1.0>,
  "reasoning": "<Concise explanation merging both periods>",
  "key_drivers": ["<Driver 1>", "<Driver 2>", "<Driver 3>"]
}}
"""
        groq_messages = [
            {"role": "system", "content": "You are a hedge fund signal analyst. JSON output only."},
            {"role": "user", "content": prompt_content}
        ]

        response_content = None
        source = "Unknown"
        
        try:
            if self.groq_client:
                try:
                    logger.debug("Attempting dual-period analysis with Groq...")
                    completion = self._call_groq(groq_messages, temperature=0.2, max_tokens=400, timeout=8.0, response_format={"type": "json_object"})
                    response_content = completion.choices[0].message.content
                    source = "Llama 3.3 (Reasoning)"
                    logger.debug("Groq dual-period analysis successful.")
                except Exception as e:
                    logger.warning(f"Groq Dual-Period Analysis Failed: {e}. Trying Gemini...")
                    if self.gemini_model:
                        try:
                            completion = self._call_gemini(
                                system_instruction="You are a hedge fund signal analyst. JSON output only.",
                                user_prompt=prompt_content,
                                temperature=0.2,
                                max_tokens=400
                            )
                            response_content = completion.text
                            source = "Gemini 2.0 Flash (Fallback)"
                            logger.debug("Gemini dual-period analysis successful.")
                        except Exception as gemini_e:
                            logger.error(f"Gemini Dual-Period Analysis Failed: {gemini_e}. No fallback available.")
                            raise gemini_e
                    else:
                        raise e
            elif self.gemini_model:
                logger.debug("Attempting dual-period analysis with Gemini (Groq not available)...")
                completion = self._call_gemini(
                    system_instruction="You are a hedge fund signal analyst. JSON output only.",
                    user_prompt=prompt_content,
                    temperature=0.2,
                    max_tokens=400
                )
                response_content = completion.text
                source = "Gemini 2.0 Flash"
                logger.debug("Gemini dual-period analysis successful.")
            else:
                logger.error("No LLM client available for dual-period analysis.")
                return self._empty_result()
            
            # Parse
            import json
            start = response_content.find('{')
            end = response_content.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(response_content[start:end])
                return {
                    "score_today": max(-1.0, min(1.0, float(data.get('score_today', 0)))),
                    "score_weekly": max(-1.0, min(1.0, float(data.get('score_weekly', 0)))),
                    "reasoning": data.get('reasoning', "Analysis unavailable."),
                    "key_drivers": data.get('key_drivers', []),
                    "source": source
                }
            else:
                logger.error(f"No JSON found in dual-period response: {response_content}")
                return self._empty_result()
                
        except Exception as e:
            logger.error(f"Error in dual analysis: {e}")
            return self._empty_result()
    
    def _parse_response(self, response: str) -> Dict:
        """Parse Groq/Gemini API response."""
        import json
        
        try:
            # Try to extract JSON from response
            # Sometimes the model adds extra text or markdown blocks, so we look for JSON brackets
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                
                # Validate and normalize
                label = data.get('label', 'neutral').lower()
                if label not in ['positive', 'negative', 'neutral']:
                    label = 'neutral'
                
                score = float(data.get('score', 0.0))
                score = max(-1.0, min(1.0, score))  # Clamp to [-1, 1]
                
                confidence = float(data.get('confidence', 0.0))
                confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
                
                reasoning = data.get('reasoning', '')
                
                return {
                    'label': label,
                    'score': score,
                    'confidence': confidence,
                    'reasoning': reasoning
                }
            else:
                logger.error(f"No JSON found in LLM response: {response}")
                return self._empty_result()
                
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return self._empty_result()
    
    def _empty_result(self) -> Dict:
        """Return empty/neutral result for error cases."""
        return {
            'label': 'neutral',
            'score': 0.0,
            'confidence': 0.0,
            'reasoning': 'Unable to analyze sentiment'
        }
    
    def generate_score_summary(self, ticker: str, score_data: dict) -> tuple[str, str]:
        """
        Generates a 'Senior Equity Analyst' summary using LLM with Fallback.
        Persona: cynical, sophisticated, data-driven CFA charterholder.
        Output: Structured JSON for the new UI layout.
        Returns: Tuple(summary_text, source_label)
        """
        if not self.is_available:
            return self._generate_fallback_summary(score_data), "Formula Fallback"

        source_label = "Unknown"
        
        # Unwrap data
        total = score_data.get('total_score', 0)
        rating = score_data.get('rating', 'Neutral')
        q_score = score_data.get('fundamentals_score', 0) # Mapped to Quality
        t_score = score_data.get('timing_score', 0) # Newly passed key
        modifications = score_data.get('modifications', [])
        missing_data = score_data.get('missing_data', [])
            
        # Format breakdown items for context
        breakdown_list = score_data.get('breakdown', [])
        breakdown_str = self._format_breakdown(breakdown_list)
            
        outlooks = score_data.get('outlook_context', {})
        short_term = outlooks.get('short_term', [])
        medium_term = outlooks.get('medium_term', [])
        long_term = outlooks.get('long_term', [])
            
        # Construct Prompt
        prompt_content = f"""
            Role: Senior Equity Analyst (CFA) at a top-tier hedge fund.
            Task: Write an INSTITUTIONAL RESEARCH NOTE on {ticker}.
            
            DATA:
            - Scorer Rating: {rating.upper()} (Score: {total}/100)
            - Quality Score (Fundamentals): {q_score}/100 (Weight: 70%)
            - Timing Score (Technicals): {t_score}/100 (Weight: 30%)
            
            CRITICAL ALERTS (Must Address if present):
            - Risk Factors/Vetos: {', '.join(modifications) if modifications else 'None'}
            - MISSING DATA (Score=0 for these): {', '.join(missing_data) if missing_data else 'None'}
            
            KEY FACTOR BREAKDOWN:
            {breakdown_str}
            
            CONTEXT:
            - Short-Term (Technicals): {', '.join(short_term)}
            - Medium-Term (Regime/Sector): {', '.join(medium_term)}
            - Long-Term (Valuation/Growth): {', '.join(long_term)}
            
            OUTPUT REQUIREMENTS (JSON ONLY):
            1. "executive_summary": 2 decisive sentences. State the thesis clearly. If data is missing or risks are present, Mention them as caveats.
            2. "factor_analysis": A dictionary with keys "quality" and "timing".
               - "quality": 1 sentence analyzing valuation, margins, or solvency. Mention any missing fundamental data if relevant.
               - "timing": 1 sentence analyzing trend, momentum, or volume.
            3. "risk_factors": A list of 2-3 specific risks (e.g. "Margin compression", "Data Gaps", "Sector rotation"). bullet points style strings.
            4. "outlook": A dictionary with keys "3m" (Tactical), "6m" (Catalyst), "12m" (Strategic). Max 10 words each.
            
            TONE:
            - Professional, sophisticated, decisive.
            - NO "I think" or "Basic". use terms like "multiple expansion", "margin contraction", "capitulation", "technically damaged".
            - If Critical Alerts exist, be cautious/skeptical.
            
            Respond ONLY with the RAW JSON object.
            """

        groq_messages = [
            {
                "role": "system",
                "content": "You are a Senior CFA Analyst. Output valid JSON only."
            },
            {
                "role": "user",
                "content": prompt_content
            }
        ]
        
        response_text = None

        try:
            # TRY GROQ
            if self.groq_client:
                try:
                    logger.debug("Attempting summary generation with Groq...")
                    completion = self._call_groq(groq_messages, temperature=0.3, max_tokens=600, response_format={"type": "json_object"})
                    response_text = completion.choices[0].message.content
                    source_label = "Llama 3.3 (Groq)"
                    logger.debug("Groq summary generation successful.")
                except Exception as e:
                    logger.warning(f"Groq Summary Gen Failed: {e}. Trying Gemini...")
                    if self.gemini_model:
                        try:
                            completion = self._call_gemini(
                                system_instruction="You are a Senior CFA Analyst. Output valid JSON only.",
                                user_prompt=prompt_content,
                                temperature=0.3,
                                max_tokens=600
                            )
                            response_text = completion.text
                            source_label = "Gemini 2.0 Flash (Fallback)"
                            logger.info(f"Successfully generated summary via {source_label}")
                        except Exception as gemini_e:
                            logger.error(f"Gemini Summary Gen Failed: {gemini_e}. No fallback available.")
                            raise gemini_e
                    else:
                        raise e
            
            elif self.gemini_model:
                logger.debug("Attempting summary generation with Gemini (Groq not available)...")
                completion = self._call_gemini(
                    system_instruction="You are a Senior CFA Analyst. Output valid JSON only.",
                    user_prompt=prompt_content,
                    temperature=0.3,
                    max_tokens=600
                )
                response_text = completion.text
                source_label = "Gemini 2.0 Flash"
                logger.info(f"Gemini 2.0 summary generation successful.")
            else:
                logger.error("No LLM client available for summary generation.")
                return self._generate_fallback_summary(score_data), "Formula Fallback"

            # Parse JSON
            import json
            summary_data = {}
            try:
                # Clean code blocks
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                summary_data = json.loads(response_text)
                # The user's provided code only extracted "executive_summary".
                # The original code returned the full JSON.
                # I will return the full parsed JSON object as the summary, as the original `generate_score_summary` did.
                # The user's instruction for `generate_score_summary` output requirements is a JSON, so returning the parsed JSON is correct.
                return summary_data, source_label
            except Exception as json_e:
                logger.error(f"Error parsing summary JSON from {source_label}: {json_e}. Raw response: {response_text}")
                # Fallback to returning raw text if JSON parsing fails, or a structured error.
                # The original code returned `summary = data.get("executive_summary", response_text)`.
                # Let's return a structured dict with the raw text if parsing fails.
                return {"executive_summary": response_text, "error": "JSON parsing failed"}, source_label

        except Exception as e:
            logger.error(f"Summary Gen Failed: {e}")
            return self._generate_fallback_summary(score_data), "Formula Fallback (Error)"
    
    def _format_breakdown(self, breakdown) -> str:
        """Format breakdown (dict or list) for prompt."""
        if not breakdown:
            return "No detailed breakdown available."
        
        lines = []
        if isinstance(breakdown, list):
            for item in breakdown[:15]:
                cat = item.get('category', 'Metric')
                met = item.get('metric', '')
                stat = item.get('status', '')
                lines.append(f"  - [{cat}] {met}: {stat}")
        elif isinstance(breakdown, dict):
            for category, metrics in breakdown.items():
                if isinstance(metrics, dict):
                    for metric, data in metrics.items():
                        if isinstance(data, dict):
                            status = data.get('status', 'N/A')
                            lines.append(f"  - {metric}: {status}")
        return "\n".join(lines[:10])
    
    def _generate_fallback_summary(self, score_data: dict) -> Dict:
        """Generate a fallback summary without AI."""
        total = score_data.get('total_score', 0)
        fund = score_data.get('fundamentals_score', 0)
        trend_pen = score_data.get('trend_penalty', 0)
        income = score_data.get('income_bonus', 0)
        
        parts = []
        if fund >= 80:
            parts.append(f"strong Fundamentals ({fund} pts)")
        elif fund >= 60:
            parts.append(f"solid Fundamentals ({fund} pts)")
        else:
            parts.append(f"weak Fundamentals ({fund} pts)")
        
        if trend_pen < 0:
            parts.append(f"a Trend Gate Penalty ({trend_pen})")
        if income > 0:
            parts.append(f"an Income Safety Bonus (+{income})")
        
        summary_text = ""
        if len(parts) == 1:
            summary_text = f"The score is driven by {parts[0]}."
        elif len(parts) == 2:
            summary_text = f"The score is anchored by {parts[0]}, with {parts[1]}."
        else:
            summary_text = f"The score is anchored by {parts[0]}, but affected by {parts[1]} and {parts[2]}."

        return {
            "executive_summary": summary_text,
            "factor_analysis": {
                "quality": f"Fundamentals score: {fund} pts.",
                "timing": f"Timing score: {score_data.get('timing_score', 0)} pts."
            },
            "risk_factors": ["Automated analysis unavailable"],
            "outlook": {"3m": "N/A", "6m": "N/A", "12m": "N/A"}
        }


# Singleton instance
_groq_instance = None


def get_groq_analyzer() -> GroqSentimentAnalyzer:
    """
    Get or create singleton Groq analyzer instance.
    """
    global _groq_instance
    if _groq_instance is None:
        _groq_instance = GroqSentimentAnalyzer()
    return _groq_instance


# Example usage
if __name__ == "__main__":
    # Test the analyzer
    analyzer = GroqSentimentAnalyzer()
    
    if not analyzer.is_available:
        print("ERROR: Groq API key not found. Set GROQ_API_KEY environment variable.")
        exit(1)
    
    test_cases = [
        ("Tesla reports record Q4 deliveries, beating analyst estimates by 10%", "TSLA"),
        ("Company misses earnings, lowers guidance for next quarter", ""),
        ("Merger talks continue, regulatory approval pending", "Tech sector"),
    ]
    
    print("Testing Groq Sentiment Analyzer (Llama 3.1 70B)\n")
    print("=" * 80)
    
    for text, context in test_cases:
        print(f"\nText: {text}")
        if context:
            print(f"Context: {context}")
        
        result = analyzer.analyze(text, context)
        
        print(f"Sentiment: {result['label'].upper()}")
        print(f"Score: {result['score']:.3f}")
        print(f"Confidence: {result['confidence']:.3f}")
        print(f"Reasoning: {result['reasoning']}")
        print("-" * 80)
