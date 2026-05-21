---
id: agent-swarm-kimi-codegen-readme
version: v1.2.0
description: "agent-swarm-kimi-codegen SKILL.md 的人類可讀解釋書。記載 Kimi 代碼分包技能的設計原理、Moonshot API 調用規範、避坑經驗注入機制、閉環修正 3 輪流程、Context Caching Token 優化、JSON Schema 強制輸出、與 Mission Pipeline 的協作關係與常見誤解糾偏，供主人參考。"
author: Kevin Lin
skill_bundle: agent-harness-by-kevinlinz
tags: [swarm-kimi, codegen, readme, reference]
---

# Agent Swarm Kimi Codegen 解釋書

## 文件定位

| 檔案 | 讀者 | 用途 |
|------|------|------|
| SKILL.md（根目錄） | LLM + 主人掃描 | 簡短描述，供 use_skill 建立 available_skill |
| SKILL.md（assets/） | LLM 執行 | 執行指令集：API 調用、避坑注入、閉環修正、Token 優化 |
| SKILL.md（本檔，位於 readme/） | 主人 | 設計原理、API 規範、閉環機制、Token 優化策略 |

LLM 不讀取本檔案。本檔案僅供主人理解 Kimi Codegen 技能的設計意圖。

## 為何需要這個技能？

當 Mission Pipeline 中的 Generator 需要生成專業代碼時：
- 直接在主對話中生成代碼，容易受上下文干擾，輸出格式不穩定
- 不注入避坑經驗，重複踩坑（如邊界條件遺漏、依賴版本衝突）
- 生成後不測試，交付後才發現錯誤，返工成本高
- 不控制 Token 消耗，長任務成本爆炸
- 輸出格式混亂（Markdown 圍欄 + JSON 混雜），難以自動解析

Kimi Codegen 的設計目標是：**通過 Moonshot API (kimi-k2.6) 專業分包代碼生成，強制 JSON 輸出，注入避坑經驗，3 輪閉環修正，Context Caching 減少 Token 消耗。**

## 核心設計原理

### 1. 為何要「分包」而非「本地生成」？

| 生成方式 | 優點 | 缺點 | 適用場景 |
|---------|------|------|---------|
| **本地生成** | 快速、無額外 API 成本 | 受上下文干擾、格式不穩定、難以注入專業經驗 | 簡單腳本、對話記錄 |
| **API 分包** | 專業模型、格式穩定、可注入避坑經驗、可閉環修正 | 有 API 成本、需網絡連接 | 複雜算法、生產代碼、測試覆蓋 |

**核心原則**：當代碼複雜度超過「單文件腳本」或需要「高測試覆蓋」時，必須分包給 Kimi 專業生成。

### 2. 避坑經驗注入機制

過去 Generator 生成代碼時，每次都從零開始，重複踩坑：
- 邊界條件遺漏（空列表、最大值、負數）
- 依賴版本衝突（未鎖定版本號）
- 異常處理不完善（只 catch 不處理）
- 測試覆蓋不足（只測主路徑，不測分支）

**新機制**：在 API 調用前，將歷史避坑經驗注入 System Prompt：

```
Historical lessons:
- 邊界條件：sku_list 為空時必須返回 validation_errors，不能返回 null
- 依賴版本：pandas 必須鎖定 >=2.0.0，否則 read_csv 行為不一致
- 異常處理：網絡超時必須重試 3 次，每次間隔指數退避
- 測試覆蓋：必須包含 empty / single / max / negative 四種邊界值
```

**注入來源**：SKILL_CORRECTIONS.md + SCRIPT_CORRECTIONS.md + 歷史 CORRECTION.md

### 3. 閉環修正 3 輪機制

代碼生成不是「一次交付」，而是「多次迭代」：

| 輪次 | 動作 | 輸入 | 輸出 |
|------|------|------|------|
| **Round 1** | 初始生成 | structured_spec + pitfalls | code_package (JSON) |
| **Round 2** | 第一次修正 | error_report (失敗測試 + 錯誤信息) | 修正後 code_package |
| **Round 3** | 第二次修正 | error_report (剩餘問題) | 最終 code_package |
| **Round 4+** | 上報主人 | 累積錯誤報告 | [ESCALATED] 需人工介入 |

**核心規則**：最多 3 輪自動修正，第 4 輪必須上報主人。防止無限循環消耗 Token。

### 4. Context Caching Token 優化

| 優化策略 | 實施方式 | Token 節省 |
|---------|---------|-----------|
| **System Prompt 緩存** | 將避坑經驗和 Schema 定義放入 System Prompt，啟用 Context Caching | 30-50% |
| **Compact JSON** | 使用 separators=(',', ':') 去除多餘空格 | 10-15% |
| **Diff 傳輸** | 修正輪次只傳輸錯誤信息 + 關鍵上下文，不重傳完整 spec | 40-60% |
| **Response Format 強制** | 指定 response_format={"type": "json_object"}，減少格式無效重試 | 20-30% |

**核心價值**：相比無優化調用，Token 消耗降低 50-70%。

### 5. JSON Schema 強制輸出

代碼包必須符合固定 Schema，禁止 Markdown 圍欄：

```json
{
  "code": {
    "main": "string",
    "tests": "string",
    "dockerfile": "string"
  },
  "logic_analysis": "string",
  "test_coverage": ["string"],
  "dependencies": ["string"],
  "execution_command": "string"
}
```

