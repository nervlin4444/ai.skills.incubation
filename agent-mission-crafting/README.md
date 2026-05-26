---
title: Agent Mission Crafting - Human Readable Guide
name: agent-mission-crafting
description: Human-readable explanation of Generator design intent, think-first-then-act principle, batch output mechanism, error collection, Skill-Acquiring mandatory reference, appointment material specification, execution issue tagging.
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
  local_path: "{baseDir}/README.md"
  github_path: "agent-mission-crafting/README.md"
---

# Agent Mission Crafting 解釋書

## 文件定位

| 檔案 | 讀者 | 用途 |
|------|------|------|
| SKILL.md（根目錄） | LLM + 主人掃描 | 簡短描述，供 use_skill 建立 available_skill |
| SKILL.md（assets/） | LLM 執行 | 執行指令集：技術執行、分批次輸出、錯誤收集、問題標記 |
| SKILL.md（本檔，位於 readme/） | 主人 | 設計原理、先想好後實行、委任素材規範、執行問題標記 |

LLM 不讀取本檔案。本檔案僅供主人理解 Generator 技能的設計意圖。

## 為何需要這個技能？

當 Evaluator 批准 checklist 後，如果直接讓 LLM 執行：
- 可能一口氣輸出全部內容，導致截斷或丟失
- 遇到疑問時擅自決定，不詢問主人，導致返工
- 發現計劃錯誤時自行修正，不通知 coordinator，導致責任模糊
- 執行錯誤不記錄，下次重複踩坑
- 不查詢現有技能，憑空創造解決方案，成功率低

Mission Crafting 的設計目標是：**按照最終版 checklist 逐項執行，先想好後實行，分批次輸出，遇到疑問立即上報，錯誤記錄到 CORRECTION.md。**

## 核心設計原理

### 1. 「先想好，後實行」原則

**錯誤做法**：收到 checklist 後立即開始執行，邊做邊想。
**正確做法**：執行前強制確認 4 項：

| 確認項 | 說明 | 不解決的後果 |
|------|------|-------------|
| 讀取所有輸入檔案 | CHECKLIST.md / 原始需求 / PLANNER_REPORT / EVALUATOR_REPORT / SUGGESTION.md / CORRECTION.md | 遺漏 Evaluator 的置頂問題或 Planner 的預判 |
| 確認主人裁決項 | 檢查 checklist 中是否有「待主人確認」標記 | 擅自決定技術選型，導致與主人預期不符 |
| 理解 checklist 粒度 | 確認每個子任務的輸入、輸出、驗收標準 | 執行時發現「這步怎麼做」而頻繁打斷 |
| 預估輸出規模 | 估算總 token 數，決定分幾個批次 | 一口氣輸出導致截斷，後半內容丟失 |

**核心原則**：執行前的 5 分鐘思考，可以節省 50% 的返工時間。

### 2. 分批次輸出機制

當預估輸出 > 2000 tokens 時，強制分為 4 個批次：

| 批次 | 內容 | 驗收標準 |
|------|------|---------|
| 批次 1 | 框架與結構 | 目錄層級正確、欄位齊全 |
| 批次 2 | 核心邏輯 | 算法正確、邊界條件處理 |
| 批次 3 | 細節填充 | 格式對齊、字體統一、間距精確 |
| 批次 4 | 最終校驗 | 對照 checklist 逐項勾選 |

**為何需要分批次？**
- 防止截斷：LLM 輸出長度有限，分批次確保每段完整
- 便於驗收：每批次獨立可驗證，發現問題立即修正
- 降低認知負荷：主人可以分批審閱，而非一次性面對巨量內容

### 3. 遇到疑問處理原則

Generator 執行時會遇到 4 種情況：

| 情況 | 處理方式 | 輸出標記 |
|------|---------|---------|
| checklist 說清楚了 | 直接執行 | [EXECUTING] |
| checklist 沒說清楚，但 Evaluator 已置頂 | 按 Evaluator 的建議執行 | [FOLLOW-EVALUATOR] |
| checklist 沒說清楚，且無置頂 | **輸出 [QUESTION] 上報 coordinator** | [QUESTION] |
| 發現計劃錯誤（執行時才暴露） | **立即停止 → 記錄 CORRECTION.md → 上報 coordinator** | [PLAN-ERROR] |

**關鍵規則**：Generator **禁止**擅自決定。任何不確定的事項必須輸出 [QUESTION]，等待主人或 coordinator 回覆。

### 4. 錯誤收集與 CORRECTION.md 更新

Generator 是「第一線執行者」，最容易發現「計劃與現實的差距」。所有錯誤必須記錄：

