# F-006 免費模型連通測試與評分報告

> 生成時間：2026-05-11T18:44:33Z
> 測試總數：29 個 free 模型
> 四月之後發佈：10 個
> 評分規則：✅ 成功 = 反應速度越快分越高（延遲反比）｜❌ 報錯 = 0 分

---

## 📊 評分結果（按分數降序）

| # | 模型 ID | 供應商 | 發佈日期 | 狀態 | 延遲 (ms) | 積分 | 備註 |
|---|---------|--------|----------|------|-----------|------|------|
| 1 | `arcee-ai/trinity-large-thinking:free` | Arcee-ai | 2026-04-01 | ✅ success | 850 | **100** | ✅ 成功連通，延遲 850ms |
| 2 | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | NVIDIA | 2026-04-28 | ✅ success | 982 | **87** | ✅ 成功連通，延遲 982ms |
| 3 | `poolside/laguna-m.1:free` | Poolside | 2026-04-28 | ✅ success | 1068 | **80** | ✅ 成功連通，延遲 1068ms |
| 4 | `poolside/laguna-xs.2:free` | Poolside | 2026-04-28 | ✅ success | 1114 | **76** | ✅ 成功連通，延遲 1114ms |
| 5 | `baidu/qianfan-ocr-fast:free` | Baidu | 2026-04-20 | ✅ success | 1794 | **47** | ✅ 成功連通，延遲 1794ms |
| 6 | `inclusionai/ring-2.6-1t:free` | inclusionAI | 2026-05-08 | ✅ success | 1935 | **44** | ✅ 成功連通，延遲 1935ms |
| 7 | `baidu/cobuddy:free` | Baidu | 2026-05-06 | ✅ success | 2737 | **31** | ✅ 成功連通，延遲 2737ms |
| 8 | `openrouter/owl-alpha` | OpenRouter | 2026-04-28 | ✅ success | 2989 | **28** | ✅ 成功連通，延遲 2989ms |
| 9 | `google/gemma-4-31b-it:free` | Google | 2026-04-02 | ❌ rate_limited | 665 | **0** | ❌ Rate Limited（HTTP 429），延遲 665ms |
| 10 | `google/gemma-4-26b-a4b-it:free` | Google | 2026-04-03 | ❌ rate_limited | 707 | **0** | ❌ Rate Limited（HTTP 429），延遲 707ms |

---

## 📈 統計摘要

| 指標 | 值 |
|------|-----|
| 成功連通 | 8/10 |
| 連通失敗 | 2/10 |
| 平均延遲（成功） | 1684ms |
| 平均積分 | 49.3 |
| 最高積分 | 100（arcee-ai/trinity-large-thinking:free）|
| 最低積分 | 0（google/gemma-4-26b-a4b-it:free）|

---

## 🏆 最佳表現 TOP 3

**1. `arcee-ai/trinity-large-thinking:free`** — 積分 100，延遲 850ms，發佈 2026-04-01
**2. `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`** — 積分 87，延遲 982ms，發佈 2026-04-28
**3. `poolside/laguna-m.1:free`** — 積分 80，延遲 1068ms，發佈 2026-04-28

---

## ⚠️ 連通失敗模型

- `google/gemma-4-31b-it:free`：❌ Rate Limited（HTTP 429），延遲 665ms
- `google/gemma-4-26b-a4b-it:free`：❌ Rate Limited（HTTP 429），延遲 707ms

---
*報告由 F-006 批量測試 + llm.scorer 評分生成*