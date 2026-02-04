
from services.vinsight_scorer import EquityScorer, CryptoScorer, ETFScorer, StockData

def test_poly():
    scorers = [EquityScorer(), CryptoScorer(), ETFScorer()]
    print(f"Instantiated {len(scorers)} scorers.")
    
    for s in scorers:
        print(f"Scorer: {s.__class__.__name__}, Version: {s.VERSION}")
        try:
             # Just checking if evaluate exists and is callable. 
             # We pass None or garbage just to see if it accepts the call or raises NotImplemented vs TypeError
             # Actually evaluate expects data, Crypto/ETF implementation is placeholder so it might return placeholder result safely.
             if isinstance(s, EquityScorer):
                 continue # Skip equity, tested elsewhere
             res = s.evaluate(None)
             print(f"  -> Evaluate Result: {res.rating}")
        except Exception as e:
             print(f"  -> Evaluate Error: {e}")

if __name__ == "__main__":
    test_poly()
