import pandas as pd
import logging
import io
import csv
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_portfolio_csv(file_path: str) -> List[Dict]:
    """
    Parse a CSV file and extract portfolio holdings with support for multiple formats.
    
    Supports:
    1. Broker-specific templates (Fidelity, Schwab, Robinhood)
    2. Simple holdings (Symbol, Quantity, Avg Cost)
    3. Heuristic fallback for unknown CSVs
    
    Returns: [{symbol, quantity, avg_cost}, ...]
    """
    try:
        # Detect encoding and skip metadata rows
        content, header_idx = _preprocess_csv(file_path)
        if content is None:
            return []
            
        df = pd.read_csv(io.StringIO(content), skiprows=header_idx)
    except Exception as e:
        logger.error(f"Failed to read CSV {file_path}: {e}")
        return []

    if df.empty:
        return []

    # Normalize column names for easier matching: lowercase, strip, replace spaces/dots with underscores
    original_cols = list(df.columns)
    df.columns = [str(c).strip().lower().replace(' ', '_').replace('.', '_') for c in df.columns]
    cols = set(df.columns)

    # Strategy 1: Template Matching
    # Fidelity History/Activity
    if _is_fidelity_activity(cols):
        return _parse_transaction_history(df, {
            'symbol': ['symbol'],
            'action': ['action', 'description'],
            'quantity': ['quantity'],
            'price': ['price']
        }, broker="Fidelity")

    # Schwab Holdings / Positions
    if _is_schwab_holdings(cols):
        return _parse_simple_holdings(df, {
            'symbol': ['symbol'],
            'quantity': ['quantity'],
            'avg_cost': ['cost_basis', 'price']
        })

    # Strategy 2: Improved Robinhood Handling
    if _is_robinhood_transactions(cols):
        return _parse_transaction_history(df, {
            'symbol': ['instrument', 'symbol', 'ticker'],
            'action': ['trans_code', 'activity_type', 'type', 'side', 'action'],
            'quantity': ['quantity'],
            'price': ['price', 'average_price', 'avg_price', 'cost']
        }, broker="Robinhood")

    # Strategy 3: Standard Simple Holdings (Symbol, Qty, Cost)
    if _is_simple_holdings(cols):
        return _parse_simple_holdings(df, {
            'symbol': ['symbol', 'ticker', 'stock'],
            'quantity': ['quantity', 'qty', 'shares'],
            'avg_cost': ['avg_cost', 'average_cost', 'cost_basis', 'cost', 'price', 'avg_price']
        })

    # Strategy 4: Fallback - Ticker List (just extract anything looking like a ticker)
    return _parse_ticker_list(df)


def _preprocess_csv(file_path: str) -> Tuple[Optional[str], int]:
    """
    Read file, handling encodings and finding the actual header row.
    Returns (content_string, header_line_index).
    """
    encodings = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252']
    content = None
    
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
            
    if not content:
        return None, 0

    lines = content.splitlines()
    header_idx = 0
    
    # Heuristic to find the header: look for a line containing 'symbol' or 'ticker' or many recognized keywords
    keywords = {'symbol', 'ticker', 'instrument', 'quantity', 'qty', 'price', 'action', 'trans_code'}
    for i, line in enumerate(lines[:10]):  # Only check first 10 lines
        # Normalize and split
        parts = [p.strip().lower().replace(' ', '_').replace('.', '_') for p in line.split(',')]
        if any(k in parts for k in keywords):
            header_idx = i
            break
            
    return content, header_idx


def _is_fidelity_activity(cols: set) -> bool:
    """Detect Fidelity activity export."""
    return 'symbol' in cols and 'action' in cols and 'quantity' in cols


def _is_schwab_holdings(cols: set) -> bool:
    """Detect Schwab holdings export."""
    # Schwab often has 'Symbol', 'Description', 'Quantity', 'Price', 'Price Change'
    return 'symbol' in cols and 'quantity' in cols and ('price' in cols or 'cost_basis' in cols)


def _is_robinhood_transactions(cols: set) -> bool:
    """Detect Robinhood transaction CSV format."""
    ticker_cols = {'instrument', 'symbol', 'ticker'}
    action_cols = {'trans_code', 'activity_type', 'type', 'side', 'action'}
    return bool(ticker_cols & cols) and bool(action_cols & cols) and 'quantity' in cols


def _is_simple_holdings(cols: set) -> bool:
    """Detect simple holdings CSV with quantity."""
    ticker_cols = {'symbol', 'ticker', 'stock'}
    qty_cols = {'quantity', 'qty', 'shares'}
    return bool(ticker_cols & cols) and bool(qty_cols & cols)


