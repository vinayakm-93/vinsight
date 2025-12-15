import requests

def search_ticker(query: str):
    """
    Searches for a ticker using Yahoo Finance's autocomplete API.
    """
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        r = requests.get(url, params=params, headers=headers)
        data = r.json()
        
        results = []
        if 'quotes' in data:
            for q in data['quotes']:
                if 'symbol' in q:
                    results.append({
                        "symbol": q['symbol'],
                        "name": q.get('shortname', q.get('longname', '')),
                        "type": q.get('quoteType', ''),
                        "exchange": q.get('exchange', '')
                    })
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []
