'''
---
title: "fetch_alipay_rate.py"
name: "currency-exchange-tracker"
description: "Fetch HKD/CNY exchange rate via ExchangeRate-API as a backup data source. Saves results to CSV history."
version: "v2.0.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T16:45:00+08:00"
fixes: [25]
auth_config:
  provider: exchangerate_api
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/scripts/fetch_alipay_rate.py"
  github_path: "currency-exchange-tracker/scripts/fetch_alipay_rate.py"
---
'''

# -*- coding: utf-8 -*-

import requests
import csv
import os
from datetime import datetime

def fetch_alipay_rate():
    """Fetch HKD/CNY rate via ExchangeRate-API."""
    try:
        url = "https://api.exchangerate-api.com/v4/latest/HKD"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        hkd_to_usd = data["rates"]["HKD"]
        usd_to_cny = data["rates"]["CNY"]
        hkd_to_cny = usd_to_cny / hkd_to_usd

        return {
            "source": "ExchangeRate-API",
            "from_currency": "HKD",
            "to_currency": "CNY",
            "rate": round(hkd_to_cny, 4),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"Error fetching rate: {e}")
        return None

def save_to_csv(rate_data, csv_path="assets/exchange_rate_history.csv"):
    """Save rate data to CSV file (compatible with record_exchange_rate.py format)."""
    if rate_data is None:
        return False

    file_exists = os.path.isfile(csv_path)
    rows = []
    fieldnames = ["date", "hkd_to_cny", "cny_to_hkd", "source", "timestamp"]

    if file_exists:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    date_str = datetime.now().strftime("%Y-%m-%d")
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if today's record exists
    today_exists = any(row["date"] == date_str for row in rows)

    if today_exists:
        # Remove today's record (will overwrite)
        rows = [row for row in rows if row["date"] != date_str]

    # Calculate cny_to_hkd from hkd_to_cny
    hkd_to_cny = rate_data["rate"]
    cny_to_hkd = round(1 / hkd_to_cny, 4) if hkd_to_cny > 0 else 0

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        writer.writerow({
            "date": date_str,
            "hkd_to_cny": hkd_to_cny,
            "cny_to_hkd": cny_to_hkd,
            "source": rate_data["source"],
            "timestamp": timestamp_str
        })

    print(f"Rate data saved to {csv_path}")
    return True

if __name__ == "__main__":
    print("Fetching Alipay HKD/CNY rate...")
    rate_data = fetch_alipay_rate()

    if rate_data:
        print(f"Success: {rate_data['from_currency']} -> {rate_data['to_currency']} = {rate_data['rate']}")
        save_to_csv(rate_data)
    else:
        print("Failed")
