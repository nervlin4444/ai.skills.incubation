---
title: "API Reference - HKD/CNY Exchange Tracker"
name: "currency-exchange-tracker"
description: "API endpoints, request formats, response structures, and error codes for HKD/CNY exchange rate data sources."
version: "v2.0.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T16:45:00+08:00"
fixes:
  - "Fix fetch_alipay_rate.py CSV format inconsistency (use same format as record_exchange_rate.py)"
auth_config:
  provider: yahoo_finance
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/references/api_reference.md"
  github_path: "currency-exchange-tracker/references/api_reference.md"
---

# API Reference - HKD/CNY Exchange Tracker

> **Version**: v2.0.1  
> **Updated**: 2026-05-25

---

## Data Sources

### 1. Yahoo Finance API

**Endpoint**:
```
https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}
```

**Supported Currency Pairs**:
| Direction | Symbol | Description |
|-----------|--------|-------------|
| HKD→CNY | HKDCNY=X | HKD to CNY |
| CNY→HKD | CNYHKD=X | CNY to HKD |

**Request Method**: GET

**Headers**:
```
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
```

**Response Format** (JSON):
```json
{
  "chart": {
    "result": [{
      "meta": {
        "regularMarketPrice": 0.9234,
        "previousClose": 0.9222,
        "currency": "CNY"
      }
    }]
  }
}
```

**Field Descriptions**:
| Field | Type | Description |
|-------|------|-------------|
| regularMarketPrice | float | Current exchange rate |
| previousClose | float | Previous close price |
| currency | string | Quote currency |

**Calculation Logic**:
- Daily change = regularMarketPrice - previousClose
- Change percent = (daily change / previousClose) × 100

---

### 2. Investing.com (Backup Source)

**Endpoint**:
```
https://hk.investing.com/currencies/hkd-cny
```

**Description**: Web page scraping (requires beautifulsoup4)

**Implementation**:
```python
from bs4 import BeautifulSoup
import requests

url = "https://hk.investing.com/currencies/hkd-cny"
headers = {'User-Agent': 'Mozilla/5.0...'}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')
# Extract rate data from HTML
```

**Note**: This source requires additional parsing logic. Current version prioritizes Yahoo Finance API.

---

### 3. ExchangeRate-API (Alipay Backup)

**Endpoint**:
```
https://api.exchangerate-api.com/v4/latest/HKD
```

**Description**: Free exchange rate API. Returns HKD to all currencies. CNY rate extracted from rates["CNY"].

---

## Script Interfaces

### fetch_exchange_rate.py

**Function**: Fetch real-time exchange rate

**CLI Arguments**:
```bash
python fetch_exchange_rate.py --direction {hkd-to-cny|cny-to-hkd} --output {json|text}
```

**Parameters**:
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| --direction | No | hkd-to-cny | Exchange direction |
| --output | No | json | Output format |

**Return Format** (JSON):
```json
{
  "rate": 0.9234,
  "change": 0.0012,
  "change_percent": 0.13,
  "update_time": "2026-05-11 10:02:37",
  "source": "Yahoo Finance"
}
```

**Error Format**:
```json
{
  "error": "All sources failed",
  "details": "yahoo: Connection timeout; investing: HTTP 403",
  "rate": null,
  "source": null,
  "suggestion": "Please check internet connection or try again later"
}
```

---

### record_exchange_rate.py

**Function**: Record daily exchange rate to CSV

**CLI Arguments**:
```bash
# Auto fetch and record
python record_exchange_rate.py --auto

# Manual record
python record_exchange_rate.py --hkd-to-cny 0.92 --cny-to-hkd 1.09 --source "Manual"

# Force overwrite
python record_exchange_rate.py --auto --force
```

**CSV Format**:
```csv
date,hkd_to_cny,cny_to_hkd,source,timestamp
2026-05-11,0.9234,1.0827,Yahoo Finance,2026-05-11T10:02:37+08:00
```

---

### analyze_exchange_rate.py

**Function**: Analyze exchange rate trends and provide recommendations

**CLI Arguments**:
```bash
python analyze_exchange_rate.py --days 7
```

**Parameters**:
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| --days | No | 7 | Analysis period (days) |

---

### set_alert.py

**Function**: Set exchange rate alerts

**Subcommands**:
```bash
# Add alert
python set_alert.py add --direction hkd-to-cny --target 0.95 --condition above --note "Good rate"

# List alerts
python set_alert.py list

# Deactivate alert
python set_alert.py deactivate alert_20260511_143022

# Delete alert
python set_alert.py delete alert_20260511_143022
```

**Alert Conditions**:
| Condition | Description |
|-----------|-------------|
| above | Rate above target |
| below | Rate below target |
| cross-above | Break above target |
| cross-below | Break below target |

---

## Configuration

### Global Config (CONFIG)

```python
CONFIG = {
    "timeout": 10,        # API request timeout (seconds)
    "max_retries": 3,     # Max retry attempts
    "sources": {
        "yahoo": {
            "url": "https://query1.finance.yahoo.com/v8/finance/chart/HKDCNY=X",
            "priority": 1     # Priority (lower = higher)
        },
        "investing": {
            "url": "https://hk.investing.com/currencies/hkd-cny",
            "priority": 2
        }
    }
}
```

---

## Error Codes

| Error Type | Description | Resolution |
|-----------|-------------|------------|
| Connection timeout | Network timeout | Check connection, retry later |
| HTTP 403 | Access denied | Source may block access, try backup |
| No HTTP library | Missing HTTP library | Install requests: `pip install requests` |
| Rate not found | Cannot parse rate | Source format may have changed |

---

## Dependencies

```
requests (optional, recommended)
urllib (Python standard library, fallback)
beautifulsoup4 (optional, for Investing.com scraping)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v2.0.0 | 2026-05-11 | Real API calls, alert feature, complete documentation |
| v1.0.0 | 2026-05-08 | Initial version, hardcoded data |
