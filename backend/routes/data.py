from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from services import finance, analysis, simulation, search, earnings
from services.search import search_ticker
from services.vinsight_scorer import VinSightScorer, StockData, Fundamentals, Technicals, Sentiment, Projections, ScoreResult
from services.groq_sentiment import get_groq_analyzer
import yfinance as yf
import requests
import logging
import json
import os

logger = logging.getLogger(__name__)

# yf_session removed to allow yfinance to handle its own session

router = APIRouter(prefix="/api/data", tags=["data"])

class BatchStockRequest(BaseModel):
    tickers: list[str]

@router.get("/sector-benchmarks")
def get_sector_benchmarks():
    """Return sector benchmarks for peer comparison display in UI."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'sector_benchmarks.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sector benchmarks config not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid sector benchmarks config")


@router.get("/quote/{ticker}")
def get_quick_quote(ticker: str):
    """
    Lightweight endpoint for current price data.
    Returns only essential real-time information with minimal API calls.
    Perfect for frequent polling without exhausting rate limits.
    """
    from services import yahoo_client
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get the most recent price data
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
        previous_close = info.get('regularMarketPreviousClose') or info.get('previousClose', 0)
        
        # Calculate change
        change = current_price - previous_close if current_price and previous_close else 0
        change_percent = (change / previous_close * 100) if previous_close else 0
        
        return {
            "symbol": ticker.upper(),
            "currentPrice": current_price,
            "previousClose": previous_close,
            "change": change,
            "changePercent": change_percent,
            "marketState": info.get('marketState', 'CLOSED'),  # REGULAR, PRE, POST, CLOSED
            "timestamp": info.get('regularMarketTime', None)
        }
    except Exception as e:
        # Fallback to yahoo_client on rate limit
        if "Too Many Requests" in str(e) or "Rate limited" in str(e) or "429" in str(e):
            logger.info(f"Using yahoo_client fallback for {ticker} quick quote")
            chart = yahoo_client.get_chart_data(ticker, interval="1d", range_="1d")
            if chart and chart.get("meta"):
                meta = chart["meta"]
                last_price = meta.get("regularMarketPrice", 0)
                prev_close = meta.get("chartPreviousClose", 0)
                change = last_price - prev_close if prev_close else 0
                change_percent = (change / prev_close * 100) if prev_close else 0
                return {
                    "symbol": ticker.upper(),
                    "currentPrice": last_price,
                    "previousClose": prev_close,
                    "change": change,
                    "changePercent": change_percent,
                    "marketState": "REGULAR", # Assumption for fallback
                    "timestamp": meta.get("regularMarketTime")
                }
        logger.error(f"Error fetching quote for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/earnings/{ticker}")
def get_earnings_analysis(ticker: str, db: Session = Depends(get_db)):
    return earnings.analyze_earnings(ticker, db)

@router.get("/search")
def search_stocks(q: str):
    return search_ticker(q)

@router.get("/stock/{ticker}")
def get_stock_details(ticker: str):
    try:
        info = finance.get_stock_info(ticker)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-prices")
async def get_batch_prices_endpoint(request: BatchStockRequest):
    """
    Get lightweight batch stock prices for Watchlist Sidebar.
    Optimized for speed.
    """
    try:
        data = finance.get_batch_prices(request.tickers)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-stock")
def get_batch_stock_details(payload: dict):
    """
    Fetch details for multiple stocks in one request.
    Payload: { "tickers": ["AAPL", "MSFT", ...] }
    """
    tickers = payload.get("tickers", [])
    if not tickers:
        return []
        
    try:
        return finance.get_batch_stock_details(tickers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{ticker}")
def get_stock_history_data(ticker: str, period: str = "1mo", interval: str = "1d"):
    try:
        history = finance.get_stock_history(ticker, period, interval)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/news/{ticker}")
def get_stock_news(ticker: str):
    try:
        news = finance.get_news(ticker)
        return news
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/{ticker}")
def get_technical_analysis(ticker: str, period: str = "2y", interval: str = "1d", include_sentiment: bool = False, include_simulation: bool = False, sector_override: str = None):
    """
    Technical analysis with optional sector override.
    sector_override: None (auto-detect), 'Standard' (defaults), or specific sector name
    """
    try:
        # Use concurrent.futures to fetch independent data in parallel
        # 1. History, Info, News, Institutional can be fetched concurrently
        import concurrent.futures
        
        # Define fetch wrappers to handle exceptions gracefully (Graceful Degradation)
        from services import yahoo_client
        import pandas as pd
        
        def fetch_history():
            try:
                return finance.get_stock_history(ticker, period, interval)
            except Exception as e:
                logger.error(f"Error fetching history: {e}")
                # Fallback to yahoo_client on rate limit
                if "Too Many Requests" in str(e) or "Rate limited" in str(e) or "429" in str(e):
                    logger.info(f"Using yahoo_client fallback for {ticker} history")
                    chart = yahoo_client.get_chart_data(ticker, interval=interval, range_=period)
                    if chart and chart.get("timestamp"):
                        # Convert to list of dicts format with CAPITALIZED keys (expected by analysis.py)
                        timestamps = chart["timestamp"]
                        quotes = chart.get("indicators", {}).get("quote", [{}])[0]
                        history = []
                        for i, ts in enumerate(timestamps):
                            close_val = quotes.get("close", [None])[i] if i < len(quotes.get("close", [])) else None
                            # Skip entries where 'Close' is None to avoid downstream errors
                            if close_val is None:
                                continue
                                
                            history.append({
                                "Date": pd.Timestamp(ts, unit='s').isoformat(),
                                "Open": quotes.get("open", [None])[i] if i < len(quotes.get("open", [])) else close_val,
                                "High": quotes.get("high", [None])[i] if i < len(quotes.get("high", [])) else close_val,
                                "Low": quotes.get("low", [None])[i] if i < len(quotes.get("low", [])) else close_val,
                                "Close": close_val,
                                "Volume": quotes.get("volume", [None])[i] if i < len(quotes.get("volume", [])) else 0,
                            })
                        return history
                return []
                
        def fetch_info():
            try:
                return finance.get_stock_info(ticker)
            except Exception as e:
                logger.error(f"Error fetching stock info: {e}")
                # Fallback to yahoo_client on rate limit
                if "Too Many Requests" in str(e) or "Rate limited" in str(e) or "429" in str(e):
                    logger.info(f"Using yahoo_client fallback for {ticker} info")
                    
                    # Try chart data first for basic info as it's more reliable than quoteSummary
                    chart = yahoo_client.get_chart_data(ticker, interval="1d", range_="1d")
                    info = {}
                    if chart and chart.get("meta"):
                        meta = chart["meta"]
                        info['currentPrice'] = meta.get('regularMarketPrice') or meta.get('chartPreviousClose')
                        info['previousClose'] = meta.get('chartPreviousClose')
                        info['shortName'] = meta.get('shortName', ticker)
                        info['longName'] = meta.get('longName', ticker)
                        info['sector'] = meta.get('instrumentType', 'Financial Services') # Default for funds often missing sector
                    
                    # Try to supplement with quoteSummary if available
                    summary = yahoo_client.get_quote_summary(ticker, modules="price,summaryDetail,financialData,defaultKeyStatistics")
                    if summary:
                        for module in ["price", "summaryDetail", "financialData", "defaultKeyStatistics"]:
                            if module in summary:
                                for key, val in summary[module].items():
                                    if key not in info: # Don't overwrite what we got from chart
                                        if isinstance(val, dict) and "raw" in val:
                                            info[key] = val["raw"]
                                        elif not isinstance(val, dict):
                                            info[key] = val
                    return info
                return {}

        def fetch_news():
            try:
                return finance.get_news(ticker)
            except Exception as e:
                logger.error(f"Error fetching news: {e}")
                return []


        def fetch_institutional():
            try:
                return finance.get_institutional_holders(ticker)
            except Exception as e:
                logger.error(f"Error fetching institutional: {e}")
                return {}

        def fetch_earnings():
             try:
                 return earnings.analyze_earnings(ticker, next(get_db()))
             except Exception as e:
                 logger.error(f"Error fetching earnings: {e}")
                 return {}

        def fetch_advanced():
            try:
                return finance.get_advanced_metrics(ticker)
            except Exception as e:
                logger.error(f"Error fetching advanced metrics: {e}")
                return {} # Fallbacks handled below

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_hist = executor.submit(fetch_history)
            future_info = executor.submit(fetch_info)
            future_news = executor.submit(fetch_news)
            future_inst = executor.submit(fetch_institutional)
            future_adv = executor.submit(fetch_advanced)
            # future_earn = executor.submit(fetch_earnings) # DB dependency tricky here
            
            # Wait for results
            history = future_hist.result()
            fundamentals_info = future_info.result()
            news = future_news.result()
            institutional = future_inst.result()
            advanced_metrics = future_adv.result()

        if not history:
             raise HTTPException(status_code=404, detail="No history data found")
        
        # 2. Calculate Technical Indicators FIRST (needed for VinSight)
        indicators = analysis.calculate_technical_indicators(history)
        risk = analysis.calculate_risk_metrics(history)
        
        # 3. Process additional Data for VinSight
        
        if include_sentiment:
            # v7.3 Optimization: Disable deep analysis (LLM) since sentiment is 0% weight.
            try:
                sentiment_result = analysis.calculate_news_sentiment(news, deep_analysis=False, ticker=ticker)
            except Exception as e:
                logger.error(f"Error calculating sentiment: {e}")
                sentiment_result = None
            
            # Default to neutral if None
            if not sentiment_result:
                 sentiment_result = {"label": "Neutral", "score": 0, "confidence": 0, "article_count": 0}
        else:
            sentiment_result = None
            
        # Run Simulation (Ideally distinct from 'analysis' but we are consolidating)
        # Using a smaller history window for simulation usually sufficient (1y) but 2y is fine
        if include_simulation:
            sim_result = simulation.run_monte_carlo(history, days=90, simulations=10000) # 10k sims for statistical accuracy
        else:
            sim_result = {}
        
        # v5.0 Data Fetching
        regime = finance.get_market_regime()
        
        # Ensure beta is a float (handle None or missing)
        raw_beta = fundamentals_info.get("beta")
        beta = float(raw_beta) if raw_beta is not None else 1.0
        
        # Yield is often 0 if missing. yfinance provides 'dividendYield' (decimal)
        raw_yield = fundamentals_info.get("dividendYield")
        div_yield = float(raw_yield) if raw_yield is not None else 0.0
        div_yield_pct = div_yield * 100

        # 4. Adapt Data for VinSight Scorer v5.0
        
        # --- Fundamentals ---
        # Inst Ownership
        inst_own = institutional.get("institutionsPercentHeld", 0) * 100 # Convert to % if decimal
        if inst_own < 1 and institutional.get("institutionsPercentHeld", 0) > 0:
             inst_own = institutional.get("institutionsPercentHeld", 0) * 100
        elif inst_own == 0 and "institutionsPercentHeld" in institutional:
             inst_own = institutional["institutionsPercentHeld"] * 100

        # Inst Ownership Change
        # Analyze insider transactions to infer institutional sentiment
        # If recent transactions show more buying -> "Rising", more selling -> "Falling", else "Flat"
        txs = institutional.get('insider_transactions', [])
        buy_value = 0
        sell_value = 0
        for t in txs[:10]:
            text = t.get('Text', '').lower()
            value = t.get('Value') or 0
            if 'sale' in text or 'sell' in text:
                sell_value += abs(value) if isinstance(value, (int, float)) else 0
            elif 'purchase' in text or 'buy' in text:
                buy_value += abs(value) if isinstance(value, (int, float)) else 0
        
        if buy_value > sell_value * 1.5:  # Significantly more buying
            inst_changing = "Rising"
        elif sell_value > buy_value * 1.5:  # Significantly more selling
            inst_changing = "Falling"
        else:
            inst_changing = "Flat"

        # v5.5 Price handling: Ensure current_price is a float and not None
        last_close = history[-1]['Close'] if history else None
        current_price = float(last_close) if last_close is not None else 0.0
        
        # Handle sentiment safely - use default values if sentiment is None
        if sentiment_result:
            sentiment_score = sentiment_result.get('score', 0)
            sentiment_label = sentiment_result.get('label', 'Neutral')
            news_art_count = sentiment_result.get('article_count', 0)
        else:
            sentiment_score = 0
            sentiment_label = 'Neutral'
            # Fix: Use actual news count even if deep analysis was skipped
            news_art_count = len(news) if news else 0
            
        # Social Volume Proxy: High if article count > 5 (arbitrary for now)
        news_vol_high = news_art_count > 5
        
        analyst_data = fundamentals_info.get('analyst', {})
        target_price = analyst_data.get('targetMeanPrice', current_price)
        num_analysts = analyst_data.get('numberOfAnalystOpinions', 0)
        
        upside = ((target_price / current_price) - 1) * 100 if current_price > 0 and target_price > 0 else 0

        earnings_growth = fundamentals_info.get("earningsQuarterlyGrowth", 0) # decimal
        
        # P/E
        pe = fundamentals_info.get("trailingPE", 0)
        
        # PEG Ratio
        peg = finance.get_peg_ratio(ticker)
        
        detected_sector = fundamentals_info.get("sector", "Technology")
        
        # Apply sector override if provided
        if sector_override and sector_override != "Auto":
            if sector_override == "Standard":
                active_sector = "Standard"  # Will use defaults in scorer
            else:
                active_sector = sector_override
        else:
            active_sector = detected_sector
        
        # v6.3: Get new fields
        # v7.3: Get new fields
        profit_margin = fundamentals_info.get("profitMargins", 0) or 0
        operating_margin = fundamentals_info.get("operatingMargins", 0) or 0
        debt_to_equity = fundamentals_info.get("debtToEquity", 0) or 0
        if debt_to_equity > 10:
            debt_to_equity = debt_to_equity / 100
        
        current_ratio = fundamentals_info.get("currentRatio") or 0.0
        roe = fundamentals_info.get("returnOnEquity") or 0.0
        roa = fundamentals_info.get("returnOnAssets") or 0.0
        forward_pe = fundamentals_info.get("forwardPE") or 0.0
            
        fcf_yield = fundamentals_info.get("fcf_yield", 0.0)
        
        # Fetch EPS Surprise (New helper in finance)
        eps_surprise = finance.get_earnings_surprise(ticker)
        
        fund_data = Fundamentals(
            inst_ownership=inst_own,
            pe_ratio=pe or 0,
            forward_pe=forward_pe,
            peg_ratio=peg,
            earnings_growth_qoq=earnings_growth,
            revenue_growth_3y=advanced_metrics.get('revenue_growth_3y_cagr'), # None if missing
            sector_name=active_sector,
            profit_margin=profit_margin,
            operating_margin=operating_margin,
            gross_margin_trend=advanced_metrics.get('gross_margin_trend', 'Flat'), # NEW
            roe=roe,
            roa=roa,
            debt_to_equity=debt_to_equity,
            debt_to_ebitda=advanced_metrics.get('debt_to_ebitda'), # None if missing
            interest_coverage=advanced_metrics.get('interest_coverage', 100.0), # 100 is safe default (no debt mood)
            current_ratio=current_ratio,
            altman_z_score=advanced_metrics.get('altman_z_score'), # None if missing
            fcf_yield=fcf_yield,
            eps_surprise_pct=eps_surprise
        )

        # --- Technicals ---
        latest_ind = indicators[-1] if indicators else {}
        rsi = latest_ind.get('RSI', 50)
        sma50 = latest_ind.get('SMA_50', 0)
        sma200 = latest_ind.get('SMA_200', 0)
        
        # Fix: Derive momentum from price vs SMA50 (more reliable than indicator signal)
        if current_price > sma50:
            momentum = "Bullish"
        else:
            momentum = "Bearish"

        # Volume Trend - Use 5-day average for more reliable signal
        if len(history) >= 6:
            recent_prices = [h['Close'] for h in history[-6:]]
            recent_volumes = [h['Volume'] for h in history[-6:]]
            
            # Price trend: compare last 3 days avg to previous 3 days avg
            price_recent = sum(recent_prices[-3:]) / 3
            price_earlier = sum(recent_prices[:3]) / 3
            price_rising = price_recent > price_earlier
            
            # Volume trend: compare last 3 days avg to previous 3 days avg
            vol_recent = sum(recent_volumes[-3:]) / 3
            vol_earlier = sum(recent_volumes[:3]) / 3
            vol_rising = vol_recent > vol_earlier
            
            if price_rising and vol_rising:
                vol_trend = "Price Rising + Vol Rising"
            elif price_rising and not vol_rising:
                vol_trend = "Price Rising + Vol Falling"
            elif not price_rising and vol_rising:
                vol_trend = "Price Falling + Vol Rising"
            else:
                vol_trend = "Weak/Mixed"
        elif len(history) >= 2:
            p_change = history[-1]['Close'] - history[-2]['Close']
            v_change = history[-1]['Volume'] - history[-2]['Volume']
            if p_change > 0 and v_change > 0:
                vol_trend = "Price Rising + Vol Rising"
            elif p_change > 0 and v_change < 0:
                vol_trend = "Price Rising + Vol Falling"
            elif p_change < 0 and v_change > 0:
                vol_trend = "Price Falling + Vol Rising"
            else:
                vol_trend = "Weak/Mixed"
        else:
            vol_trend = "Weak/Mixed"
            
        # CFA Technicals (RVOL & Distance to High)
        avg_vol = fundamentals_info.get('averageVolume')
        curr_vol = history[-1]['Volume'] if history else 0
        relative_volume = (curr_vol / avg_vol) if avg_vol and avg_vol > 0 else 1.0
        
        high52 = fundamentals_info.get('fiftyTwoWeekHigh')
        distance_to_high = ((high52 - current_price) / high52) if high52 and high52 > 0 else 0.0

        tech_data = Technicals(
            price=current_price,
            sma50=sma50,
            sma200=sma200,
            rsi=rsi,
            relative_volume=relative_volume,
            distance_to_high=distance_to_high,
            momentum_label=momentum,
            volume_trend=vol_trend
        )

        # Insider Activity Detection
        # v3.0: MSPR is now fetched in sentiment analysis, use it if available
        ins_activity = "No Activity"
        
        # Check if sentiment result has MSPR from Finnhub
        if sentiment_result and sentiment_result.get('insider_mspr_label') and sentiment_result.get('insider_mspr_label') != "No Data":
            ins_activity = sentiment_result.get('insider_mspr_label', 'No Activity')
        else:
            # Fallback to yfinance transaction parsing (with heuristic 10b5-1 detection)
            txs = institutional.get('insider_transactions', [])
            
            # Filter out and count transactions
            discretionary_txs = [t for t in txs if not t.get('is_10b5_1', False)]
            
            insider_buy = 0
            insider_sell = 0
            sell_dates = []
            executive_sells = 0
            
            from datetime import datetime
            
            for t in discretionary_txs:
                text = t.get('Text', '').lower()
                position = t.get('Position', '').lower()
                date_str = t.get('Date', '')
                
                # Double check for gifts in case heuristic missed it
                if 'gift' in text:
                    continue
                
                is_sale = any(word in text for word in ['sale', 'sell', 'sold', 'disposition'])
                is_buy = any(word in text for word in ['purchase', 'buy', 'bought', 'acquisition', 'exercise'])
                
                if is_sale:
                    insider_sell += 1
                    if any(title in position for title in ['ceo', 'cfo', 'coo', 'president', 'director', 'officer']):
                        executive_sells += 1
                    if date_str:
                        try:
                            sell_dates.append(datetime.strptime(date_str.split(' ')[0], '%Y-%m-%d'))
                        except:
                            pass
                elif is_buy:
                    insider_buy += 1
            
            # Cluster Selling Detection
            is_cluster_selling = False
            if executive_sells >= 3 and len(sell_dates) >= 3:
                sell_dates.sort()
                for i in range(len(sell_dates) - 2):
                    if (sell_dates[i+2] - sell_dates[i]).days <= 14:
                        is_cluster_selling = True
                        break
            
            # Classify
            if not discretionary_txs:
                ins_activity = "No Activity"
            elif is_cluster_selling:
                ins_activity = "Cluster Selling"
            elif insider_buy > insider_sell and insider_buy >= 2:
                ins_activity = "Net Buying"
            elif insider_sell > insider_buy and insider_sell >= 6:
                ins_activity = "Heavy Selling"
            elif insider_sell > insider_buy:
                ins_activity = "Mixed/Minor Selling"
            else:
                ins_activity = "No Activity"
        
        try:
            sentiment_data = Sentiment(
                news_sentiment_label=sentiment_label,
                news_sentiment_score=sentiment_score,
                news_article_count=news_art_count
                # v6.5: insider_activity removed from scoring - MSPR now display-only
            )
        except TypeError as e:
            logger.error(f"Sentiment Instantiation Failed: {e}. LIKELY STALE SERVER STATE.")
            raise HTTPException(status_code=500, detail=f"Server State Mismatch (Restart Backend): {e}")
            
        # --- Projections ---
        # Simulation returns p50 list. We need the FINAL P50 value.
        p50_val = sim_result.get('p50', [])[-1] if sim_result.get('p50') else current_price
        
        # Risk/Reward
        # Gain to P90: P90_final - Current
        # Loss to P10: Current - P10_final
        p90_val = sim_result.get('p90', [])[-1] if sim_result.get('p90') else current_price
        p10_val = sim_result.get('p10', [])[-1] if sim_result.get('p10') else current_price
        
        gain_p90 = max(0, p90_val - current_price)
        loss_p10 = max(0, current_price - p10_val)
        
        # v5.0 Projections
        p50_final = sim_result.get('p50', [])[-1] if sim_result.get('p50') else current_price
        p90_final = sim_result.get('p90', [])[-1] if sim_result.get('p90') else current_price
        p10_final = sim_result.get('p10', [])[-1] if sim_result.get('p10') else current_price
        
        proj_data = Projections(
            monte_carlo_p50=p50_final,
            monte_carlo_p90=p90_final,
            monte_carlo_p10=p10_final,
            current_price=current_price
        )

        # 4. Evaluate
        stock_data = StockData(
            ticker=ticker,
            beta=beta,
            dividend_yield=div_yield_pct,
            market_bull_regime=regime["bull_regime"],
            fundamentals=fund_data,
            technicals=tech_data,
            sentiment=sentiment_data,
            projections=proj_data
        )
        
        scorer = VinSightScorer()
        score_result = scorer.evaluate(stock_data)

        # 5. Format Output for Frontend (Backward Compatible wrapper)
        rating_color_map = {
            "Strong Buy": "emerald",
            "Buy": "emerald",
            "Hold": "yellow",
            "Sell": "red"
        }
        
        color = rating_color_map.get(score_result.rating, "yellow")
        
        # Build detailed score explanation for transparency
        fund_score = score_result.breakdown.get('Fundamentals', 0)
        tech_score = score_result.breakdown.get('Technicals', 0)
        sent_score = score_result.breakdown.get('Sentiment', 0)
        proj_score = score_result.breakdown.get('Projections', 0)
        
        # Generate human-readable explanations for each pillar
        fund_explanation = []
        benchmarks = scorer._get_benchmarks(active_sector)
        sector_pe = benchmarks.get('pe_median', 20.0)

        if pe and pe > 0:
            if pe < 15:
                fund_explanation.append(f"P/E of {pe:.1f} is undervalued (Graham value)")
            elif pe < sector_pe:
                fund_explanation.append(f"P/E of {pe:.1f} is below sector median ({sector_pe:.0f})")
            else:
                fund_explanation.append(f"P/E of {pe:.1f} exceeds sector median ({sector_pe:.0f})")
        if peg is not None and peg > 0:
            if peg < 1.0:
                fund_explanation.append(f"PEG of {peg:.2f} suggests undervaluation")
            elif peg > 1.5:
                fund_explanation.append(f"PEG of {peg:.2f} indicates growth premium")
        if inst_own > 70:
            fund_explanation.append(f"Strong institutional backing ({inst_own:.0f}%)")
        
        # New v6.0 Fundamentals Factors
        margin_target = benchmarks.get('margin_healthy', 0.12)
        if profit_margin:
            if profit_margin >= margin_target:
                fund_explanation.append(f"Healthy margins ({profit_margin*100:.1f}%) vs sector ({margin_target*100:.0f}%)")
            else:
                fund_explanation.append(f"Margins ({profit_margin*100:.1f}%) trail sector ({margin_target*100:.0f}%)")
        
        debt_target = benchmarks.get('debt_safe', 1.0)
        if debt_to_equity:
            if debt_to_equity <= debt_target:
                fund_explanation.append(f"Prudent debt level ({debt_to_equity:.1f}x) vs peer max ({debt_target:.1f}x)")
            else:
                fund_explanation.append(f"Elevated debt ({debt_to_equity:.1f}x) vs peer max ({debt_target:.1f}x)")
        
        tech_explanation = []
        tech_explanation.append(f"Momentum: {momentum}")
        tech_explanation.append(f"RSI: {rsi:.0f}")
        if vol_trend != "Weak/Mixed":
            tech_explanation.append(f"Volume confirms: {vol_trend}")
        else:
            tech_explanation.append("Volume pattern is mixed")
        
        sent_explanation = []
        sent_explanation.append(f"News sentiment: {sentiment_label}")
        
        # Format Source safely
        if sentiment_result:
            raw_source = sentiment_result.get('source', 'Unknown')
            source_display = {
                "finnhub": "Finnhub (Tier 1)",
                "yfinance": "Yahoo Finance (Tier 2)",
                "textblob": "TextBlob (Fallback)"
            }.get(raw_source, raw_source)
            sent_explanation.append(f"Source: {source_display}")
        else:
            sent_explanation.append("Source: Unknown (Fallback)")
             
        sent_explanation.append(f"Insider activity: {ins_activity}")
        if news_art_count < 3:
            sent_explanation.append("Low volume penalty: < 3 articles (-2pts)")
        elif news_art_count < 5:
            sent_explanation.append("Low volume penalty: < 5 articles (-1pt)")
        
        proj_explanation = []
        upside_pct = ((p50_final - current_price) / current_price) * 100 if current_price > 0 else 0
        proj_explanation.append(f"Quarterly P50 Target: ${p50_final:.2f} ({'+' if upside_pct > 0 else ''}{upside_pct:.1f}%)")
        
        if p90_final > current_price:
            bull_upside = ((p90_final - current_price) / current_price) * 100
            proj_explanation.append(f"Bull Case (P90): ${p90_final:.2f} (+{bull_upside:.1f}%)")
            
        if p10_final < current_price:
            bear_downside = ((current_price - p10_final) / current_price) * 100
            proj_explanation.append(f"Bear Case (P10): ${p10_final:.2f} (-{bear_downside:.1f}%)")
            
        # VaR
        var_risk = risk.get('var_95', 0)
        var_amt = abs(var_risk * current_price)
        proj_explanation.append(f"Daily Value at Risk (95%): ${var_amt:.2f}")
        
        score_explanation = {
            "fundamentals": {
                "score": f"{fund_score}/70",
                "factors": fund_explanation
            },
            "sentiment": {
                "score": f"{sent_score}/10",
                "factors": sent_explanation
            },
            "projections": {
                "score": f"{proj_score}/10",
                "factors": proj_explanation
            },
            "technicals": {
                "score": f"{tech_score}/10",
                "factors": tech_explanation
            }
        }
        
        # Refined Outlooks
        short_term_outlook = [
            f"Momentum is {momentum.lower()}",
            f"RSI ({rsi:.0f}) is {'oversold' if rsi < 30 else 'overbought' if rsi > 70 else 'neutral'}",
            f"Volume {vol_trend.lower()}"
        ]
        
        medium_term_outlook = [
            f"VinSight Rating: {score_result.rating}",
            f"Market Regime: {'Bullish' if regime['bull_regime'] else 'Defensive/Bearish'}",
            f"Sector: {active_sector}"
        ]
        
        long_term_outlook = [
            f"Valuation: {'Reasonable' if pe < 25 else 'Premium'}",
            f"Projected Upside: {upside_pct:.1f}%",
            f"Institutional Quality: {'High' if inst_own > 60 else 'Low/Moderate'}"
        ]

        # Generate AI Summary using Groq
        try:
            groq = get_groq_analyzer()
            score_data_for_ai = {
                'total_score': score_result.total_score,
                'rating': score_result.rating,
                'fundamentals_score': score_result.breakdown.get('Quality Score', 0),
                'timing_score': score_result.breakdown.get('Timing Score', 0),
                'breakdown': score_result.details,
                'outlook_context': {
                    'short_term': short_term_outlook,
                    'medium_term': medium_term_outlook,
                    'long_term': long_term_outlook
                },
                'modifications': score_result.modifications,
                'missing_data': score_result.missing_data
            }
            ai_summary = groq.generate_score_summary(ticker, score_data_for_ai)
        except Exception as e:
            logger.warning(f"AI summary generation failed: {e}")
            ai_summary = score_result.verdict_narrative
        
        ai_analysis_response = {
            "rating": score_result.rating.upper(), # BUY/SELL
            "color": color,
            "score": score_result.total_score,
            "justification": ai_summary,  # Use AI-generated summary
            "raw_breakdown": score_result.breakdown,
            "modifications": score_result.modifications,
            "missing_data": score_result.missing_data,
            "score_explanation": score_explanation,
            "details": score_result.details, # New structured breakdown for UI
            "outlook_context": score_data_for_ai['outlook_context'] # Expose deterministic outlooks
        }

        # Prepare SMA dict for frontend
        sma_data = {
            "sma_5": latest_ind.get('SMA_5'),
            "sma_10": latest_ind.get('SMA_10'),
            "sma_50": latest_ind.get('SMA_50'),
            "sma_200": latest_ind.get('SMA_200')
        }
        
        return {
            "indicators": indicators, 
            "risk": risk, 
            "sentiment": sentiment_result,  # Can be None
            "ai_analysis": ai_analysis_response, 
            "sma": sma_data,
            "sector_info": {
                "detected": detected_sector,
                "active": active_sector,
                "is_override": sector_override is not None and sector_override != "Auto"
            },
            # CONSOLIDATED DATA (For Frontend Optimization)
            "simulation": sim_result,
            "institutional": institutional,
            "news": news,
            "history": history, # Optionally returned, frontend can use to init chart
            "stock_details": fundamentals_info # Consolidated: Return raw info too
        }
    except Exception as e:
        logger.exception(f"Error in technical analysis for {ticker}")
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.")

@router.get("/institutional/{ticker}")
def get_institutional_data(ticker: str):
    try:
        return finance.get_institutional_holders(ticker)
    except Exception as e:
        logger.error(f"Error fetching institutional data for {ticker}: {e}")
        # Return empty structure rather than 500 to keep UI alive
        return {"holders": [], "total_institutional": 0, "status": "Error/Rate Limited"}

@router.get("/simulation/{ticker}")
def get_simulation(ticker: str):
    try:
        from services import yahoo_client
        import pandas as pd
        try:
            history = finance.get_stock_history(ticker, period="1y")
        except Exception as e:
            if "Too Many Requests" in str(e) or "Rate limited" in str(e) or "429" in str(e):
                logger.info(f"Using yahoo_client fallback for {ticker} simulation history")
                chart = yahoo_client.get_chart_data(ticker, interval="1d", range_="1y")
                if chart and chart.get("timestamp"):
                    timestamps = chart["timestamp"]
                    quotes = chart.get("indicators", {}).get("quote", [{}])[0]
                    history = []
                    for i, ts in enumerate(timestamps):
                        close_val = quotes.get("close", [None])[i] if i < len(quotes.get("close", [])) else None
                        if close_val is None: continue
                        history.append({
                            "Date": pd.Timestamp(ts, unit='s').isoformat(),
                            "Close": close_val,
                            "Open": quotes.get("open", [None])[i] or close_val,
                            "High": quotes.get("high", [None])[i] or close_val,
                            "Low": quotes.get("low", [None])[i] or close_val,
                            "Volume": quotes.get("volume", [None])[i] or 0
                        })
                    if not history: raise e
                else:
                    raise e
            else:
                raise e
                
        sim_result = simulation.run_monte_carlo(history)
        
        # Also fetch analyst targets for combined response
        try:
            analyst_targets = finance.get_analyst_targets(ticker)
        except:
            analyst_targets = {}
            
        sim_result["analyst_targets"] = analyst_targets
        
        return sim_result
    except Exception as e:
        logger.error(f"Error in simulation for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/{ticker}")
def get_sentiment(ticker: str):
    """
    Dedicated endpoint for sentiment analysis (lazy-loaded).
    """
    try:
        try:
            news = finance.get_news(ticker)
        except Exception:
            # Fallback to yahoo_client news if possible
            from services import yahoo_client
            news = yahoo_client.get_news(ticker)
            
        sentiment_result = analysis.calculate_news_sentiment(news, deep_analysis=True, ticker=ticker)
        return sentiment_result
    except Exception as e:
        logger.error(f"Error in sentiment for {ticker}: {e}")
        return {"label": "Neutral", "score": 0, "confidence": 0, "article_count": 0, "status": "Error/Rate Limited"}
