---
title: "currency-exchange-tracker — LLM SKILL.md"
name: "currency-exchange-tracker"
description: "Track HKD/CNY exchange rates daily, record historical data, and provide optimal exchange timing recommendations."
version: "v2.0.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T16:45:00+08:00"
fixes: [25]
auth_config:
  provider: yahoo_finance
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/SKILL.md"
  github_path: "currency-exchange-tracker/SKILL.md"
---

# HKD/CNY Exchange Tracker

## Overview

This skill provides automated tracking of HKD to CNY and CNY to HKD exchange rates. It records daily exchange rates, analyzes historical trends, and provides recommendations on optimal exchange timing based on past 7-day comparisons.

## Quick Start

To accomplish any exchange rate task, follow these steps:

1. **Fetch current exchange rate** - Use `scripts/fetch_exchange_rate.py` to get real-time rates
2. **Record exchange rate** - Use `scripts/record_exchange_rate.py` to save to historical record
3. **Analyze trends** - Use `scripts/analyze_exchange_rate.py` to get exchange timing recommendations

## Task Categories

### 1. Fetch Current Exchange Rate

To fetch the current HKD/CNY or CNY/HKD exchange rate:

```bash
python scripts/fetch_exchange_rate.py --direction [hkd-to-cny|cny-to-hkd]
```

This script:
- Fetches real-time exchange rates from multiple sources (Investing.com, Yahoo Finance, XE.com)
- Returns current rate, daily change, and update time
- Supports two directions: HKD→CNY or CNY→HKD

**Examples**:
```bash
# Fetch HKD to CNY rate
python scripts/fetch_exchange_rate.py --direction hkd-to-cny

# Fetch CNY to HKD rate
python scripts/fetch_exchange_rate.py --direction cny-to-hkd
```

### 2. Record Daily Exchange Rate

To record today's exchange rate to historical record:

```bash
python scripts/record_exchange_rate.py --auto
```

This script:
- Automatically fetches current rates
- Appends to `assets/exchange_rate_history.csv`
- Records date, HKD/CNY rate, CNY/HKD rate, source, and timestamp

**Manual recording**:
```bash
python scripts/record_exchange_rate.py --hkd-to-cny 0.92 --cny-to-hkd 1.09 --source "Investing.com"
```

### 3. Analyze Exchange Trends & Recommend Optimal Timing

To analyze past 7-30 days and get exchange recommendations:

```bash
python scripts/analyze_exchange_rate.py --days 7
```

This script:
- Reads historical data from `assets/exchange_rate_history.csv`
- Compares current rate with past N days (default: 7)
- Calculates statistics: min, max, average, standard deviation
- **Provides recommendation**: Whether now is a good time to exchange
- References market examples: "rate better than past 7-day average" = current rate is better than past 7-day average

**Output example**:
```
Exchange Rate Analysis (Past 7 Days)
======================================
Current HKD/CNY Rate: 0.9234
7-Day Average: 0.9156
7-Day Min: 0.9100
7-Day Max: 0.9250

RECOMMENDATION: Good time to exchange HKD→CNY
   (Current rate is 0.85% better than 7-day average)

Trend: Rising (HKD strengthening)
```

**Extended analysis**:
```bash
# Analyze past 30 days
python scripts/analyze_exchange_rate.py --days 30

# Compare with past 7, 14, 30 days
python scripts/analyze_exchange_rate.py --compare-all
```

### 4. Set Exchange Rate Alert

To set an alert when exchange rate reaches a target:

```bash
python scripts/set_alert.py --direction hkd-to-cny --target 0.95 --condition above
```

This script:
- Saves alert configuration to `assets/exchange_alerts.json`
- Can be checked manually or via automation
- Supports conditions: `above`, `below`, `cross-above`, `cross-below`

## Data Storage

### Historical Record Format (CSV)

Location: `assets/exchange_rate_history.csv`

| Column | Description |
|--------|-------------|
| date | YYYY-MM-DD format |
| hkd_to_cny | HKD to CNY rate |
| cny_to_hkd | CNY to HKD rate |
| source | Data source (Investing.com, Yahoo Finance, etc.) |
| timestamp | ISO 8601 timestamp |

### Alert Configuration (JSON)

Location: `assets/exchange_alerts.json`

```json
{
  "alerts": [
    {
      "direction": "hkd-to-cny",
      "target": 0.95,
      "condition": "above",
      "created": "2026-05-08T10:45:00+08:00",
      "active": true
    }
  ]
}
```

## References

For detailed API documentation and data source references, see:
- `references/api_reference.md` - API endpoints and scraping methods
- `references/market_examples.md` - Market examples and market analysis patterns

## Resources

### scripts/
- `fetch_exchange_rate.py` - Fetch real-time exchange rates
- `record_exchange_rate.py` - Record daily exchange rates
- `analyze_exchange_rate.py` - Analyze trends and recommend optimal timing
- `set_alert.py` - Set exchange rate alerts
- `fetch_alipay_rate.py` - Fetch Alipay HKD/CNY rate via ExchangeRate-API

### references/
- `api_reference.md` - API documentation for exchange rate sources
- `market_examples.md` - Market examples: common exchange timing patterns

### assets/
- `exchange_rate_history.csv` - Historical exchange rate records
- `exchange_alerts.json` - Active exchange rate alerts
