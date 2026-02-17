import pandas as pd
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def parse_portfolio_csv(file_path: str) -> List[Dict]:
    """
    Parse a CSV file and extract portfolio holdings.
    
    Supports:
    1. Robinhood transaction history (Instrument, Trans Code, Quantity, Price)
    2. Simple holdings (Symbol/Ticker, Quantity, Avg Cost)
    3. Generic ticker list (just Symbol column → quantity=0, tracking only)
    
    Returns: [{symbol, quantity, avg_cost}, ...]
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        return []

    if df.empty:
        return []

    # Normalize column names
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    cols = set(df.columns)

    # Strategy 1: Robinhood Transaction History
    # Columns: instrument, trans_code (Buy/Sell), quantity, price
    if _is_robinhood_transactions(cols):
        return _parse_robinhood_transactions(df)

    # Strategy 2: Simple Holdings CSV
    # Columns: symbol/ticker, quantity, avg_cost/cost_basis
    if _is_simple_holdings(cols):
        return _parse_simple_holdings(df)

    # Strategy 3: Generic ticker list (fallback)
    return _parse_ticker_list(df)


def _is_robinhood_transactions(cols: set) -> bool:
    """Detect Robinhood transaction CSV format."""
    ticker_cols = {'instrument', 'symbol', 'ticker'}
    action_cols = {'trans_code', 'activity_type', 'type', 'side', 'action'}
    return bool(ticker_cols & cols) and bool(action_cols & cols) and 'quantity' in cols


def _is_simple_holdings(cols: set) -> bool:
    """Detect simple holdings CSV with quantity."""
    ticker_cols = {'symbol', 'ticker', 'stock'}
    return bool(ticker_cols & cols) and 'quantity' in cols


def _parse_robinhood_transactions(df: pd.DataFrame) -> List[Dict]:
    """Parse Robinhood transaction history → net holdings."""
    # Find ticker column
    ticker_col = _find_column(df.columns, ['instrument', 'symbol', 'ticker'])
    action_col = _find_column(df.columns, ['trans_code', 'activity_type', 'type', 'side', 'action'])
    qty_col = 'quantity'
    price_col = _find_column(df.columns, ['price', 'average_price', 'avg_price', 'cost'])

    if not ticker_col or not action_col:
        return []

    holdings: Dict[str, Dict] = {}  # symbol → {quantity, total_cost}

    for _, row in df.iterrows():
        symbol = str(row[ticker_col]).strip().upper()
        if not symbol or symbol == 'NAN' or len(symbol) > 10:
            continue

        try:
            quantity = abs(float(row[qty_col]))
        except (ValueError, TypeError):
            continue

        price = 0.0
        if price_col:
            try:
                price_val = str(row[price_col]).replace('$', '').replace(',', '').strip()
                price = abs(float(price_val))
            except (ValueError, TypeError):
                price = 0.0

        action = str(row[action_col]).strip().lower()
        is_buy = any(kw in action for kw in ['buy', 'bought', 'sto', 'reinvest'])
        is_sell = any(kw in action for kw in ['sell', 'sold', 'stc'])

        if symbol not in holdings:
            holdings[symbol] = {'quantity': 0.0, 'total_cost': 0.0, 'buy_qty': 0.0}

        if is_buy:
            holdings[symbol]['quantity'] += quantity
            holdings[symbol]['total_cost'] += quantity * price
            holdings[symbol]['buy_qty'] += quantity
        elif is_sell:
            holdings[symbol]['quantity'] -= quantity

    # Convert to output format, filter out zero/negative positions
    result = []
    for symbol, data in holdings.items():
        if data['quantity'] > 0.001:  # Still holding shares
            avg_cost = data['total_cost'] / data['buy_qty'] if data['buy_qty'] > 0 else None
            result.append({
                'symbol': symbol,
                'quantity': round(data['quantity'], 4),
                'avg_cost': round(avg_cost, 2) if avg_cost else None
            })

    result.sort(key=lambda x: x['symbol'])
    return result


def _parse_simple_holdings(df: pd.DataFrame) -> List[Dict]:
    """Parse simple holdings CSV (ticker, qty, avg_cost)."""
    ticker_col = _find_column(df.columns, ['symbol', 'ticker', 'stock'])
    qty_col = 'quantity'
    cost_col = _find_column(df.columns, ['avg_cost', 'average_cost', 'cost_basis', 'cost', 'price', 'avg_price'])

    if not ticker_col:
        return []

    result = []
    for _, row in df.iterrows():
        symbol = str(row[ticker_col]).strip().upper()
        if not symbol or symbol == 'NAN' or len(symbol) > 10:
            continue

        try:
            quantity = float(row[qty_col])
        except (ValueError, TypeError):
            continue

        if quantity <= 0:
            continue

        avg_cost = None
        if cost_col:
            try:
                cost_val = str(row[cost_col]).replace('$', '').replace(',', '').strip()
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
    ticker_col = _find_column(df.columns, ['symbol', 'ticker', 'stock'])
    if not ticker_col:
        # Fall back to first column
        ticker_col = df.columns[0]

    result = []
    seen = set()
    for _, row in df.iterrows():
        symbol = str(row[ticker_col]).strip().upper()
        if not symbol or symbol == 'NAN' or len(symbol) > 10 or symbol in seen:
            continue
        # Basic ticker validation: letters only, 1-5 chars
        if symbol.isalpha() and 1 <= len(symbol) <= 5:
            seen.add(symbol)
            result.append({
                'symbol': symbol,
                'quantity': 0,
                'avg_cost': None
            })

    result.sort(key=lambda x: x['symbol'])
    return result


def _find_column(columns, candidates: list) -> Optional[str]:
    """Find the first matching column name from candidates."""
    col_set = set(columns)
    for candidate in candidates:
        if candidate in col_set:
            return candidate
    return None
