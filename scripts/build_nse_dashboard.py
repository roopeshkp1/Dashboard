#!/usr/bin/env python3
"""
Main orchestrator to build NSE trading dashboard.
Coordinates fetching data, applying filters, and generating output JSON.
"""

import os
import sys
import json
from pathlib import Path

def run_nse_pipeline(output_dir='data'):
    """Run the complete NSE dashboard data pipeline"""
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    print("\n" + "=" * 70)
    print("NSE TRADING DASHBOARD - BUILD PIPELINE")
    print("=" * 70)
    
    # Step 1: Fetch NSE data
    print("\n[STEP 1] Fetching NSE data from Yahoo Finance...")
    print("-" * 70)
    
    try:
        from fetch_nse_data import fetch_all_data
        raw_data = fetch_all_data(output_dir)
        print("✓ NSE data fetch completed")
    except Exception as e:
        print(f"✗ Error fetching NSE data: {str(e)}")
        return False
    
    # Step 2: Apply filters
    print("\n[STEP 2] Applying filter criteria...")
    print("-" * 70)
    
    try:
        from apply_nse_filters import apply_all_filters
        filtered_data = apply_all_filters(
            os.path.join(output_dir, 'nse_raw_data.json'),
            output_dir
        )
        print("✓ Filters applied successfully")
    except Exception as e:
        print(f"✗ Error applying filters: {str(e)}")
        return False
    
    # Step 3: Generate dashboard JSON
    print("\n[STEP 3] Generating dashboard data...")
    print("-" * 70)
    
    try:
        dashboard_data = {
            'version': '1.0',
            'title': 'NSE Trading Dashboard',
            'description': 'Indian market trading dashboard with EMA and performance filters',
            'indices': filtered_data['indices'],
            'filter_1_ema_uptrend': filtered_data['filters']['filter_1_ema_uptrend'],
            'filter_2_performance': filtered_data['filters']['filter_2_performance'],
            'metadata': {
                'last_updated': filtered_data['timestamp'],
                'total_indices': len(filtered_data['indices']),
                'total_stocks_scanned': len(raw_data.get('stocks', {})),
            }
        }
        
        # Save dashboard data
        dashboard_file = os.path.join(output_dir, 'nse_dashboard.json')
        with open(dashboard_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        
        print(f"✓ Dashboard data generated: {dashboard_file}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("DASHBOARD BUILD SUMMARY")
        print("=" * 70)
        print(f"Indices tracked: {dashboard_data['metadata']['total_indices']}")
        print(f"Stocks scanned: {dashboard_data['metadata']['total_stocks_scanned']}")
        print(f"Filter 1 matches: {dashboard_data['filter_1_ema_uptrend']['count']}")
        print(f"Filter 2 matches: {dashboard_data['filter_2_performance']['count']}")
        print(f"Last updated: {dashboard_data['metadata']['last_updated']}")
        print("=" * 70)
        
        return True
    
    except Exception as e:
        print(f"✗ Error generating dashboard: {str(e)}")
        return False

if __name__ == '__main__':
    output_dir = sys.argv[1] if len(sys.argv) > 1 else 'data'
    success = run_nse_pipeline(output_dir)
    sys.exit(0 if success else 1)
