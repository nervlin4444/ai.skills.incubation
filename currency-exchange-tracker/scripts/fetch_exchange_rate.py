'''
---
title: "fetch_exchange_rate.py"
name: "currency-exchange-tracker"
description: "Fetch real-time HKD/CNY exchange rates from multiple sources (Yahoo Finance, Investing.com). Supports HKD-to-CNY and CNY-to-HKD directions."
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
  local_path: "{baseDir}/scripts/fetch_exchange_rate.py"
  github_path: "currency-exchange-tracker/scripts/fetch_exchange_rate.py"
---
'''

# -*- coding: utf-8 -*-

import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Config-driven: API endpoints and settings
CONFIG = {
    "timeout": 10,
    "max_retries": 3,
    "sources": {
        "investing": {
            "url": "https://hk.investing.com/currencies/hkd-cny",
            "fallback_rate": None,
        },
        "yahoo": {
            "url": "https://query1.finance.yahoo.com/v8/finance/chart/HKDCNY=X",
            "fallback_rate": None,
        }
    }
}

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("Warning: requests library not installed. Using urllib.", file=sys.stderr)

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

def fetch_from_investing(direction):
    """Fetch exchange rate from Investing.com (web scraping fallback)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        if HAS_REQUESTS:
            response = requests.get(CONFIG["sources"]["investing"]["url"],
                                  headers=headers,
                                  timeout=CONFIG["timeout"])
            return {
                "error": "Web scraping requires additional setup (beautifulsoup4)",
                "rate": None,
                "source": "Investing.com"
            }
        elif HAS_URLLIB:
            req = Request(CONFIG["sources"]["investing"]["url"], headers=headers)
            with urlopen(req, timeout=CONFIG["timeout"]) as response:
                html = response.read().decode('utf-8')
                return {
                    "error": "Web scraping requires additional setup (beautifulsoup4)",
                    "rate": None,
                    "source": "Investing.com"
                }
    except Exception as e:
        return {
            "error": f"Failed to fetch from Investing.com: {str(e)}",
            "rate": None,
            "source": "Investing.com"
        }

def fetch_from_yahoo(direction):
    """Fetch exchange rate from Yahoo Finance API"""
    symbol = "HKDCNY=X" if direction == "hkd-to-cny" else "CNYHKD=X"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    for attempt in range(CONFIG["max_retries"]):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            if HAS_REQUESTS:
                response = requests.get(url, headers=headers, timeout=CONFIG["timeout"])
                data = response.json()
            elif HAS_URLLIB:
                req = Request(url, headers=headers)
                with urlopen(req, timeout=CONFIG["timeout"]) as response:
                    data = json.loads(response.read().decode('utf-8'))
            else:
                return {
                    "error": "No HTTP library available (install requests or urllib)",
                    "rate": None,
                    "source": "Yahoo Finance"
                }

            if data.get("chart", {}).get("error"):
                return {
                    "error": f"Yahoo Finance API error: {data['chart']['error']}",
                    "rate": None,
                    "source": "Yahoo Finance"
                }

            result = data["chart"]["result"][0]
            meta = result["meta"]

            current_rate = meta.get("regularMarketPrice")
            previous_close = meta.get("previousClose")

            if current_rate:
                change = current_rate - previous_close if previous_close else 0
                change_percent = (change / previous_close * 100) if previous_close else 0

                return {
                    "rate": round(current_rate, 4),
                    "change": round(change, 4),
                    "change_percent": round(change_percent, 2),
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "Yahoo Finance"
                }
            else:
                return {
                    "error": "No rate data in Yahoo Finance response",
                    "rate": None,
                    "source": "Yahoo Finance"
                }

        except (HTTPError, URLError) as e:
            if attempt < CONFIG["max_retries"] - 1:
                continue
            return {
                "error": f"Yahoo Finance API failed after {CONFIG['max_retries']} attempts: {str(e)}",
                "rate": None,
                "source": "Yahoo Finance"
            }
        except Exception as e:
            return {
                "error": f"Yahoo Finance unexpected error: {str(e)}",
                "rate": None,
                "source": "Yahoo Finance"
            }

    return {
        "error": "All attempts failed",
        "rate": None,
        "source": "Yahoo Finance"
    }

def fetch_exchange_rate(direction):
    """Fetch exchange rate for given direction."""
    sources = [
        ("yahoo", fetch_from_yahoo),
        ("investing", fetch_from_investing)
    ]

    errors = []

    for source_name, source_func in sources:
        try:
            data = source_func(direction)
            if data and data.get("rate") is not None:
                return data
            elif data.get("error"):
                errors.append(f"{source_name}: {data['error']}")
        except Exception as e:
            errors.append(f"{source_name}: {str(e)}")
            continue

    return {
        "error": "All sources failed",
        "details": "; ".join(errors),
        "rate": None,
        "source": None,
        "suggestion": "Please check internet connection or try again later"
    }

def main():
    parser = argparse.ArgumentParser(description="Fetch HKD/CNY exchange rate")
    parser.add_argument("--direction", choices=["hkd-to-cny", "cny-to-hkd"],
                       default="hkd-to-cny", help="Exchange direction")
    parser.add_argument("--output", choices=["json", "text"], default="json",
                       help="Output format")

    args = parser.parse_args()

    data = fetch_exchange_rate(args.direction)

    if args.output == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        if "error" in data and data["rate"] is None:
            print(f"Error: {data['error']}")
            if "details" in data:
                print(f"Details: {data['details']}")
            sys.exit(1)
        else:
            print(f"Exchange Rate ({args.direction}): {data['rate']}")
            print(f"Change: {data.get('change', 'N/A')} ({data.get('change_percent', 'N/A')}%)")
            print(f"Update Time: {data['update_time']}")
            print(f"Source: {data['source']}")

if __name__ == "__main__":
    main()
