import requests

def search_ticker(query: str):
    """
    Searches for a ticker using Yahoo Finance's autocomplete API.
    Updated with modern headers to avoid blocking.
    """
    if not query or len(query.strip()) < 1:
        return []
        
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {
            "q": query,
            "lang": "en-US",
            "region": "US",
            "quotesCount": 10,
            "newsCount": 0,
            "enableFuzzyQuery": "false",
            "quotesQueryId": "tss_match_phrase_query"
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://finance.yahoo.com/',
            'Origin': 'https://finance.yahoo.com'
        }
        
        r = requests.get(url, params=params, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        results = []
        if 'quotes' in data:
            for q in data['quotes']:
                if 'symbol' in q:
                    # Filter for relevant quote types (Equity, ETF, Index)
                    quote_type = q.get('quoteType', '')
                    if quote_type in ['EQUITY', 'ETF', 'INDEX', 'MUTUALFUND', 'FUTURE']:
                        results.append({
                            "symbol": q['symbol'],
                            "name": q.get('shortname', q.get('longname', q['symbol'])),
                            "type": quote_type,
                            "exchange": q.get('exchange', 'N/A')
                        })
        return results
    except Exception as e:
        print(f"DEBUG: Search service error for query '{query}': {e}")
        # Log to stderr for potential debugging in production logs
        import sys
        print(f"Error in search_ticker: {str(e)}", file=sys.stderr)
        return []
