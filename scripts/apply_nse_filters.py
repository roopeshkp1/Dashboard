#!/usr/bin/env python3
"""
Apply NSE filter criteria to stocks data.

Filter Criteria:
  1. EMA-based Filter:
     - Price > ₹30
     - EMA(20) > EMA(50) > EMA(200) (uptrend confirmation)
     - Market Cap > ₹800 crore

  2. Performance-based Filter:
     - Price > ₹30
     - Market Cap > ₹800 crore
     - 3-month performance > 20%
"""

import json
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return None
    
    prices_array = np.array(prices[-period*3:])  # Use extra data for accuracy
    ema = prices_array.copy().astype(float)
    multiplier = 2 / (period + 1)
    
    for i in range(1, len(ema)):
        ema[i] = (prices_array[i] * multiplier) + (ema[i-1] * (1 - multiplier))
    
    return float(ema[-1])

def get_market_cap_estimate(price, symbol):
    """
    Estimate market cap for NSE stocks.
    Note: This is a simplified approach. In production, use:
    - NSE API (www.nseindia.com)
    - Financial databases (Moneycontrol, BSE website)
    - Dedicated stock APIs
    
    For now, using typical share counts for major companies.
    """
    # Typical share counts (in crores) for major NSE stocks - UPDATE based on actual data
    share_counts = {
        'TCS': 450,
        'INFY': 350,
        'WIPRO': 300,
        'RELIANCE': 250,
        'HDFC': 150,
        'ICICIBANK': 380,
        'AXISBANK': 320,
        'BAJAJFINSV': 120,
        'MARUTI': 60,
        'TATAMOTORS': 450,
        'ASIANPAINT': 150,
        'HINDUNILVR': 200,
        'NESTLEIND': 40,
        'ITC': 600,
        'BRITANNIA': 50,
        'LT': 200,
        'ULTRACEMCO': 100,
        'SBIN': 700,
        'KOTAKBANK': 180,
        'HDFCBANK': 280,
        'SUNPHARMA': 180,
        'APOLLOHOSP': 100,
        'DIVI': 150,
        'DRREDDY': 120,
        'LUPIN': 180,
        'POWERGRID': 800,
        'NTPC': 1000,
        'COALINDIA': 1100,
        'SBILIFE': 200,
        'ONGC': 850,
        'BAJAJ-AUTO': 80,
        'TATASTEEL': 200,
        'HINDALCO': 250,
        'JSWSTEEL': 280,
        'VEDL': 500,
        'ADANIPORTS': 200,
        'ADANIGREEN': 250,
        'ADANITRANS': 300,
        'TITAN': 100,
        'MCDOWELL-N': 100,
    }
    
    stock_code = symbol.replace('.NS', '')
    share_count = share_counts.get(stock_code, 150)  # Default to 150 crore shares
    market_cap = (price * share_count) / 1e7  # Convert to crores
    return market_cap

def calculate_three_month_performance(hist_data):
    """Calculate 3-month performance percentage"""
    try:
        if not hist_data or 'Close' not in hist_data:
            return None
        
        closes = hist_data['Close']
        if len(closes) < 60:  # Need at least 60 days (~3 months)
            return None
        
        # Get last 3 months of data
        close_prices = closes[-60:]
        
        start_price = close_prices[0]
        end_price = close_prices[-1]
        
        if start_price == 0:
            return None
        
        performance = ((end_price - start_price) / start_price) * 100
        return float(performance)
    except:
        return None

