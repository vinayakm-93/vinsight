"""
Groq Sentiment Analyzer using Llama 3.1 70B
Uses Groq API for deep financial sentiment analysis with reasoning.
"""

import os
from groq import Groq
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class GroqSentimentAnalyzer:
    """
    Groq-based sentiment analyzer using Llama 3.1 70B.
    Provides deep analysis with reasoning for financial texts.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq analyzer.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            logger.warning("No Groq API key found. Set GROQ_API_KEY environment variable.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)
        
        # Updated to latest Groq model (llama-3.1-70b-versatile was decommissioned)
        # See: https://console.groq.com/docs/models
        self.model = "llama-3.3-70b-versatile"  # Latest as of Dec 2024
    
    def analyze(self, text: str, context: str = "") -> Dict:
        """
        Analyze sentiment using Groq/Llama 3.1.
        
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
        if not self.client:
            logger.error("Groq client not initialized (missing API key)")
            return self._empty_result()
        
        if not text or not text.strip():
            return self._empty_result()
        
        try:
            # Build prompt with few-shot examples
            prompt = self._build_prompt(text, context)
            
            # Call Groq API
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial sentiment analysis expert. Analyze the sentiment of financial news and provide a JSON response."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.3,  # Low temperature for consistent results
                max_tokens=200
            )
            
            response = chat_completion.choices[0].message.content
            
            # Parse response
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
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
        if not self.client:
            return self._empty_result()
            
        if not items:
            return self._empty_result()
            
        # Limit to top 15 items to fit in context window and avoid noise
        items = items[:15]
        
        joined_text = "\n\n".join([f"- {item}" for item in items])
        
        prompt = f"""You are a cynical, sophisticated financial analyst. Analyze the sentiment of these news items for {context}:

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
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior financial analyst. You are skeptical, fact-based, and immune to corporate spin. You analyze aggregate news to determine true market sentiment."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.2, # Lower, more deterministic
                max_tokens=300
            )
            
            # Extract JSON from response (handling potential markdown blocks)
            content = chat_completion.choices[0].message.content
            return self._parse_response(content)
            
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
        if not self.client:
            return self._empty_result()
            
        # Format lists
        latest_text = "\n".join([f"- {item.get('title')} ({item.get('summary', '')[:600]}...)" for item in latest_items[:10]])
        if not latest_text:
            latest_text = "No significant news in the last 24 hours."
            
        historical_text = "\n".join([f"- {item.get('title')} ({item.get('summary', '')[:600]}...)" for item in historical_items[:15]])
        if not historical_text:
            historical_text = "No significant news in the last week."
            
        prompt = f"""You are a sophisticated financial analyst. Analyze the dual-period sentiment for {context}.

PERIOD 1: LAST 24 HOURS (Immediate Pulse)
{latest_text}