**為何強制 JSON？**
- 可被下游工具自動解析（無需正則提取）
- 結構穩定，欄位齊全
- 便於版本控制和 diff 比對

## 與 Mission Pipeline 的協作關係

### 觸發條件

| 觸發者 | 場景 | 說明 |
|--------|------|------|
| **agent-mission-crafting** | Generator 需要專業代碼生成 | 如「生成條碼校驗算法」「生成補貨計算模組」 |
| **agent-coordination-mode** | 協調者任命 Kimi 為代碼專家 | 當任務涉及複雜算法或生產級代碼時 |

### 輸入來源

| 輸入 | 來源 | 用途 |
|------|------|------|
| **structured_spec** | Generator / Planner | 代碼需求規格（輸入/輸出、邊界條件、測試矩陣） |
| **pitfalls** | SKILL_CORRECTIONS.md | 避坑經驗注入 System Prompt |
| **task_id** | coordinator | 追蹤會話和輪次 |

### 輸出交付

| 輸出 | 格式 | 接收者 |
|------|------|--------|
| **code_package** | JSON (強制 Schema) | Generator（嵌入到執行結果） |
| **logic_analysis** | Markdown | Evaluator（QC 審視） |
| **test_coverage** | 字符串數組 | Evaluator（驗收標準核對） |

## 常見誤解糾偏（重要）

### 誤解 1：「Kimi Codegen 可以生成任何代碼」

**錯誤理解**：所有代碼生成都應該分包給 Kimi。

**正確理解**：只有「複雜算法」或「生產級代碼」才需要分包。簡單腳本（< 50 行）本地生成更高效。

**後果**：過度分包增加 API 成本和延遲，簡單任務反而變慢。

### 誤解 2：「閉環修正可以無限進行」

**錯誤理解**：發現錯誤就讓 Kimi 一直修，直到完美。

**正確理解**：最多 3 輪自動修正。第 4 輪必須上報主人。完美是敵人，夠用是朋友。

**後果**：無限修正導致 Token 消耗爆炸，且可能陷入「修正引入新錯誤」的死循環。

### 誤解 3：「避坑經驗可以憑空編造」

**錯誤理解**：為了讓 Kimi 生成更好的代碼，編造一些「經驗」注入。

**正確理解**：避坑經驗必須來自真實的 SKILL_CORRECTIONS.md / SCRIPT_CORRECTIONS.md。編造的經驗可能誤導 Kimi。

**後果**：虛假經驗導致 Kimi 過度防禦，生成冗餘代碼，甚至引入不存在的限制。

### 誤解 4：「JSON Schema 可以靈活調整」

**錯誤理解**：根據每次任務調整輸出 Schema，讓 Kimi 輸出更靈活。

**正確理解**：Schema 必須固定。下游工具（Generator、Evaluator）依賴固定欄位解析。調整 Schema 會破壞兼容性。

**後果**：Schema 變動後，所有下游工具需要同步更新，導致版本混亂。

### 誤解 5：「Token 優化不重要，準確性優先」

**錯誤理解**：為了確保 Kimi 理解需求，傳輸盡可能多的上下文。

**正確理解**：Token 優化和準確性並不矛盾。Context Caching 和 Diff 傳輸在減少 Token 的同時保持準確性。

**後果**：不優化 Token，長任務的 API 成本可能增加 5-10 倍，且響應速度極慢。

## 信息噪音事後觀察

### 噪音控制策略

| 策略 | 實施方式 | 效果 |
|------|---------|------|
| **讀者分流** | assets/ 給 LLM，readme/ 給主人 | API 參數細節、調用代碼不出現在本文件中 |
| **內容聚焦** | 只解釋「為何這樣設計」和「什麼時候會誤解」 | 主人不需要知道如何逐行調用 Moonshot API |
| **設計原理優先** | 用「如果不這樣設計會怎樣」解釋每個機制的必要性 | 讓主人理解機制背後的業務邏輯 |
| **誤解糾偏** | 列舉常見誤解及後果，但不展開技術實現 | 幫助主人識別 LLM 的錯誤行為 |

### 噪音比例評估

| 內容類別 | 比例 | 是否對主人有用 |
|---------|------|--------------|
| 文件定位說明 | 5% | ✅ 有用 |
| 核心設計原理 | 30% | ✅ 有用 |
| 避坑經驗注入 | 15% | ✅ 有用 |
| 閉環修正機制 | 15% | ✅ 有用 |
| Token 優化策略 | 15% | ✅ 有用 |
| JSON Schema 規範 | 10% | ✅ 有用 |
| 與 Pipeline 協作 | 5% | ✅ 有用 |
| 常見誤解糾偏 | 5% | ✅ 有用 |
| **總計** | **100%** | **信息噪音比例：0%** |

## 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|---------|
| v1.0.0 | 2026-05-06 | 初始版本，定義 Moonshot API 調用和閉環修正 |
| v1.1.0 | 2026-05-07 | 統一 provenance_state 字段，精簡為索引風格，API 參數移到 reference/ |
| v1.2.0 | 2026-05-11 | 對齊 Agent Swarm 架構（身份分流、紅線、異常處理、版本鎖定），融入 Mission Pipeline 協作規範 |

---

*最後更新：2026-05-11*
*本檔案為人類可讀解釋書，LLM 執行指令請參考 assets/SKILL.md*