def calculate_volume_atr(hist_data):
    """Calculate ATR (Average True Range) and other technical indicators"""
    try:
        if not hist_data or 'Close' not in hist_data:
            return {'atr': None, 'avg_volume': None}
        
        df = pd.DataFrame(hist_data)
        
        if len(df) < 14:
            return {'atr': None, 'avg_volume': None}
        
        # Calculate ATR
        df['H-L'] = df['High'] - df['Low']
        df['H-C'] = abs(df['High'] - df['Close'].shift())
        df['L-C'] = abs(df['Low'] - df['Close'].shift())
        df['TR'] = df[['H-L', 'H-C', 'L-C']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        atr = float(df['ATR'].iloc[-1]) if not pd.isna(df['ATR'].iloc[-1]) else None
        avg_volume = float(df['Volume'].tail(20).mean()) if 'Volume' in df.columns else None
        
        return {'atr': atr, 'avg_volume': avg_volume}
    except:
        return {'atr': None, 'avg_volume': None}

def apply_filter_1(stocks_data):
    """
    Filter 1: EMA-based Uptrend
    - Price > ₹30
    - EMA(20) > EMA(50) > EMA(200)
    - Market Cap > ₹800 crore
    """
    filtered = []
    
    for symbol, stock in stocks_data.items():
        try:
            price = stock['price']
            
            # Condition 1: Price > ₹30
            if price <= 30:
                continue
            
            # Get historical data
            if 'history' not in stock or not stock['history']:
                continue
            
            hist = stock['history']
            closes = hist.get('Close', [])
            
            if len(closes) < 200:  # Need at least 200 days for EMA(200)
                continue
            
            # Calculate EMAs
            ema20 = calculate_ema(closes, 20)
            ema50 = calculate_ema(closes, 50)
            ema200 = calculate_ema(closes, 200)
            
            if None in [ema20, ema50, ema200]:
                continue
            
            # Condition 2: EMA(20) > EMA(50) > EMA(200)
            if not (ema20 > ema50 > ema200):
                continue
            
            # Condition 3: Market Cap > ₹800 crore
            market_cap = get_market_cap_estimate(price, symbol)
            if market_cap < 800:
                continue
            
            # Calculate additional metrics
            tech_indicators = calculate_volume_atr(hist)
            three_month_perf = calculate_three_month_performance(hist)
            
            filtered.append({
                'symbol': stock['symbol'],
                'price': price,
                'market_cap_crore': market_cap,
                'ema20': ema20,
                'ema50': ema50,
                'ema200': ema200,
                'change_pct': stock.get('change_pct', 0),
                'volume': stock.get('volume', 0),
                'atr': tech_indicators.get('atr'),
                'avg_volume': tech_indicators.get('avg_volume'),
                'performance_3m': three_month_perf,
                'filter_match': 'EMA Uptrend',
            })
        except Exception as e:
            continue
    
    return filtered

def apply_filter_2(stocks_data):
    """
    Filter 2: Performance-based
    - Price > ₹30
    - Market Cap > ₹800 crore
    - 3-month performance > 20%
    """
    filtered = []
    
    for symbol, stock in stocks_data.items():
        try:
            price = stock['price']
            
            # Condition 1: Price > ₹30
            if price <= 30:
                continue
            
            # Condition 2: Market Cap > ₹800 crore
            market_cap = get_market_cap_estimate(price, symbol)
            if market_cap < 800:
                continue
            
            # Get historical data for 3-month performance
            if 'history' not in stock or not stock['history']:
                continue
            
            hist = stock['history']
            
            # Condition 3: 3-month performance > 20%
            three_month_perf = calculate_three_month_performance(hist)
            if three_month_perf is None or three_month_perf <= 20:
                continue
            
            # Calculate additional metrics
            closes = hist.get('Close', [])
            ema20 = calculate_ema(closes, 20) if len(closes) >= 20 else None
            ema50 = calculate_ema(closes, 50) if len(closes) >= 50 else None
            tech_indicators = calculate_volume_atr(hist)
            
            filtered.append({
                'symbol': stock['symbol'],
                'price': price,
                'market_cap_crore': market_cap,
                'performance_3m': three_month_perf,
                'ema20': ema20,
                'ema50': ema50,
                'change_pct': stock.get('change_pct', 0),
                'volume': stock.get('volume', 0),
                'atr': tech_indicators.get('atr'),
                'avg_volume': tech_indicators.get('avg_volume'),
                'filter_match': 'High Performance',
            })
        except Exception as e:
            continue
    
    return filtered

def apply_all_filters(raw_data_path='data/nse_raw_data.json', output_dir='data'):
    """Apply all filters to NSE stocks"""
    
    print("\n" + "=" * 60)
    print("APPLYING NSE FILTERS")
    print("=" * 60)
    
    # Load raw data
    with open(raw_data_path, 'r') as f:
        raw_data = json.load(f)
    
    stocks_data = raw_data.get('stocks', {})
    indices_data = raw_data.get('indices', {})
    
    # Apply filters
    print("\nApplying Filter 1: EMA-based Uptrend...")
    filter1_results = apply_filter_1(stocks_data)
    print(f"  Found {len(filter1_results)} stocks")
    
    print("\nApplying Filter 2: Performance-based...")
    filter2_results = apply_filter_2(stocks_data)
    print(f"  Found {len(filter2_results)} stocks")
    
    # Prepare output
    filtered_data = {
        'timestamp': datetime.now().isoformat(),
        'indices': indices_data,
        'filters': {
            'filter_1_ema_uptrend': {
                'name': 'EMA Uptrend (Price > ₹30, EMA20 > EMA50 > EMA200, Market Cap > ₹800cr)',
                'count': len(filter1_results),
                'stocks': sorted(filter1_results, key=lambda x: x['ema20'] - x['ema200'], reverse=True)
            },
            'filter_2_performance': {
                'name': 'High Performance (Price > ₹30, Market Cap > ₹800cr, 3M Perf > 20%)',
                'count': len(filter2_results),
                'stocks': sorted(filter2_results, key=lambda x: x['performance_3m'], reverse=True)
            }
        }
    }
    
    # Save filtered data
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'nse_filtered_data.json'), 'w') as f:
        json.dump(filtered_data, f, indent=2)
    
    print("\n✓ Filters applied successfully!")
    print(f"  Output: {output_dir}/nse_filtered_data.json")
    
    return filtered_data

if __name__ == '__main__':
    import sys
    raw_data_path = sys.argv[1] if len(sys.argv) > 1 else 'data/nse_raw_data.json'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'data'
    apply_all_filters(raw_data_path, output_dir)
