"""Tests for portfolio CSV parser."""
import os
import tempfile
import pytest
from services.portfolio_parser import parse_portfolio_csv


def _write_csv(content: str) -> str:
    """Write CSV content to a temp file, return path."""
    fd, path = tempfile.mkstemp(suffix='.csv')
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path


class TestRobinhoodTransactions:
    """Test parsing Robinhood transaction history CSVs."""

    def test_basic_buy_sell(self):
        csv = _write_csv(
            "Instrument,Trans Code,Quantity,Price\n"
            "AAPL,Buy,50,142.50\n"
            "NVDA,Buy,10,450.00\n"
            "AAPL,Sell,10,200.00\n"
            "TSLA,Buy,25,210.00\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 3
        aapl = next(h for h in result if h['symbol'] == 'AAPL')
        assert aapl['quantity'] == 40  # 50 bought - 10 sold
        assert aapl['avg_cost'] == 142.50  # Avg of buys only

        nvda = next(h for h in result if h['symbol'] == 'NVDA')
        assert nvda['quantity'] == 10
        assert nvda['avg_cost'] == 450.00

    def test_fully_sold_excluded(self):
        csv = _write_csv(
            "Instrument,Trans Code,Quantity,Price\n"
            "AAPL,Buy,50,142.50\n"
            "AAPL,Sell,50,200.00\n"
            "NVDA,Buy,10,450.00\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 1
        assert result[0]['symbol'] == 'NVDA'

    def test_dollar_sign_prices(self):
        csv = _write_csv(
            "Instrument,Trans Code,Quantity,Price\n"
            "AAPL,Buy,50,$142.50\n"
            "NVDA,Buy,10,$450.00\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 2
        aapl = next(h for h in result if h['symbol'] == 'AAPL')
        assert aapl['avg_cost'] == 142.50

    def test_activity_type_column(self):
        """Robinhood sometimes uses 'Activity Type' instead of 'Trans Code'."""
        csv = _write_csv(
            "Instrument,Activity Type,Quantity,Price\n"
            "AAPL,Bought,50,142.50\n"
            "NVDA,Sold,10,450.00\n"
            "NVDA,Bought,20,400.00\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 2
        nvda = next(h for h in result if h['symbol'] == 'NVDA')
        assert nvda['quantity'] == 10  # 20 bought - 10 sold


class TestSimpleHoldings:
    """Test parsing simple holdings CSVs."""

    def test_basic_holdings(self):
        csv = _write_csv(
            "Symbol,Quantity,Avg Cost\n"
            "AAPL,50,142.50\n"
            "NVDA,10,450.00\n"
            "TSLA,25,210.00\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 3
        aapl = next(h for h in result if h['symbol'] == 'AAPL')
        assert aapl['quantity'] == 50
        assert aapl['avg_cost'] == 142.50

    def test_ticker_column_name(self):
        csv = _write_csv(
            "Ticker,Quantity,Cost Basis\n"
            "AAPL,50,142.50\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 1
        assert result[0]['symbol'] == 'AAPL'

    def test_no_cost_column(self):
        csv = _write_csv(
            "Symbol,Quantity\n"
            "AAPL,50\n"
            "NVDA,10\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 2
        assert result[0]['avg_cost'] is None


class TestTickerList:
    """Test parsing generic ticker-only CSVs."""

    def test_symbol_column(self):
        csv = _write_csv(
            "Symbol\n"
            "AAPL\n"
            "NVDA\n"
            "TSLA\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 3
        assert all(h['quantity'] == 0 for h in result)
        assert all(h['avg_cost'] is None for h in result)

    def test_first_column_fallback(self):
        csv = _write_csv(
            "Stocks\n"
            "AAPL\n"
            "NVDA\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 2

    def test_deduplication(self):
        csv = _write_csv(
            "Symbol\n"
            "AAPL\n"
            "AAPL\n"
            "NVDA\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_file(self):
        csv = _write_csv("")
        result = parse_portfolio_csv(csv)
        os.unlink(csv)
        assert result == []

    def test_invalid_file(self):
        result = parse_portfolio_csv("/nonexistent/path.csv")
        assert result == []

    def test_whitespace_handling(self):
        csv = _write_csv(
            "Symbol , Quantity , Avg Cost\n"
            " AAPL , 50 , 142.50\n"
            " nvda , 10 , 450.00\n"
        )
        result = parse_portfolio_csv(csv)
        os.unlink(csv)

        assert len(result) == 2
        symbols = [h['symbol'] for h in result]
        assert 'AAPL' in symbols
        assert 'NVDA' in symbols  # Should be uppercased
