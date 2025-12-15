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