| 錯誤類型 | 記錄位置 | 用途 |
|---------|---------|------|
| 計劃錯誤（Planner 遺漏） | CORRECTION.md + SUGGESTION.md | 供 Planner 下次改進 |
| 評估錯誤（Evaluator 漏檢） | CORRECTION.md + checklist.評估問題 | 供 Evaluator 下次改進 |
| 執行錯誤（Generator 自身） | CORRECTION.md + checklist.執行問題 | 供 Generator 下次改進 |

**累積價值**：CORRECTION.md 是團隊的「錯誤日誌」，累積後可分析「哪類問題最多」，針對性改進。

## Skill-Acquiring 強制引用（新增，解決 #17）

### 為何 Generator 必須查詢現有技能？

過去 Generator 遇到需求時直接憑空創造解決方案，導致：
- 重複造輪子（已有成熟技能卻不用）
- 技術選型錯誤（選了不穩定的方案）
- 成功率低（26.1% 社區技能含漏洞，自行創造風險更高）

**新規則**：Generator 在「先想好」階段，必須調用 agent-skill-acquiring 查詢現有技能。

### 查詢流程

```
收到 checklist
    |
    v
[強制] 調用 agent-skill-acquiring
    ├──→ 搜尋系統標註技能（最高信任）
    ├──→ 搜尋用戶技能清單
    ├──→ 搜尋供應商技能清單
    |
    v
匹配到成熟技能？
    ├──→ 是 → 引用並執行（成功率 +30%）
    └──→ 否 → 標記 [SKILL-NOT-FOUND] → 上報 coordinator
```

### 與 skill-improving 的關係

執行前必須查閱 SKILL_CORRECTIONS.md（由 skill-improving 維護）：
- 避免重複踩坑（上次已記錄的錯誤）
- 遵循最佳實踐（已驗證的方案）
- 提升執行穩定性

## 委任素材規範（新增，解決 #18）

### Generator 階段應收到的完整素材

當 coordinator 任命 Generator 時，必須傳遞以下素材（一字不改）：

| 素材 | 來源 | 用途 | 是否強制 |
|------|------|------|---------|
| CHECKLIST.md（最終版） | Planner + Evaluator 迭代後 | 執行藍圖 | ✅ 強制 |
| PLANNER_REPORT_{時間}.md | Planner | 理解設計意圖 | ✅ 強制 |
| EVALUATOR_REPORT_{時間}.md | Evaluator | 理解已解決的問題與置頂項 | ✅ 強制 |
| SUGGESTION.md | 前輪累積 | 了解 Planner 缺口歷史 | ⚠️ 如有則必讀 |
| CORRECTION.md | 歷史累積 | 避免重複踩坑 | ⚠️ 如有則必讀 |
| 原始需求 | 主人輸入 | 對照需求確保不偏差 | ✅ 強制 |
| P0 禁止清單 | SKILL_CORRECTIONS.md | 確保執行過程不觸碰紅線 | ✅ 強制 |
| 角色定義 | 任命書 | 確認本次執行範圍 | ✅ 強制 |
| 層級標記 | L1 | 確認權限範圍 | ✅ 強制 |
| 家族手冊確認 | 5 項強制勾選 | bootstrap + conversation + coordination + corrections + skill-acquiring | ✅ 強制 |
| **任務性質** | **任命書** | **新增 / 修改 / 優化 / 調查 / 整合** | **✅ 新增強制** |
| **目標描述** | **任命書** | **具體要達成什麼（可驗證的標準）** | **✅ 新增強制** |

**關鍵改進（v1.2.0）**：
- 新增「任務性質」欄位：Generator 必須知道是「從零新增」還是「修改現有」，這決定了技術方案
- 新增「目標描述」欄位：必須是可驗證的標準（如「視覺保真度 85%」），而非模糊的「做好一點」

### 素材不足時的處理

若任命書缺少「任務性質」或「目標描述」：
1. 輸出 [QUESTION] 要求 coordinator 補充
2. 禁止擅自假設（例如假設是「修改」而實際是「新增」）

## 執行問題標記（新增，解決 #19）

### 技術錯誤如何標記於 checklist？

Generator 執行時發現技術錯誤（如腳本不存在、API 返回異常、邊界條件未處理），必須：

1. **標記 checklist**：在對應子任務的「執行問題」欄位記錄
2. **記錄 CORRECTION.md**：錯誤描述 + 影響 + 修正方案 + 預防措施
3. **輸出 [EXECUTION-ISSUE]**：上報 coordinator，由 coordinator 決定是否返回 Planner 修正

