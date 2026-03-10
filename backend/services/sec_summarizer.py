import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from edgar import set_identity, Company
import google.generativeai as genai

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, engine
import models
from sqlalchemy.orm import Session


logger = logging.getLogger("sec_summarizer")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# SEC requires identity
set_identity('Vinsight-Agent vinsight@example.com')

class SECSummarizer:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = None
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('models/gemini-2.0-flash')
            except Exception as e:
                logger.error(f"Failed to configure Gemini API: {e}")

    def _summarize_text_gemini(self, text: str, prompt: str) -> str:
        if not self.gemini_model: return "Summary generation failed (no LLM)."
        try:
            response = self.gemini_model.generate_content(
                prompt + "\n\nText:\n" + text[:200000], # Gemini Flash supports 1M token context
                generation_config={"temperature": 0.2, "max_output_tokens": 1500}
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini summarization failed: {e}")
            return "Summary generation failed."

    def summarize_section(self, text: str, section_name: str) -> str:
        if not text:
            return ""
            
        prompts = {
            "business": "Summarize the following SEC Business Description (Item 1) into a concise 150-word overview of what the company actually does and sells.",
            "risk": "Summarize the following SEC Risk Factors (Item 1A) into a dense, bulleted list of the top 5-7 most material threats facing this company. Keep it under 400 words.",
            "legal": "Summarize the following SEC Legal Proceedings (Item 3) into a brief bulleted list of material active lawsuits or regulatory actions. If none are material, say 'No material legal proceedings'.",
            "mda": "Summarize the following SEC MD&A (Item 7) into a tight 200-word paragraph detailing management's perspective on revenue trajectory and margins."
        }
        
        prompt = prompts.get(section_name, "Summarize the following SEC document concisely.")
        
        return self._summarize_text_gemini(text, prompt)

    def get_sec_context(self, symbol: str, db: 'Session') -> Dict[str, Any]:
        """
        Main entrypoint. Checks if DB has fresh data. If not, scrapes, summarizes, saves, and returns.
        """
        symbol = symbol.upper()
        # 1. Look up DB dates
        summary_record = db.query(models.SecSummary).filter(models.SecSummary.symbol == symbol).first()
        
        # 2. Get SEC Dates
        try:
            company = Company(symbol)
            tenk_list = company.get_filings(form='10-K')
            tenq_list = company.get_filings(form='10-Q')
            
            latest_10k = tenk_list.latest() if tenk_list else None
            latest_10q = tenq_list.latest() if tenq_list else None
            
            sec_latest_10k_date = latest_10k.filing_date if latest_10k else None
            sec_latest_10q_date = latest_10q.filing_date if latest_10q else None
            
        except Exception as e:
            logger.error(f"Failed to fetch metadata from SEC for {symbol}: {e}")
            # If SEC is down, return what we have in DB
            if summary_record:
                return self._record_to_dict(summary_record)
            return {}

        # 3. Validation Check
        cache_hit = True
        needs_10k_update = False
        needs_10q_update = False

        if summary_record:
            if str(summary_record.latest_10k_date) != str(sec_latest_10k_date):
                needs_10k_update = True
                cache_hit = False
            if str(summary_record.latest_10q_date) != str(sec_latest_10q_date):
                needs_10q_update = True
                cache_hit = False
        else:
            cache_hit = False
            needs_10k_update = True
            needs_10q_update = True

        if cache_hit:
            logger.info(f"SEC Cache HIT for {symbol} (10K: {summary_record.latest_10k_date}, 10Q: {summary_record.latest_10q_date})")
            return self._record_to_dict(summary_record)

        logger.info(f"SEC Cache MISS for {symbol}. Scraping needed.")
        
        if not summary_record:
            summary_record = models.SecSummary(symbol=symbol)
            db.add(summary_record)

        # 4. Ingest newer 10-K
        if needs_10k_update and latest_10k:
            logger.info(f"Scraping and summarizing 10-K for {symbol}...")
            obj = latest_10k.obj()
            
            # Item 1: Business
            txt_1 = self._get_item_text(obj, ["Item 1", "ITEM 1"])
            summary_record.business_description = self.summarize_section(txt_1, "business") if txt_1 else "No business description available."
            
            # Item 1A: Risk Factors
            txt_1a = self._get_item_text(obj, ["Item 1A", "ITEM 1A"])
            summary_record.risk_factors_10k = self.summarize_section(txt_1a, "risk") if txt_1a else "No risk factors available."
            
            # Item 3: Legal
            txt_3 = self._get_item_text(obj, ["Item 3", "ITEM 3"])
            summary_record.legal_proceedings = self.summarize_section(txt_3, "legal") if txt_3 else "No legal proceedings available."
            
            # Item 7: MD&A
            txt_7 = self._get_item_text(obj, ["Item 7", "ITEM 7"])
            summary_record.mda = self.summarize_section(txt_7, "mda") if txt_7 else "No MD&A available."
            
            summary_record.latest_10k_date = str(sec_latest_10k_date)
            
        # 5. Ingest newer 10-Q Delta
        if needs_10q_update and latest_10q:
            logger.info(f"Scraping and summarizing 10-Q for {symbol}...")
            qobj = latest_10q.obj()
            
            txt_q_1a = self._get_item_text(qobj, ["Part II, Item 1A", "Item 1A", "ITEM 1A"])
            if txt_q_1a and len(txt_q_1a.strip()) > 200: # Ensure it's not just "None" or boilerplate
                summary_record.latest_10q_delta = self.summarize_section(txt_q_1a, "risk")
            else:
                summary_record.latest_10q_delta = "No material updates to risk factors."
                
            summary_record.latest_10q_date = str(sec_latest_10q_date)

        summary_record.last_updated_at = datetime.utcnow()
        db.commit()
        db.refresh(summary_record)
        return self._record_to_dict(summary_record)

    def _get_item_text(self, obj: Any, keys: list) -> str:
        for k in keys:
            try:
                res = getattr(obj, k.lower().replace(" ", "_").replace(",", ""), None)
                if res is None and hasattr(obj, '__getitem__'):
                    res = obj[k]
                if res:
                    return str(res)
            except Exception:
                pass
        return ""

    def _record_to_dict(self, record: 'models.SecSummary') -> Dict[str, Any]:
        return {
            "symbol": record.symbol,
            "business_description": record.business_description,
            "risk_factors_10k": record.risk_factors_10k,
            "legal_proceedings": record.legal_proceedings,
            "mda": record.mda,
            "latest_10q_delta": record.latest_10q_delta,
            "latest_10k_date": record.latest_10k_date,
            "latest_10q_date": record.latest_10q_date,
            "last_updated_at": record.last_updated_at.isoformat() if record.last_updated_at else None
        }

def get_sec_summaries(symbol: str, db: 'Session') -> Dict[str, Any]:
    summarizer = SECSummarizer()
    return summarizer.get_sec_context(symbol, db)

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import SessionLocal
    from dotenv import load_dotenv
    load_dotenv()
    db = SessionLocal()
    summarizer = SECSummarizer()
    res = summarizer.get_sec_context("AAPL", db)
    print("Result for AAPL:")
    for key, val in res.items():
        if val and isinstance(val, str) and len(val) > 100:
            print(f"{key}: {val[:100]}...")
        else:
            print(f"{key}: {val}")
