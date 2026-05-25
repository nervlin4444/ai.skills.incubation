---
title: "Scoring Dimensions and Weights"
name: "openrouter-llm-tracker"
description: "Defines the scoring dimensions, weight distribution, and calculation formula for LLM model evaluation."
version: "v1.2.2"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T11:58:00+08:00"
fixes: []
auth_config:
  provider: openrouter
  auth_method: token
  token_env_var: OPENROUTER_API_KEY
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/references/RANKING.md"
  github_path: "openrouter-llm-tracker/references/RANKING.md"
---
# Scoring Dimensions and Weights

## 1. Scoring Dimensions

Each model is evaluated across five dimensions. Each dimension score is 0-100.

| Dimension ID | Dimension Name | Description | Measurement Method |
|--------------|----------------|-------------|-------------------|
| latency | 延遲表現 | Time to first token (TTFB) and total generation time | Measured by scripts/llm.curl.py |
| accuracy | 準確率 | Task completion correctness on benchmark tasks | Manual evaluation or benchmark results |
| tool_reliability | 工具可靠性 | Function calling success rate and stability | Measured by tool calling test suite |
| cost_efficiency | 成本效益 | Token consumption and cost per unit task | Calculated from pricing + token usage |
| context_stability | 上下文穩定性 | Consistency under long context (>50% max) | Measured by long-context stress test |

## 2. Weight Distribution (Default — Pending Owner Calibration)

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| latency | 0.20 | Speed is critical for interactive agents |
| accuracy | 0.30 | Correctness is the highest priority |
| tool_reliability | 0.20 | Agent workflows depend on stable tool use |
| cost_efficiency | 0.15 | Cost control for production scaling |
| context_stability | 0.15 | Long context is essential for complex tasks |

**Composite Score Formula:**

```
composite = (latency * 0.20) + (accuracy * 0.30) + (tool_reliability * 0.20) + (cost_efficiency * 0.15) + (context_stability * 0.15)
```

## 3. Dimension Scoring Criteria

### 3.1 Latency (延遲)

| Score | TTFB (ms) | Total (ms) | Description |
|-------|-----------|------------|-------------|
| 100 | < 100 | < 500 | Instant response |
| 90 | < 200 | < 1000 | Fast |
| 80 | < 500 | < 2000 | Acceptable |
| 70 | < 1000 | < 5000 | Moderate |
| 60 | < 2000 | < 10000 | Slow |
| 50 | < 5000 | < 30000 | Very slow |
| 0 | > 5000 | > 30000 | Unusable |

### 3.2 Accuracy (準確率)

| Score | Benchmark | Description |
|-------|-----------|-------------|
| 100 | Top 1% on SWE-Bench / MMLU | Frontier level |
| 90 | Top 5% | Excellent |
| 80 | Top 10% | Good |
| 70 | Top 20% | Acceptable |
| 60 | Top 40% | Mediocre |
| 50 | Top 60% | Below average |
| 0 | Bottom 40% | Unusable |

### 3.3 Tool Reliability (工具可靠性)

| Score | Success Rate | Description |
|-------|--------------|-------------|
| 100 | > 99% | Perfect tool calling |
| 90 | > 95% | Highly reliable |
| 80 | > 90% | Reliable |
| 70 | > 80% | Acceptable |
| 60 | > 70% | Unstable |
| 50 | > 60% | Poor |
| 0 | < 60% | Broken |

### 3.4 Cost Efficiency (成本效益)

| Score | Cost per 1M tokens (input+output) | Description |
|-------|-----------------------------------|-------------|
| 100 | Free | Zero cost |
| 90 | < $0.50 | Extremely cheap |
| 80 | < $1.00 | Very cheap |
| 70 | < $2.00 | Cheap |
| 60 | < $5.00 | Moderate |
| 50 | < $10.00 | Expensive |
| 0 | > $10.00 | Prohibitive |

### 3.5 Context Stability (上下文穩定性)

| Score | Pass Rate at 80% Context | Description |
|-------|--------------------------|-------------|
| 100 | > 99% | Perfect long-context handling |
| 90 | > 95% | Excellent |
| 80 | > 90% | Good |
| 70 | > 80% | Acceptable |
| 60 | > 70% | Degradation noticeable |
| 50 | > 60% | Significant degradation |
| 0 | < 60% | Unusable for long tasks |

## 4. Score Update Rules

| Action | Rule |
|--------|------|
| New score | Average with existing score using exponential moving average (EMA). Default alpha = 0.3. |
| Minimum samples | Do not update tier until at least 3 scores are recorded. |
| Outlier rejection | Scores beyond 2 standard deviations from mean are flagged for review. |
| Manual override | Owner can manually set score via scripts/llm.scorer.py with force=True. |

## 5. History Record Format

Each score update appends to llm.scores.json history array:

```json
{
  "history": [
    {
      "timestamp": "2026-05-12T01:00:00Z",
      "dimensions": {"latency": 85, "accuracy": 92, "tool_reliability": 88, "cost_efficiency": 95, "context_stability": 80},
      "composite": 88.1,
      "tier_before": "domain_expert",
      "tier_after": "specialist_manager",
      "reason": "Composite score crossed threshold 85"
    }
  ]
}
```

## 6. Status

| Item | Status | Owner |
|------|--------|-------|
| Dimension weights | Pending calibration | 主人 |
| Scoring criteria thresholds | Pending calibration | 主人 |
| EMA alpha value | Pending confirmation | 主人 |
| Minimum samples rule | Pending confirmation | 主人 |

## 7. Usage

This file is read by scripts/llm.scorer.py during score calculation. If this file is missing or a section is empty, the script falls back to equal weights (0.2 each) and default thresholds, logging a warning.

---

*File: openrouter-llm-tracker/references/RANKING.md*
*Naming convention: dot-separated, no hyphens or underscores in filenames*