### 執行問題 vs SUGGESTION.md

| 錯誤類型 | 誰造成 | 標記位置 | 是否上報 Planner |
|---------|--------|---------|----------------|
| 計劃問題 | Planner 遺漏 | SUGGESTION.md + checklist.計劃問題 | 是（返回 Planner） |
| 評估問題 | Evaluator 漏檢 | checklist.評估問題 | 是（返回 Evaluator） |
| **執行問題** | **Generator 自身** | **checklist.執行問題** | **否（Generator 自行修正）** |

**關鍵區分**：
- 如果是「Planner 沒說清楚導致執行困難」→ 計劃問題 → 追加 SUGGESTION.md → 返回 Planner
- 如果是「Generator 自己寫錯代碼」→ 執行問題 → 標記 checklist.執行問題 → Generator 自行修正

### 真實案例：analyze_exchange_rate.py 腳本不存在（0510 執行）

**錯誤處理（過去）**：
Generator 發現腳本不存在，自行建立 analyze_exchange_rate.py，未上報 coordinator。
→ 違反紅線：擅自修改計劃。

**正確處理（v1.2.0）**：
1. Generator 發現腳本不存在 → 輸出 [PLAN-ERROR]
2. 記錄 CORRECTION.md：「checklist 要求執行 analyze_exchange_rate.py，但腳本不存在」
3. 上報 coordinator：「執行時發現計劃錯誤：腳本缺失，建議 Planner 修正 checklist」
4. coordinator 決定：返回 Planner 補充腳本生成步驟，或主人裁決允許 Generator 建立

## 反覆論證中的 Generator 角色

在 Mission Pipeline 中，Generator 不是「一次性執行」，而是可能參與多輪：

| 輪次 | Generator 的角色 | 動作 |
|------|----------------|------|
| R9-R10 | 首次執行 | 按照最終版 checklist 執行，輸出 [EXECUTING] |
| R11 | Evaluator QC 後 | 接收 Evaluator 的優點保留 / 缺點更正，修正後重新交付 |
| R12+ | 最終交付 | 所有問題解決後，輸出 [CRAFTING-COMPLETE] |

**關鍵規則**：
- Generator 只接收「最終版 checklist」（經 Evaluator 批准）
- Generator 不參與 Planning/Evaluating 階段的反覆論證
- Generator 的輸出由 Evaluator 進行最終 QC

## 與其他技能的關係

### 架構定位

| 技能 | 角色 | 說明 |
|------|------|------|
| agent-harness-engineering | 架構總圖 | 定義全部技能集合的 LAYER 0-4 架構 |
| agent-bootstrap | 唯一進入口 | 強制第一個載入，鎖定執行鏈順序 |
| agent-conversation-mode | 持續記錄器 | 記錄 crafting 階段的執行進度 |
| agent-coordination-mode | 任務路由器 | 傳遞最終版 checklist 給 Generator，回收 GENERATOR_REPORT |
| agent-mission-planning | 任務拆解者 | 生成 checklist，Generator 按此執行 |
| agent-mission-evaluating | 質量驗證者 | 批准 checklist，QC Generator 輸出 |
| **agent-mission-crafting** | **技術執行者** | **本技能。按照 checklist 逐項執行，分批次輸出，錯誤記錄** |
| agent-mission-finishing | 收尾交付者 | 填充最終六個欄位，最終交付 |
| agent-skill-acquiring | 技能搜尋者 | Generator 執行前強制查詢 |
| agent-skill-improving | 技能改進者 | 維護 SKILL_CORRECTIONS.md，Generator 執行前查閱 |

### 與 Evaluator 的協作關係

- Generator 接收 Evaluator 批准的 checklist（非初版）
- Generator 執行後，Evaluator 進行最終 QC
- Generator 必須回應 Evaluator 的 QC 發現（優點保留 / 缺點更正）

### 與 Planner 的協作關係

- Generator **禁止**直接與 Planner 溝通（必須通過 coordinator）
- 若發現 Planner 缺口，追加到 SUGGESTION.md，由 coordinator 傳遞給 Planner
- Generator 不修改 checklist（這是 Planner 的職責）

## 常見誤解糾偏（重要）

### 誤解 1：「Generator 只需要『做』，不需要『想』」

**錯誤理解**：收到 checklist 後立即執行，邊做邊調整。

**正確理解**：Generator 必須「先想好，後實行」。執行前確認 4 項：輸入檔案、主人裁決項、checklist 粒度、輸出規模。

**後果**：如果不先想好，可能遺漏 Evaluator 的置頂問題，導致執行偏差。

