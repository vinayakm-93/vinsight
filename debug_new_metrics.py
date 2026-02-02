import yfinance as yf
import pandas as pd

def check_metrics(ticker):
    print(f"--- Checking {ticker} ---")
    stock = yf.Ticker(ticker)
    
    # 1. Info check
    info = stock.info
    print(f"EBITDA: {info.get('ebitda')}")
    print(f"Total Debt: {info.get('totalDebt')}")
    print(f"Interest Coverage (info): {info.get('interestCoverage')}") # Often missing
    
    # 2. Financials for Margin Trend & Interest Coverage
    print("\n[Quarterly Financials Head]")
    qf = stock.quarterly_financials
    if not qf.empty:
        print(qf.index)
        # Check for Gross Profit and Total Revenue for Margin Calculation
        if 'Gross Profit' in qf.index and 'Total Revenue' in qf.index:
            rev = qf.loc['Total Revenue']
            gp = qf.loc['Gross Profit']
            margins = gp / rev
            print(f"Recent Gross Margins: {margins.head(4).tolist()}")
            
        # Check for Interest Expense for Coverage
        if 'Interest Expense' in qf.index and 'EBIT' in qf.index:
            ebit = qf.loc['EBIT']
            intest = qf.loc['Interest Expense']
            # Note: Interest Expense is usually negative in yfinance
            cov = ebit / intest.abs()
            print(f"Recent Interest Coverage: {cov.head(4).tolist()}")
            
    # 3. Balance Sheet for Altman Z & Debt/EBITDA
    print("\n[Quarterly Balance Sheet Head]")
    qbs = stock.quarterly_balance_sheet
    if not qbs.empty:
        required = ['Total Assets', 'Total Liab', 'Total Current Assets', 'Total Current Liabilities', 'Retained Earnings']
        print(f"Available keys: {[k for k in required if k in qbs.index]}")
        
    print(f"Current Price: {info.get('currentPrice')}")
    print(f"52w High: {info.get('fiftyTwoWeekHigh')}")
    print(f"Avg Vol: {info.get('averageVolume')}")

if __name__ == "__main__":
    check_metrics("NVDA")
