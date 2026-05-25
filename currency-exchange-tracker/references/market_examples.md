---
title: "Market Examples - HKD/CNY Exchange Tracker"
name: "currency-exchange-tracker"
description: "Common exchange timing patterns, alert scenarios, historical data analysis examples, and best practices for HKD/CNY exchange."
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
  local_path: "{baseDir}/references/market_examples.md"
  github_path: "currency-exchange-tracker/references/market_examples.md"
---

# Market Examples - HKD/CNY Exchange Tracker

> **Version**: v2.0.1  
> **Updated**: 2026-05-25

---

## Common Exchange Timing Patterns

### Pattern 1: Rate Better Than Past 7 Days

**Scenario**: Current rate is higher than 7-day average

**Criteria**:
```
Current rate > 7-day average + 0.5%
```

**Recommendation**: Good time to exchange HKD to CNY

**Example**:
```
Current HKD→CNY: 0.9234
7-day average: 0.9156
Difference: +0.85%

Recommendation: Good time to exchange HKD→CNY
   (Current rate is 0.85% better than 7-day average)
```

---

### Pattern 2: Rate Worse Than Past 7 Days

**Scenario**: Current rate is lower than 7-day average

**Criteria**:
```
Current rate < 7-day average - 0.5%
```

**Recommendation**: May not be optimal exchange timing

**Example**:
```
Current HKD→CNY: 0.9100
7-day average: 0.9156
Difference: -0.61%

Recommendation: May not be optimal exchange timing
   (Current rate is 0.61% worse than 7-day average)
```

---

### Pattern 3: Rate Stable (Sideways)

**Scenario**: Current rate is within ±0.5% of 7-day average

**Criteria**:
```
7-day average - 0.5% <= Current rate <= 7-day average + 0.5%
```

**Recommendation**: Neutral, can exchange if needed

**Example**:
```
Current HKD→CNY: 0.9234
7-day average: 0.9234
Difference: 0.00%

Recommendation: Neutral, can exchange if needed
   (Current rate is within 7-day average ±0.5%)
```

---

### Pattern 4: Rising Trend (HKD Strengthening)

**Scenario**: Rate has been rising for 3+ consecutive days

**Criteria**:
```
Consecutive 3+ days: daily rate > previous day rate
```

**Recommendation**: HKD strengthening, observe before deciding

**Example**:
```
Date          HKD→CNY
2026-05-08    0.9200
2026-05-09    0.9210  (+0.11%)
2026-05-10    0.9225  (+0.16%)
2026-05-11    0.9234  (+0.10%)

Trend: Rising (HKD strengthening)
```

---

### Pattern 5: Falling Trend (HKD Weakening)

**Scenario**: Rate has been falling for 3+ consecutive days

**Criteria**:
```
Consecutive 3+ days: daily rate < previous day rate
```

**Recommendation**: HKD weakening, consider exchanging if CNY needed urgently

**Example**:
```
Date          HKD→CNY
2026-05-08    0.9250
2026-05-09    0.9240  (-0.11%)
2026-05-10    0.9230  (-0.11%)
2026-05-11    0.9220  (-0.11%)

Trend: Falling (HKD weakening)
```

---

## Alert Usage Scenarios

### Scenario 1: Set Target Rate Alert

**User Need**: Notify when HKD→CNY reaches 0.95

**Operation**:
```bash
python set_alert.py add   --direction hkd-to-cny   --target 0.95   --condition above   --note "Target rate reached, can exchange"
```

**Output**:
```
Alert created successfully
   ID: alert_20260511_143022
   Direction: hkd-to-cny
   Target: 0.95
   Condition: above
   Status: Active
```

---

### Scenario 2: Set Stop-Loss Alert

**User Need**: Notify when HKD→CNY drops below 0.90

**Operation**:
```bash
python set_alert.py add   --direction hkd-to-cny   --target 0.90   --condition below   --note "Rate too low, consider stop-loss"
```

---

### Scenario 3: List All Alerts

**Operation**:
```bash
python set_alert.py list
```

**Output**:
```
Exchange Rate Alerts (2 total)
============================================================

ID: alert_20260511_143022
  Direction: hkd-to-cny
  Target: 0.95
  Condition: above
  Status: Active
  Created: 2026-05-11T14:30:22+08:00
  Note: Target rate reached, can exchange

ID: alert_20260511_145500
  Direction: hkd-to-cny
  Target: 0.90
  Condition: below
  Status: Active
  Created: 2026-05-11T14:55:00+08:00
  Note: Rate too low, consider stop-loss
```

---

## Historical Data Analysis Example

### 30-Day Trend Analysis

```
Exchange Rate Analysis (Past 30 Days)
==================================================
Current HKD/CNY Rate: 0.9234
30-Day Average: 0.9200
30-Day Min: 0.9150
30-Day Max: 0.9280

Recommendation: Good time to exchange HKD→CNY
   (Current rate is 0.37% better than 30-day average)

Trend: Rising (HKD strengthening)

Detailed Data (Past 30 Days):
  2026-04-12: HKD→CNY 0.9150, Source: Yahoo Finance
  ...
  2026-05-11: HKD→CNY 0.9234, Source: Yahoo Finance
```

---

## Best Practices

### 1. Regular Recording

Recommend daily automatic recording:
```bash
# Set cron job
0 9 * * * cd /path/to/skill && python scripts/record_exchange_rate.py --auto
```

### 2. Combined Analysis

Analyze multiple timeframes simultaneously:
```bash
python analyze_exchange_rate.py --days 7
python analyze_exchange_rate.py --days 14
python analyze_exchange_rate.py --days 30
```

### 3. Alert Strategy

- **Target rate**: Set ideal rate, notify when reached
- **Stop-loss rate**: Set minimum acceptable rate, notify when below
- **Volatility alert**: Set fluctuation threshold, notify on abnormal movement

---

## FAQ

### Q: Why does the rate differ from bank rates?
A: Our data comes from public APIs like Yahoo Finance, which may differ from actual bank trading rates. Use bank quotes as final reference; this tool is for reference only.

### Q: Data update frequency?
A: Yahoo Finance API data is typically delayed 15-30 minutes. For real-time data, consider paid APIs.

### Q: How to add new data sources?
A: Modify `scripts/fetch_exchange_rate.py` CONFIG["sources"] to add new API endpoints and parsing logic.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v2.0.0 | 2026-05-11 | Add alert scenarios, FAQ, best practices |
| v1.0.0 | 2026-05-08 | Initial version |
