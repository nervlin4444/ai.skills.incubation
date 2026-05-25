# F-006 補充報告：無日期 Free 模型評分

> 生成時間：2026-05-11T18:53:04Z
> 評分對象：29 個無 release_date 的 free 模型
> 評分規則：✅ 成功 = 延遲越低分越高（反比公式，保底10分） | ❌ 報錯 = 0 分

---

## 📊 評分結果（按分數降序）

| # | 模型 ID | 供應商 | api_created | 狀態 | 延遲 (ms) | 積分 | 備註 |
|---|---------|--------|-------------|------|-----------|------|------|
| 1 | `nvidia/nemotron-3-nano-30b-a3b:free` | NVIDIA | 2025-12-14 | ✅ success | 714 | **100** | 成功連通，延遲 714ms |
| 2 | `arcee-ai/trinity-large-thinking:free` | Arcee-ai | 2026-04-01 | ✅ success | 850 | **84** | 成功連通，延遲 850ms |
| 3 | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | NVIDIA | 2026-04-28 | ✅ success | 982 | **73** | 成功連通，延遲 982ms |
| 4 | `poolside/laguna-m.1:free` | Poolside | 2026-04-28 | ✅ success | 1068 | **67** | 成功連通，延遲 1068ms |
| 5 | `openai/gpt-oss-120b:free` | OpenAI | 2025-08-05 | ✅ success | 1090 | **66** | 成功連通，延遲 1090ms |
| 6 | `poolside/laguna-xs.2:free` | Poolside | 2026-04-28 | ✅ success | 1114 | **64** | 成功連通，延遲 1114ms |
| 7 | `openrouter/free` | OpenRouter | 2026-02-01 | ✅ success | 1164 | **61** | 成功連通，延遲 1164ms |
| 8 | `liquid/lfm-2.5-1.2b-thinking:free` | LiquidAI | 2026-01-20 | ✅ success | 1332 | **54** | 成功連通，延遲 1332ms |
| 9 | `liquid/lfm-2.5-1.2b-instruct:free` | LiquidAI | 2026-01-20 | ✅ success | 1350 | **53** | 成功連通，延遲 1350ms |
| 10 | `nvidia/nemotron-nano-9b-v2:free` | NVIDIA | 2025-09-05 | ✅ success | 1445 | **49** | 成功連通，延遲 1445ms |
| 11 | `nvidia/nemotron-nano-12b-v2-vl:free` | NVIDIA | 2025-10-28 | ✅ success | 1786 | **40** | 成功連通，延遲 1786ms |
| 12 | `baidu/qianfan-ocr-fast:free` | Baidu | 2026-04-20 | ✅ success | 1794 | **40** | 成功連通，延遲 1794ms |
| 13 | `inclusionai/ring-2.6-1t:free` | inclusionAI | 2026-05-08 | ✅ success | 1935 | **37** | 成功連通，延遲 1935ms |
| 14 | `baidu/cobuddy:free` | Baidu | 2026-05-06 | ✅ success | 2737 | **26** | 成功連通，延遲 2737ms |
| 15 | `openrouter/owl-alpha` | OpenRouter | 2026-04-28 | ✅ success | 2989 | **24** | 成功連通，延遲 2989ms |
| 16 | `nvidia/nemotron-3-super-120b-a12b:free` | NVIDIA | 2026-03-11 | ✅ success | 4498 | **16** | 成功連通，延遲 4498ms |
| 17 | `z-ai/glm-4.5-air:free` | Z.AI | 2025-07-25 | ✅ success | 10318 | **10** | 成功連通，延遲 10318ms |
| 18 | `google/lyria-3-clip-preview` | Google | 2026-03-30 | ❌ error | 283 | **0** | 連通失敗（HTTP 403: {"error":{"message":"This model is not available in your region.","cod），延遲 283ms |
| 19 | `google/lyria-3-pro-preview` | Google | 2026-03-30 | ❌ error | 289 | **0** | 連通失敗（HTTP 403: {"error":{"message":"This model is not available in your region.","cod），延遲 289ms |
| 20 | `google/gemma-4-31b-it:free` | Google | 2026-04-02 | ❌ rate_limited | 665 | **0** | Rate Limited（HTTP 429），延遲 665ms |
| 21 | `google/gemma-4-26b-a4b-it:free` | Google | 2026-04-03 | ❌ rate_limited | 707 | **0** | Rate Limited（HTTP 429），延遲 707ms |
| 22 | `meta-llama/llama-3.3-70b-instruct:free` | Meta | 2024-12-06 | ❌ rate_limited | 820 | **0** | Rate Limited（HTTP 429），延遲 820ms |
| 23 | `meta-llama/llama-3.2-3b-instruct:free` | Meta | 2024-09-25 | ❌ rate_limited | 823 | **0** | Rate Limited（HTTP 429），延遲 823ms |
| 24 | `cognitivecomputations/dolphin-mistral-24b-venice-edition:free` | CognitiveComputations | 2025-07-09 | ❌ rate_limited | 825 | **0** | Rate Limited（HTTP 429），延遲 825ms |
| 25 | `qwen/qwen3-coder:free` | Alibaba | 2025-07-23 | ❌ rate_limited | 850 | **0** | Rate Limited（HTTP 429），延遲 850ms |
| 26 | `qwen/qwen3-next-80b-a3b-instruct:free` | Alibaba | 2025-09-11 | ❌ rate_limited | 861 | **0** | Rate Limited（HTTP 429），延遲 861ms |
| 27 | `openai/gpt-oss-20b:free` | OpenAI | 2025-08-05 | ❌ rate_limited | 893 | **0** | Rate Limited（HTTP 429），延遲 893ms |
| 28 | `nousresearch/hermes-3-llama-3.1-405b:free` | NousResearch | 2024-08-16 | ❌ rate_limited | 914 | **0** | Rate Limited（HTTP 429），延遲 914ms |
| 29 | `minimax/minimax-m2.5:free` | MiniMax | 2026-02-12 | ❌ rate_limited | 1299 | **0** | Rate Limited（HTTP 429），延遲 1299ms |

---

## 📈 統計摘要

| 指標 | 值 |
|------|-----|
| 測試模型數 | 29 |
| 成功連通 | 17/29 |
| 連通失敗 | 12/29 |
| 平均延遲（成功） | 2186ms |
| 平均積分 | 29.8 |
| 最高積分 | 100（`nvidia/nemotron-3-nano-30b-a3b:free`）|
| 最低積分 | 0（`minimax/minimax-m2.5:free`）|

---

## ⚠️ 連通失敗模型

- `google/lyria-3-clip-preview`：連通失敗（HTTP 403: {"error":{"message":"This model is not available in your region.","cod），延遲 283ms
- `google/lyria-3-pro-preview`：連通失敗（HTTP 403: {"error":{"message":"This model is not available in your region.","cod），延遲 289ms
- `google/gemma-4-31b-it:free`：Rate Limited（HTTP 429），延遲 665ms
- `google/gemma-4-26b-a4b-it:free`：Rate Limited（HTTP 429），延遲 707ms
- `meta-llama/llama-3.3-70b-instruct:free`：Rate Limited（HTTP 429），延遲 820ms
- `meta-llama/llama-3.2-3b-instruct:free`：Rate Limited（HTTP 429），延遲 823ms
- `cognitivecomputations/dolphin-mistral-24b-venice-edition:free`：Rate Limited（HTTP 429），延遲 825ms
- `qwen/qwen3-coder:free`：Rate Limited（HTTP 429），延遲 850ms
- `qwen/qwen3-next-80b-a3b-instruct:free`：Rate Limited（HTTP 429），延遲 861ms
- `openai/gpt-oss-20b:free`：Rate Limited（HTTP 429），延遲 893ms
- `nousresearch/hermes-3-llama-3.1-405b:free`：Rate Limited（HTTP 429），延遲 914ms
- `minimax/minimax-m2.5:free`：Rate Limited（HTTP 429），延遲 1299ms

---
*由 _score_all_free.py 自動生成*