PERIOD 2: LAST 7 DAYS (Weekly Context)
{historical_text}

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
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a hedge fund signal analyst. JSON output only."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.2, # Deterministic
                max_tokens=400
            )
            
            content = chat_completion.choices[0].message.content
            
            # Parse
            import json
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(content[start:end])
                return {
                    "score_today": max(-1.0, min(1.0, float(data.get('score_today', 0)))),
                    "score_weekly": max(-1.0, min(1.0, float(data.get('score_weekly', 0)))),
                    "reasoning": data.get('reasoning', "Analysis unavailble."),
                    "key_drivers": data.get('key_drivers', [])
                }
            else:
                return self._empty_result()
                
        except Exception as e:
            logger.error(f"Error in dual analysis: {e}")
            return self._empty_result()
    
    def _parse_response(self, response: str) -> Dict:
        """Parse Groq API response."""
        import json
        
        try:
            # Try to extract JSON from response
            # Sometimes the model adds extra text, so we look for JSON brackets
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
                logger.error(f"No JSON found in Groq response: {response}")
                return self._empty_result()
                
        except Exception as e:
            logger.error(f"Error parsing Groq response: {e}")
            return self._empty_result()
    
    def _empty_result(self) -> Dict:
        """Return empty/neutral result for error cases."""
        return {
            'label': 'neutral',
            'score': 0.0,
            'confidence': 0.0,
            'reasoning': 'Unable to analyze sentiment'
        }
    
    def is_available(self) -> bool:
        """Check if Groq API is available (API key configured)."""
        return self.client is not None

    def generate_score_summary(self, ticker: str, score_data: dict) -> str:
        """
        Generates a 'Senior Equity Analyst' summary using Llama 3.1 70B via Groq.
        Persona: cynical, sophisticated, data-driven CFA charterholder.
        Output: Structured JSON for the new UI layout.
        """
        if not self.is_available():
            return self._generate_fallback_summary(score_data)
            
        try:
            # Unwrap data
            total = score_data.get('total_score', 0)
            rating = score_data.get('rating', 'Neutral')
            q_score = score_data.get('fundamentals_score', 0) # Mapped to Quality
            t_score = score_data.get('timing_score', 0) # Newly passed key
            
            # Format breakdown items for context
            breakdown_list = score_data.get('breakdown', [])
            breakdown_str = self._format_breakdown(breakdown_list)
            
            outlooks = score_data.get('outlook_context', {})
            short_term = outlooks.get('short_term', [])
            medium_term = outlooks.get('medium_term', [])
            long_term = outlooks.get('long_term', [])
            
            # Construct Prompt
            prompt = f"""
            Role: Senior Equity Analyst (CFA) at a top-tier hedge fund.
            Task: Write an INSTITUTIONAL RESEARCH NOTE on {ticker}.
            
            DATA:
            - Scorer Rating: {rating.upper()} (Score: {total}/100)
            - Quality Score (Fundamentals): {q_score}/100 (Weight: 70%)
            - Timing Score (Technicals): {t_score}/100 (Weight: 30%)
            
            KEY FACTOR BREAKDOWN:
            {breakdown_str}
            
            CONTEXT:
            - Short-Term (Technicals): {', '.join(short_term)}
            - Medium-Term (Regime/Sector): {', '.join(medium_term)}
            - Long-Term (Valuation/Growth): {', '.join(long_term)}
            
            OUTPUT REQUIREMENTS (JSON ONLY):
            1. "executive_summary": 2 decisive sentences. State the thesis clearly. Be cynical if valuation is high. Be aggressive if widespread fear but good fundamentals.
            2. "factor_analysis": A dictionary with keys "quality" and "timing".
               - "quality": 1 sentence analyzing valuation, margins, or solvency.
               - "timing": 1 sentence analyzing trend, momentum, or volume.
            3. "risk_factors": A list of 2-3 specific risks (e.g. "Margin compression", "Overbought RSI", "Sector rotation"). bullet points style strings.
            4. "outlook": A dictionary with keys "3m" (Tactical), "6m" (Catalyst), "12m" (Strategic). Max 10 words each.
            
            TONE:
            - Professional, sophisticated, decisive.
            - NO "I think" or "Basic". use terms like "multiple expansion", "margin contraction", "capitulation", "technically damaged".
            
            Respond ONLY with the RAW JSON object.
            """

            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Senior CFA Analyst. Output valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            
            summary = chat_completion.choices[0].message.content.strip()
            summary = summary.strip('"').strip("'")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating score summary: {e}")
            return self._generate_fallback_summary(score_data)
    
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
    
    def _generate_fallback_summary(self, score_data: dict) -> str:
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
        
        if len(parts) == 1:
            return f"The score is driven by {parts[0]}."
        elif len(parts) == 2:
            return f"The score is anchored by {parts[0]}, with {parts[1]}."
        else:
            return f"The score is anchored by {parts[0]}, but affected by {parts[1]} and {parts[2]}."


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
    
    if not analyzer.is_available():
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