def _parse_transaction_history(df: pd.DataFrame, mapping: Dict[str, List[str]], broker: str = "") -> List[Dict]:
    """Generic transaction history parser (Buy/Sell/Split)."""
    ticker_col = _find_column(df.columns, mapping['symbol'])
    action_col = _find_column(df.columns, mapping['action'])
    qty_col = _find_column(df.columns, mapping['quantity'])
    price_col = _find_column(df.columns, mapping.get('price', []))

    if not ticker_col or not action_col or not qty_col:
        return []

    holdings: Dict[str, Dict] = {}  # symbol -> {quantity, total_cost, buy_qty}

    for _, row in df.iterrows():
        symbol = str(row[ticker_col]).strip().upper()
        # Basic filter for valid symbols (ignore cash, weird descriptions)
        if not symbol or symbol == 'NAN' or len(symbol) > 10:
            continue
            
        # Specific broker filters
        if broker == "Fidelity" and symbol == "SPAXX":  # Fidelity cash sweep
            continue

        try:
            quantity = abs(float(str(row[qty_col]).replace(',', '')))
        except (ValueError, TypeError):
            continue

        price = 0.0
        if price_col:
            try:
                price_val = str(row[price_col]).replace('$', '').replace(',', '').strip()
                if price_val and price_val.lower() != 'nan':
                    price = abs(float(price_val))
            except (ValueError, TypeError):
                price = 0.0

        action = str(row[action_col]).strip().lower()
        
        # Action keywords
        buy_keywords = ['buy', 'bought', 'sto', 'reinvest', 'dividend reinvestment', 'reinvestment']
        sell_keywords = ['sell', 'sold', 'stc']
        
        is_buy = any(kw in action for kw in buy_keywords)
        is_sell = any(kw in action for kw in sell_keywords)

        if symbol not in holdings:
            holdings[symbol] = {'quantity': 0.0, 'total_cost': 0.0, 'buy_qty': 0.0}

        if is_buy:
            holdings[symbol]['quantity'] += quantity
            holdings[symbol]['total_cost'] += quantity * price
            holdings[symbol]['buy_qty'] += quantity
        elif is_sell:
            holdings[symbol]['quantity'] -= quantity

    return _finalize_holdings(holdings)


def _parse_simple_holdings(df: pd.DataFrame, mapping: Dict[str, List[str]]) -> List[Dict]:
    """Parse positions/holdings CSV (current snapshot)."""
    ticker_col = _find_column(df.columns, mapping['symbol'])
    qty_col = _find_column(df.columns, mapping['quantity'])
    cost_col = _find_column(df.columns, mapping.get('avg_cost', []))

    if not ticker_col or not qty_col:
        return []

    result = []
    for _, row in df.iterrows():
        symbol = str(row[ticker_col]).strip().upper()
        if not symbol or symbol == 'NAN' or len(symbol) > 10:
            continue

        try:
            quantity = float(str(row[qty_col]).replace(',', ''))
        except (ValueError, TypeError):
            continue

        if quantity <= 0:
            continue

        avg_cost = None
        if cost_col:
            try:
                cost_val = str(row[cost_col]).replace('$', '').replace(',', '').strip()
                if cost_val and cost_val.lower() != 'nan':
                    avg_cost = float(cost_val)
            except (ValueError, TypeError):
                avg_cost = None

        result.append({
            'symbol': symbol,
            'quantity': round(quantity, 4),
            'avg_cost': round(avg_cost, 2) if avg_cost else None
        })

    result.sort(key=lambda x: x['symbol'])
    return result


def _parse_ticker_list(df: pd.DataFrame) -> List[Dict]:
    """Fallback: extract tickers from first suitable column."""
    # Look for a column that looks like symbols (uppercase, short length)
    ticker_col = None
    for col in df.columns:
        # Check first 5 rows to see if they look like tickers
        sample = df[col].dropna().head(5).astype(str).tolist()
        if all(1 <= len(s.strip()) <= 6 and s.strip().isalpha() for s in sample):
            ticker_col = col
            break
            
    if not ticker_col:
        ticker_col = df.columns[0]

    result = []
    seen = set()
    for _, row in df.iterrows():
        symbol = str(row[ticker_col]).strip().upper()
        if not symbol or symbol == 'NAN' or symbol in seen:
            continue
            
        # Basic ticker validation: 1-6 chars, letters or letters+dot (for classes)
        valid_chars = all(c.isalnum() or c == '.' for c in symbol)
        if valid_chars and 1 <= len(symbol) <= 8:
            seen.add(symbol)
            result.append({
                'symbol': symbol,
                'quantity': 0,
                'avg_cost': None
            })

    result.sort(key=lambda x: x['symbol'])
    return result


def _finalize_holdings(holdings: Dict[str, Dict]) -> List[Dict]:
    """Convert transaction aggregation to result list."""
    result = []
    for symbol, data in holdings.items():
        if data['quantity'] > 0.0001:  # Still holding shares
            avg_cost = data['total_cost'] / data['buy_qty'] if data['buy_qty'] > 0 else None
            result.append({
                'symbol': symbol,
                'quantity': round(data['quantity'], 4),
                'avg_cost': round(avg_cost, 2) if avg_cost else None
            })

    result.sort(key=lambda x: x['symbol'])
    return result


def _find_column(columns, candidates: list) -> Optional[str]:
    """Find the first matching column name from candidates (already normalized)."""
    col_set = set(columns)
    for candidate in candidates:
        norm_candidate = candidate.lower().replace(' ', '_').replace('.', '_')
        if norm_candidate in col_set:
            return norm_candidate
    return None
