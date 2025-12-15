import pandas as pd
from typing import List

def parse_import_file(file_path: str) -> List[str]:
    """
    Parses an Excel or CSV file and extracts stock symbols.
    Assumes a column named 'Symbol', 'Ticker', or the first column if not found.
    """
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Normalize columns
        df.columns = [c.strip().lower() for c in df.columns]
        
        possible_cols = ['symbol', 'ticker', 'stock']
        target_col = None
        
        for col in possible_cols:
            if col in df.columns:
                target_col = col
                break
        
        if target_col:
            symbols = df[target_col].dropna().astype(str).tolist()
        else:
            # Fallback to first column
            symbols = df.iloc[:, 0].dropna().astype(str).tolist()
            
        # Clean symbols
        return [s.upper().strip() for s in symbols]
    except Exception as e:
        print(f"Error parsing file: {e}")
        return []
