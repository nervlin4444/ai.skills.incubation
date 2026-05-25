'''
---
title: "record_exchange_rate.py"
name: "currency-exchange-tracker"
description: "Record daily HKD/CNY exchange rates to historical CSV file. Supports automatic fetching and manual entry with force overwrite."
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
  local_path: "{baseDir}/scripts/record_exchange_rate.py"
  github_path: "currency-exchange-tracker/scripts/record_exchange_rate.py"
---
'''

# -*- coding: utf-8 -*-

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
ASSETS_DIR = SCRIPT_DIR.parent / "assets"
HISTORY_FILE = ASSETS_DIR / "exchange_rate_history.csv"

def ensure_assets_dir():
    """Ensure assets directory exists."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

def fetch_current_rates():
    """Fetch current exchange rates from fetch_exchange_rate.py."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from fetch_exchange_rate import fetch_exchange_rate

        hkd_data = fetch_exchange_rate("hkd-to-cny")
        cny_data = fetch_exchange_rate("cny-to-hkd")

        if hkd_data.get("rate") is None:
            print(f"Warning: Failed to fetch HKD->CNY: {hkd_data.get('error', 'Unknown error')}",
                  file=sys.stderr)
            return None

        if cny_data.get("rate") is None:
            print(f"Warning: Failed to fetch CNY->HKD: {cny_data.get('error', 'Unknown error')}",
                  file=sys.stderr)
            return None

        return {
            "hkd_to_cny": hkd_data["rate"],
            "cny_to_hkd": cny_data["rate"],
            "source": hkd_data.get("source", "Unknown"),
            "timestamp": datetime.now().isoformat()
        }
    except ImportError as e:
        print(f"Warning: Could not import fetch_exchange_rate: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Error fetching rates: {e}", file=sys.stderr)
        return None

def record_rate(hkd_to_cny, cny_to_hkd, source, timestamp=None, force=False):
    """Record exchange rate to CSV file."""
    ensure_assets_dir()

    if timestamp is None:
        timestamp = datetime.now().isoformat()

    date_str = datetime.now().strftime("%Y-%m-%d")
    fieldnames = ["date", "hkd_to_cny", "cny_to_hkd", "source", "timestamp"]

    file_exists = HISTORY_FILE.exists()
    rows = []
    if file_exists:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    today_exists = any(row["date"] == date_str for row in rows)

    if today_exists and not force:
        print(f"Record for {date_str} already exists. Use --force to overwrite.")
        return False

    if today_exists and force:
        rows = [row for row in rows if row["date"] != date_str]

    with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        writer.writerow({
            "date": date_str,
            "hkd_to_cny": hkd_to_cny,
            "cny_to_hkd": cny_to_hkd,
            "source": source,
            "timestamp": timestamp
        })

    action = "Overwritten" if (today_exists and force) else "Recorded"
    print(f"{action} exchange rate for {date_str}")
    print(f"   HKD->CNY: {hkd_to_cny}")
    print(f"   CNY->HKD: {cny_to_hkd}")
    print(f"   Source: {source}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Record HKD/CNY exchange rate")
    parser.add_argument("--auto", action="store_true",
                       help="Automatically fetch and record current rates")
    parser.add_argument("--hkd-to-cny", type=float,
                       help="Manual HKD to CNY rate")
    parser.add_argument("--cny-to-hkd", type=float,
                       help="Manual CNY to HKD rate")
    parser.add_argument("--source", type=str, default="Manual",
                       help="Data source name")
    parser.add_argument("--force", action="store_true",
                       help="Force overwrite if today's record exists")

    args = parser.parse_args()

    if args.auto:
        rates = fetch_current_rates()
        if rates is None:
            print("Failed to fetch rates", file=sys.stderr)
            sys.exit(1)
        record_rate(
            hkd_to_cny=rates["hkd_to_cny"],
            cny_to_hkd=rates["cny_to_hkd"],
            source=rates["source"],
            timestamp=rates["timestamp"],
            force=args.force
        )
    elif args.hkd_to_cny and args.cny_to_hkd:
        record_rate(
            hkd_to_cny=args.hkd_to_cny,
            cny_to_hkd=args.cny_to_hkd,
            source=args.source,
            force=args.force
        )
    else:
        print("Error: Must specify --auto or --hkd-to-cny and --cny-to-hkd")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
