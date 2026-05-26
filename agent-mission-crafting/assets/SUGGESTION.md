---
title: Generator Bidirectional Cumulative Feedback Specification
name: agent-mission-crafting
description: Bidirectional cumulative feedback specification for Generator. Planner and Evaluator propose gaps; Generator marks resolved after correction. Append-only, never overwrite.
version: v1.2.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T17:18:10+08:00
fixes: []
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/SUGGESTION.md"
  github_path: "agent-mission-crafting/assets/SUGGESTION.md"
---

# SUGGESTION.md — Generator 雙向累積型反饋規範

> 核心規則：自己不建议自己。Planner 和 Evaluator 對 Generator 提出缺口，Generator 修正後標記「已解決」。
> 文件位置：agent-mission-crafting/assets/SUGGESTION.md
> 性質：累積型文件，持續追加，不覆蓋
> 版本：v1.0.0

---

## 索引表

| 缺口編號 | 子任務ID | 發現者 | 輪次 | 問題類型 | 狀態 | 關鍵詞 |
|---------|---------|--------|------|---------|------|--------|
| C-001 | T3 | PLANNER | R1 | 執行建議 | 待解決 | 等寬字體 |
| C-002 | T5 | EVALUATOR | R11 | QC 更正 | 已解決 | 字體大小 |
| C-003 | T7 | PLANNER | R1 | 執行建議 | 待解決 | 動態計算 |

---

## C-001

- **子任務 ID**: T3
- **發現者**: PLANNER
- **輪次**: R1
- **問題類型**: 執行建議
- **描述**: 條碼佔位請使用等寬字體（monospace），避免非等寬字體導致編號長度計算錯誤
- **影響**: 若使用比例字體，30 ASCII 長度的條碼編號可能視覺上溢出容器
- **建議**: 指定 font-family: 'Courier New', monospace; 並預留 35ch 寬度
- **狀態**: 待解決
- **修正驗證**: （Generator 修正後填寫）

---

## C-002

- **子任務 ID**: T5
- **發現者**: EVALUATOR
- **輪次**: R11（QC 階段）
- **問題類型**: QC 更正
- **描述**: 分店資訊字體大小需微調。Generator 輸出為 12pt，但 PDF 原稿為 10pt，視覺比例失調
- **影響**: 顧客視覺上感覺排版擁擠，專業感下降
- **建議**: 將分店資訊字體統一調整為 10pt，行高 1.4
- **狀態**: 已解決
- **修正驗證**: Generator 已修正為 10pt / 1.4 行高。Evaluator R12 驗證通過，與 PDF 原稿視覺一致。

---

## C-003

- **子任務 ID**: T7
- **發現者**: PLANNER
- **輪次**: R1
- **問題類型**: 執行建議
- **描述**: 簽名區動態計算請使用 max() 函數確保最小間距，避免貨品極多時簽名區被壓縮至 0
- **影響**: 若未設最小間距保護，極端情況下簽名區可能完全消失
- **建議**: 簽名區距離 = max(最後一項底部 + 20mm, 頁底 - 30mm)
- **狀態**: 待解決
- **修正驗證**: （Generator 修正後填寫）

---

## 使用說明

### 誰可以追加？

| 角色 | 可以給 Generator 提 SUGGESTION | 禁止行為 |
|------|------------------------------|---------|
| Planner | 執行建議（計劃階段預見的難點） | 不寫 Planner 自己的計劃缺口 |
| Evaluator | QC 更正（Crafting 完成後的偏差） | 不寫 Evaluator 自己的評估缺口 |
| Generator | 只修正、不主動提出（自己不建议自己） | 不寫 Generator 自己的執行缺口 |

### 問題類型定義

| 類型 | 說明 | 來源 |
|------|------|------|
| **執行建議** | Planner 在計劃階段預見的執行難點，提前告訴 Generator | Planner |
| **QC 更正** | Evaluator 在 QC 階段發現的輸出偏差，要求 Generator 修正 | Evaluator |
| **技術警告** | 任何角色發現的技術風險（如瀏覽器兼容性、性能瓶頸） | Planner / Evaluator |

### 如何追加？

1. **Planner**：生成 checklist 時預見執行難點 → 調用 `crafting_report.append_suggestion()` 追加
2. **Evaluator**：QC 階段發現偏差 → 調用 `crafting_report.append_suggestion()` 追加
3. **Generator**：讀取 SUGGESTION.md → 修正輸出 → 調用 `crafting_report.update_suggestion_status()` 標記「已解決」

### 狀態流轉

```
待解決 → Generator 修正 → Planner/Evaluator 驗證 → 已解決
```

### 編號規則

- 缺口編號：`C-{三位數}`（C = Crafting）
- 輪次標記：`R{數字}`（計劃階段 R1 / QC 階段 R11）
- 問題類型：`執行建議` / `QC 更正` / `技術警告`

### 與其他文件的關係

| 文件 | 用途 | 區別 |
|------|------|------|
| SUGGESTION.md（本檔） | Planner/Evaluator 對 Generator 的建議 | 外部反饋 |
| CORRECTION.md | 錯誤日誌（計劃/評估/執行問題） | 事後追溯 |
| GENERATOR_REPORT | Generator 的執行報告 | 單輪輸出 |

### 累積價值

累積 10 次任務後，可統計：
- Planner 哪類執行建議最多（技術選型？邊界條件？）
- Evaluator 哪類 QC 更正最多（字體？間距？佈局？）
- Generator 哪類問題修正最慢（技術債？理解偏差？）

這是 Generator 的「外部反饋歷史」，用於持續改進執行質量。

---

*模板版本：v1.0.0*
*最後更新：2026-05-11*
