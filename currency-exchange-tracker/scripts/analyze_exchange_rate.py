'''
---
title: "analyze_exchange_rate.py"
name: "currency-exchange-tracker"
description: "Analyze exchange rate trends from historical CSV data and provide optimal exchange timing recommendations based on past N-day comparisons."
version: "v2.0.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T16:45:00+08:00"
fixes: []
auth_config:
  provider: yahoo_finance
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/scripts/analyze_exchange_rate.py"
  github_path: "currency-exchange-tracker/scripts/analyze_exchange_rate.py"
---
'''

# -*- coding: utf-8 -*-

import argparse
import csv
from pathlib import Path
from datetime import datetime, timedelta
import sys

def analyze_trend(csv_path, days=7):
    """Analyze exchange rate trend for past N days."""
    try:
        if not Path(csv_path).exists():
            print(f"Error: {csv_path} not found")
            sys.exit(1)
    except Exception as e:
        print(f"Error checking file path: {e}")
        sys.exit(1)

    data = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    except csv.Error as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Error decoding file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error reading file: {e}")
        sys.exit(1)

    if len(data) == 0:
        print("Error: No data in CSV")
        sys.exit(1)

    try:
        data.sort(key=lambda x: x['date'], reverse=True)
        recent_data = data[:days]
        recent_data.reverse()
    except KeyError as e:
        print(f"Error: Missing required column in CSV: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing data: {e}")
        sys.exit(1)

    try:
        rates = [float(row['hkd_to_cny']) for row in recent_data]
    except (ValueError, KeyError) as e:
        print(f"Error parsing rate data: {e}")
        sys.exit(1)

    current_rate = rates[-1]
    avg_rate = sum(rates) / len(rates)
    min_rate = min(rates)
    max_rate = max(rates)

    if len(rates) >= 2:
        if rates[-1] > rates[-2]:
            trend = "Rising (HKD strengthening)"
            trend_icon = "Trend: Rising (HKD strengthening)"
        elif rates[-1] < rates[-2]:
            trend = "Falling (HKD weakening)"
            trend_icon = "Trend: Falling (HKD weakening)"
        else:
            trend = "Stable"
            trend_icon = "Trend: Stable"
    else:
        trend = "Insufficient data"
        trend_icon = "Trend: Insufficient data"

    diff_percent = ((current_rate - avg_rate) / avg_rate) * 100

    if diff_percent > 0.5:
        recommendation = f"RECOMMENDATION: Good time to exchange HKD->CNY\n   (Current rate is {diff_percent:.2f}% better than {days}-day average)"
        rec_icon = f"Recommendation: Good time to exchange HKD->CNY\n   (Current rate is {diff_percent:.2f}% better than {days}-day average)"
    elif diff_percent < -0.5:
        recommendation = f"RECOMMENDATION: May not be optimal time to exchange HKD->CNY\n   (Current rate is {abs(diff_percent):.2f}% worse than {days}-day average)"
        rec_icon = f"Recommendation: May not be optimal time to exchange HKD->CNY\n   (Current rate is {abs(diff_percent):.2f}% worse than {days}-day average)"
    else:
        recommendation = f"RECOMMENDATION: Neutral, can exchange if needed\n   (Current rate is within +/-0.5% of {days}-day average)"
        rec_icon = f"Recommendation: Neutral, can exchange if needed\n   (Current rate is within +/-0.5% of {days}-day average)"

    print(f"Exchange Rate Analysis (Past {days} Days)")
    print("=" * 50)
    print(f"Current HKD/CNY Rate: {current_rate:.4f}")
    print(f"{days}-Day Average: {avg_rate:.4f}")
    print(f"{days}-Day Min: {min_rate:.4f}")
    print(f"{days}-Day Max: {max_rate:.4f}")
    print()
    print(recommendation)
    print(trend_icon)
    print()
    print(f"Detailed Data (Past {days} Days):")
    for row in recent_data:
        print(f"  {row['date']}: HKD->CNY {row['hkd_to_cny']}, Source: {row['source']}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze exchange rate trends')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    args = parser.parse_args()

    csv_path = Path(__file__).parent.parent / 'assets' / 'exchange_rate_history.csv'
    analyze_trend(str(csv_path), args.days)
