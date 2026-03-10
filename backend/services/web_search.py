import logging
from duckduckgo_search import DDGS
from typing import List, Dict, Any

# Setup Logging
logger = logging.getLogger("web_search")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class WebSearchBackend:
    def __init__(self):
        # We initialize the DDGS client
        pass
        
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """
        Executes a live web search using DuckDuckGo.
        Returns a list of dicts with title, snippet, and url.
        - Enforces a 10-second timeout per attempt.
        - Retries once with 2-second backoff on failure.
        - Falls back to a broadened (ticker-only) query if specific query returns 0 results.
        """
        import time

        def _attempt(q: str) -> List[Dict[str, str]]:
            results = []
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(q, max_results=top_k, timelimit=None))
                for res in raw_results:
                    results.append({
                        "title":   res.get("title", "No Title"),
                        "snippet": res.get("body", "No description available.").strip(),
                        "url":     res.get("href", ""),
                    })
            return results

        logger.info(f"DDG search: '{query}'")

        # ── Attempt 1 ────────────────────────────────────────────────
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
        results = []
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(_attempt, query)
                results = fut.result(timeout=10)
        except FutureTimeout:
            logger.warning(f"DDG timeout on first attempt for '{query}', retrying...")
        except Exception as e:
            logger.warning(f"DDG error on first attempt for '{query}': {e}")

        # ── Retry once (2-second back-off) ──────────────────────────
        if not results:
            time.sleep(2)
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    fut = pool.submit(_attempt, query)
                    results = fut.result(timeout=10)
            except Exception as e:
                logger.warning(f"DDG retry also failed: {e}")

        # ── Broad fallback query ─────────────────────────────────────
        if not results:
            # Strip complex specifics down to "<ticker> <first 3 meaningful words>"
            words = [w for w in query.split() if len(w) > 2][:4]
            fallback_q = " ".join(words) + " news"
            logger.info(f"DDG zero results — trying fallback: '{fallback_q}'")
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    fut = pool.submit(_attempt, fallback_q)
                    results = fut.result(timeout=10)
            except Exception as e:
                logger.error(f"DDG fallback also failed: {e}")

        logger.info(f"DDG returned {len(results)} results for '{query}'")
        return results


if __name__ == "__main__":
    # LOCAL STABILITY TEST
    print("\\n--- Phase 2 Local Stability Test ---")
    searcher = WebSearchBackend()
    
    mock_query = "NVIDIA AI chip news 2024"
    print(f"Executing test query: '{mock_query}'")
    
    test_results = searcher.search(mock_query, top_k=3)
    
    if len(test_results) == 3:
        print("\\n✅ Passed: Retrieved exactly 3 snippets.")
    else:
        print(f"\\n❌ Failed: Retrieved {len(test_results)} snippets. Expected 3.")
        
    for i, res in enumerate(test_results):
        print(f"\\nResult {i+1}:")
        print(f"  Title: {res['title']}")
        print(f"  URL: {res['url']}")
        print(f"  Snippet: {res['snippet'][:150]}...")
        
    print("\\n--- Test Complete ---")
