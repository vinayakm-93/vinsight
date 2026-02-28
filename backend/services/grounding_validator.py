import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class GroundingValidator:
    """
    Validates LLM-generated text against the raw mathematical context to catch numeric hallucinations.
    (Phase 2 of the Scoring Engine Redesign)
    """

    def __init__(self, tolerance_pct: float = 0.05):
        # 5% margin of error for LLM rounding (e.g., 20.4 treated as 20 or 20.5)
        self.tolerance_pct = tolerance_pct

    def _extract_numbers(self, text: str) -> List[float]:
        """Extracts all standalone numbers and percentages from text."""
        if not text:
            return []
            
        # Matches formats like: 35, 35.5, -10.2, 5,000, 35%
        # Specifically avoids capturing version numbers or dates where possible
        pattern = r'[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?'
        
        matches = re.findall(pattern, text)
        extracted = []
        for m in matches:
            # Clean up the string for float conversion
            clean_str = m.replace(',', '').replace('%', '')
            try:
                extracted.append(float(clean_str))
            except ValueError:
                continue
                
        return extracted

    def _flatten_context(self, context_metrics: Dict[str, Any]) -> List[float]:
        """Flattens the nested context metrics dictionary into a list of pure floats."""
        flat_values = []
        
        def _recurse(node):
            if isinstance(node, dict):
                for v in node.values():
                    _recurse(v)
            elif isinstance(node, list):
                for item in node:
                    _recurse(item)
            elif isinstance(node, (int, float)):
                flat_values.append(float(node))
            elif isinstance(node, str):
                # Attempt to extract floats from formatted strings like "35.5%" or "$120.50"
                clean_str = node.replace(',', '').replace('%', '').replace('$', '')
                try:
                    flat_values.append(float(clean_str))
                except ValueError:
                    pass
                    
        _recurse(context_metrics)
        return flat_values

    def _fuzzy_match(self, target: float, valid_numbers: List[float]) -> bool:
        """Checks if a target number exists in the valid set, within the tolerance bounds."""
        if target == 0.0:
            return any(v == 0.0 for v in valid_numbers)
            
        # Tolerance calculation (e.g. +/- 5%)
        for val in valid_numbers:
            # Check if the target is within 5% of the valid context number
            margin = abs(val * self.tolerance_pct)
            lower_bound = round(val - margin, 4)
            upper_bound = round(val + margin, 4)
            
            target_rounded = round(target, 4)
            if lower_bound <= target_rounded <= upper_bound:
                return True
        return False

    def check_hallucinations(self, llm_text: str, context_metrics: Dict[str, Any]) -> int:
        """
        Scans text for numbers and verifies they exist in the provided context.
        Returns the number of ungrounded math hallucinations found.
        """
        if not llm_text:
            return 0
            
        llm_numbers = self._extract_numbers(llm_text)
        if not llm_numbers:
            return 0 # No math to hallucinate
            
        valid_context_numbers = self._flatten_context(context_metrics)
        
        # We implicitly allow standard conversational numbers (1, 2, 3, 5, 10, 50, 100)
        # to prevent flagging phrases like "Top 10" or "One of the best"
        safe_numbers = [1.0, 2.0, 3.0, 5.0, 10.0, 50.0, 100.0]
        
        hallucination_count = 0
        for num in llm_numbers:
            if num in safe_numbers:
                continue
                
            if not self._fuzzy_match(num, valid_context_numbers):
                logger.warning(f"Grounding Failure: LLM hallucinated number {num}")
                hallucination_count += 1
                
        return hallucination_count
