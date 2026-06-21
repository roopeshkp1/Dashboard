#!/usr/bin/env python3
"""
Fetch NSE indices and stocks data from Yahoo Finance.
Handles rate limiting and data caching to avoid Yahoo Finance API limits.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import time
import os
from datetime import datetime, timedelta
from pathlib import Path

# NSE Indices (with .NS suffix for yfinance)
NSE_INDICES = {
    '^NSEI': 'NIFTY 50',
    '^NSEBANK': 'NIFTY BANK',
    '^NSMIDCAP': 'NIFTY MIDCAP 50',
    '^NSEIT': 'NIFTY IT',
    '^NSEINFRA': 'NIFTY INFRASTRUCTURE',
    '^NSEPHARMA': 'NIFTY PHARMA',
    '^NSEAUTO': 'NIFTY AUTO',
    '^NSEPSE': 'NIFTY PSE',
    '^NSEENERGY': 'NIFTY ENERGY',
    '^NSEMET': 'NIFTY METALS',
}

# Major NSE Stocks (sample list - can be expanded)
NSE_STOCKS = [
    'TCS.NS', 'INFY.NS', 'WIPRO.NS', 'RELIANCE.NS', 'HDFC.NS',
    'ICICIBANK.NS', 'AXISBANK.NS', 'BAJAJFINSV.NS', 'MARUTI.NS', 'TATAMOTORS.NS',
    'ASIANPAINT.NS', 'HINDUNILVR.NS', 'NESTLEIND.NS', 'ITC.NS', 'BRITANNIA.NS',
    'LT.NS', 'ULTRACEMCO.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'HDFCBANK.NS',
    'SUNPHARMA.NS', 'APOLLOHOSP.NS', 'DIVI.NS', 'DRREDDY.NS', 'LUPIN.NS',
    'POWERGRID.NS', 'NTPC.NS', 'COALINDIA.NS', 'SBILIFE.NS', 'ONGC.NS',
    'BAJAJ-AUTO.NS', 'TATASTEEL.NS', 'HINDALCO.NS', 'JSWSTEEL.NS', 'VEDL.NS',
    'ADANIPORTS.NS', 'ADANIGREEN.NS', 'ADANITRANS.NS', 'TITAN.NS', 'MCDOWELL-N.NS',
]

class YFinanceRateLimitHandler:
    """Handle rate limiting for Yahoo Finance API"""
    def __init__(self, delay=0.5):
        self.delay = delay
        self.last_request_time = 0
    
    def wait(self):
        """Wait before making next request to avoid rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()

def fetch_indices_data(rate_limiter):
    """Fetch NSE indices data"""
    indices_data = {}
    
    print("Fetching NSE Indices...")
    for symbol, name in NSE_INDICES.items():
        try:
            rate_limiter.wait()
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d')
            info = ticker.info
            
            if not hist.empty:
                latest = hist.iloc[-1]
                indices_data[symbol] = {
                    'name': name,
                    'symbol': symbol,
                    'price': float(latest['Close']),
                    'open': float(latest['Open']),
                    'high': float(latest['High']),
                    'low': float(latest['Low']),
                    'volume': int(latest['Volume']) if 'Volume' in latest and latest['Volume'] > 0 else 0,
                    'change': 0,  # Will calculate below
                    'change_pct': 0,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Calculate change
                if len(hist) > 1:
                    prev_close = hist.iloc[-2]['Close']
                    change = latest['Close'] - prev_close
                    change_pct = (change / prev_close * 100) if prev_close != 0 else 0
                    indices_data[symbol]['change'] = float(change)
                    indices_data[symbol]['change_pct'] = float(change_pct)
            
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name} - Error: {str(e)}")
    
    return indices_data

def fetch_stocks_data(rate_limiter):
    """Fetch NSE stocks data with 1-year history for calculations"""
    stocks_data = {}
    
    print("\nFetching NSE Stocks...")
    for symbol in NSE_STOCKS:
        try:
            rate_limiter.wait()
            ticker = yf.Ticker(symbol)
            
            # Get 1 year of history for EMA and performance calculations
            hist = ticker.history(period='1y')
            
            if len(hist) > 0:
                latest = hist.iloc[-1]
                stock_name = symbol.replace('.NS', '')
                
                stocks_data[symbol] = {
                    'symbol': stock_name,
                    'price': float(latest['Close']),
                    'open': float(latest['Open']),
                    'high': float(latest['High']),
                    'low': float(latest['Low']),
                    'volume': int(latest['Volume']) if 'Volume' in latest and latest['Volume'] > 0 else 0,
                    'change': 0,
                    'change_pct': 0,
                    'timestamp': datetime.now().isoformat(),
                    'history': hist.to_dict('list'),  # Store full history
                }
                
                # Calculate change from previous close
                if len(hist) > 1:
                    prev_close = hist.iloc[-2]['Close']
                    change = latest['Close'] - prev_close
                    change_pct = (change / prev_close * 100) if prev_close != 0 else 0
                    stocks_data[symbol]['change'] = float(change)
                    stocks_data[symbol]['change_pct'] = float(change_pct)
                
                print(f"  ✓ {stock_name}")
        except Exception as e:
            print(f"  ✗ {symbol.replace('.NS', '')} - Error: {str(e)}")
    
    return stocks_data

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return None
    
    prices_array = np.array(prices[-period*2:])  # Use extra data for accuracy
    ema = prices_array.copy().astype(float)
    multiplier = 2 / (period + 1)
    
    for i in range(1, len(ema)):
        ema[i] = (prices_array[i] * multiplier) + (ema[i-1] * (1 - multiplier))
    
    return float(ema[-1])

def calculate_market_cap(price, shares_outstanding):
    """
    Calculate market cap. 
    Note: Yahoo Finance may not have reliable shares data for all NSE stocks.
    Using a simplified estimate based on typical Indian stock metrics.
    """
    # For NSE stocks, using a simplified approach
    # In production, use a dedicated NSE API or database for accurate market cap
    return price * shares_outstanding

def calculate_three_month_performance(hist):
    """Calculate 3-month performance percentage"""
    try:
        if len(hist) < 60:  # Need at least 60 days
            return None
        
        # Get closing prices from last 3 months
        close_prices = hist['Close'].tail(60).values
        
        if len(close_prices) < 2:
            return None
        
        start_price = close_prices[0]
        end_price = close_prices[-1]
        
        if start_price == 0:
            return None
        
        performance = ((end_price - start_price) / start_price) * 100
        return float(performance)
    except:
        return None

def fetch_all_data(output_dir='data'):
    """Main function to fetch all data"""
    rate_limiter = YFinanceRateLimitHandler(delay=0.5)
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    print("=" * 60)
    print("NSE TRADING DASHBOARD - DATA FETCH")
    print("=" * 60)
    
    # Fetch data
    indices = fetch_indices_data(rate_limiter)
    stocks = fetch_stocks_data(rate_limiter)
    
    # Prepare output
    output_data = {
        'indices': indices,
        'stocks': stocks,
        'timestamp': datetime.now().isoformat(),
    }
    
    # Save raw data
    with open(os.path.join(output_dir, 'nse_raw_data.json'), 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print("\n✓ Data fetch completed!")
    print(f"  Indices: {len(indices)}")
    print(f"  Stocks: {len(stocks)}")
    print(f"  Saved to: {output_dir}/nse_raw_data.json")
    
    return output_data

if __name__ == '__main__':
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else 'data'
    fetch_all_data(output_dir)