### 誤解 2：「Generator 可以一口氣輸出全部內容」

**錯誤理解**：為了效率，一次性輸出所有內容。

**正確理解**：輸出 > 2000 tokens 時必須分 4 個批次，每批次獨立可驗證。

**後果**：一口氣輸出容易截斷，後半內容丟失，導致交付不完整。

### 誤解 3：「Generator 遇到疑問可以自行決定」

**錯誤理解**：為了不麻煩主人，遇到不確定的事自己決定。

**正確理解**：Generator **禁止**擅自決定。任何不確定的事項必須輸出 [QUESTION]，等待回覆。

**後果**：擅自決定可能導致技術選型錯誤，最終交付與主人預期不符，返工成本極高。

### 誤解 4：「Generator 發現計劃錯誤可以自行修正」

**錯誤理解**：發現腳本不存在或方案不可行時，自己改一個更好的方案。

**正確理解**：Generator **禁止**擅自修正計劃。必須停止執行，記錄 CORRECTION.md，上報 coordinator。

**後果**：自行修正會破壞責任鏈。如果修正後出錯，無法判斷是「Planner 計劃錯」還是「Generator 修正錯」。

### 誤解 5：「Generator 不需要查詢現有技能」

**錯誤理解**：Generator 有足夠能力自行創造任何解決方案。

**正確理解**：Generator 執行前**必須**調用 agent-skill-acquiring 查詢現有技能，引用成熟方案。

**後果**：憑空創造解決方案成功率低，且可能引入漏洞（26.1% 社區技能含漏洞，自行創造風險更高）。

### 誤解 6：「Generator 的錯誤不需要記錄」

**錯誤理解**：執行錯誤自己修正就好，不需要記錄到 CORRECTION.md。

**正確理解**：所有錯誤（計劃問題、評估問題、執行問題）必須記錄到 CORRECTION.md，供團隊累積改進。

**後果**：不記錄錯誤，下次執行相同類型任務時會重複踩坑，團隊無法進步。

## 信息噪音事後觀察

### 噪音控制策略

| 策略 | 實施方式 | 效果 |
|------|---------|------|
| 讀者分流 | assets/ 給 LLM，readme/ 給主人 | LLM 執行細節不出現在本文件中 |
| 內容聚焦 | 只解釋「為何這樣設計」和「什麼時候會誤解」 | 主人不需要知道 Generator 如何逐行寫代碼 |
| 案例驅動 | 用真實項目（PDF to HTML、currency-exchange-tracker）展示執行過程 | 讓主人理解 Generator 的執行風險點 |
| 設計原理優先 | 用「如果不這樣設計會怎樣」解釋每個機制的必要性 | 讓主人理解機制背後的業務邏輯 |
| 誤解糾偏 | 列舉常見誤解及後果，但不展開技術實現 | 幫助主人識別 LLM 的錯誤行為 |

### 噪音比例評估

| 內容類別 | 比例 | 是否對主人有用 |
|---------|------|--------------|
| 文件定位說明 | 3% | ✅ 有用 |
| 核心設計原理 | 25% | ✅ 有用 |
| Skill-Acquiring 強制引用 | 12% | ✅ 有用 |
| 委任素材規範 | 15% | ✅ 有用 |
| 執行問題標記 | 12% | ✅ 有用 |
| 反覆論證角色 | 10% | ✅ 有用 |
| 與其他技能關係 | 10% | ✅ 有用 |
| 常見誤解糾偏 | 10% | ✅ 有用 |
| 信息噪音觀察 | 3% | ✅ 有用 |
| **總計** | **100%** | **信息噪音比例：0%** |

**結論**：本文件對目標讀者（主人）的信息噪音比例為 **0%**。所有內容均圍繞「理解執行設計意圖」「掌握委任素材規範」「識別 Generator 常見錯誤」展開，無 LLM 執行細節、無代碼示例、無技術規範干擾。

## 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|---------|
| v1.0 | 2026-05-01 | 初始版本，定義技術執行與分批次輸出 |
| v1.1 | 2026-05-06 | 加入「先想好後實行」原則、錯誤收集機制 |
| v1.1.1 | 2026-05-10 | 加入信息噪音事後觀察；融入 PDF to HTML 真實案例；frontmatter description 改為單行 |
| v1.2.0 | 2026-05-11 | 新增 Skill-Acquiring 強制引用（#17）、委任素材規範（任務性質/目標描述，#18）、執行問題標記機制（#19） |

---

*最後更新：2026-05-11*
*本檔案為人類可讀解釋書，LLM 執行指令請參考 assets/SKILL.md*
