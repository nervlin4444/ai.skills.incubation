---
title: Agent Coordination Mode - Human Readable Guide
name: agent-coordination-mode
description: Human-readable explanation of the coordination mode design intent, appointment mechanism, Mission Pipeline orchestration, and P0 banlist sourcing.
version: v1.3.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T09:26:53+08:00
fixes: []
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/README.md"
  github_path: "agent-coordination-mode/README.md"
---

# Agent Coordination Mode 解釋書

## 文件定位

| 檔案 | 讀者 | 用途 |
|------|------|------|
| SKILL.md（根目錄） | LLM | 執行指令集：路由判斷 + 任命流程 + 層級限制 |
| SKILL.md（本檔，位於 readme/） | 主人 | 設計原理、任命書規範、委任流程腳本化說明 |
| reference/ROUTING_RULES.md | 主人/開發者 | 路由規則的技術細節與邊界條件 |
| reference/ASSIGNMENT_TEMPLATE.md | 主人/開發者 | 任命書的標準模板與欄位說明 |
| reference/SUB_AGENT_PROTOCOLS.md | 主人/開發者 | Sub-Agent 通訊協議與狀態機 |

LLM 不讀取本檔案。本檔案僅供主人理解協調模式的設計意圖與任命機制。

## 為何需要這個技能？

當用戶輸入一個複雜任務時，Main Agent 面臨兩個核心問題：
1. **誰來做？** — 任務應該直接回覆，還是需要拆解為多個子任務由專家執行？
2. **怎麼管？** — 多個 Sub-Agent 之間如何傳遞信息、如何確保不丟失上下文、如何防止層級失控？

Coordination Mode 的設計目標是：**Main Agent 是「郵差 + 任命官」，不是「大腦」。** 它只負責判斷任務類型、任命合適的專家、傳遞完整的素材，絕不修改需求或評估輸出。

## 核心原則設計原理

| 原則 | 設計意圖 | 如果不這樣做會怎樣 |
|------|---------|------------------|
| **「你」字判斷** | 簡單任務（含「你」）直接回覆，複雜任務（不含「你」）啟動 Pipeline | 所有任務都走 Pipeline，浪費時間；或簡單任務過度拆解 |
| **郵差不修改** | Main Agent 傳遞原始需求時一字不改 | 需求在傳遞過程中被扭曲，Sub-Agent 執行錯誤方向 |
| **硬性兩層** | L1 可召喚 L2，L2 禁止召喚 L3（需申請） | 層級無限嵌套，Agent 數量爆炸，協調成本指數增長 |
| **委任書詳盡** | 任命書必須包含專家模擬、驗察需求、P0 清單、任務性質 | Sub-Agent 收到空泛任命，無法準確執行，反覆詢問 |
| **腳本化流轉** | 委任狀、checklist、report 均通過腳本統一管理 | 文件散落各處，版本混亂，coordinator 無法回收 |

## 「你」字判斷的設計原理

### 問題

用戶輸入的任務有時很簡單（「幫我查一下今天天氣」），有時很複雜（「設計一個新的庫存調撥系統」）。如果所有任務都走 Mission Pipeline，簡單任務會被過度拆解；如果都直接回覆，複雜任務會因缺乏規劃而失敗。

### 解決方案

用「你」字作為簡易判斷器：

| 輸入類型 | 示例 | 判定 | 處理方式 |
|----------|------|------|----------|
| **含「你」** | 「你覺得這個方案怎樣？」「你能幫我解釋一下嗎？」 | 簡單任務 | 直接回覆，不啟動 Pipeline |
| **不含「你」** | 「設計一個庫存調撥系統」「更新所有技能的版本號」 | 複雜任務 | 啟動 Mission Pipeline，任命專家 |
| **手動覆蓋** | 「啟動 Pipeline」「直接回覆」 | 用戶強制 | 覆蓋「你」字判斷 |

**為何用「你」字？**

因為含「你」的輸入通常是「詢問意見」「請求解釋」「確認理解」，這類任務不需要拆解為子任務。而不含「你」的輸入通常是「指令」「要求產出」「系統性修改」，這類任務需要規劃、評估、執行、收尾。

**局限性**：「分析這份報告」不含「你」但很簡單。此時用戶可手動覆蓋（「直接回覆」）。

## 委任流程腳本化（新增 v1.3.0）

### 核心事實：委任不是「複製貼上」，而是「結構化任命」

過去的問題：Main Agent 收到任務後，直接把用戶輸入複製到任命書裡傳給 Sub-Agent。這導致 Sub-Agent 收到的是「原始需求」，而不是「可執行的任命」。

正確的委任流程必須通過**腳本統一管理**，確保每個環節都有明確的產出與回收機制。

### 委任流程圖（腳本化版本）

    用戶輸入任務
        |
        v
    Main Agent（L0）判斷「你」字 → 複雜任務
        |
        v
    【腳本】create_appointment.py
        生成委任狀：APPOINTMENT_{任務ID}_{角色}.md
        內容包含：原始需求 + P0 禁止清單 + 專家模擬 + 驗察需求 + 任務性質
        |
        v
    任命 Planner L1（戰略大師）
        傳遞：委任狀 + 家族手冊確認
        |
        v
    Planner L1 執行 → 生成 CHECKLIST.md + PLANNER_REPORT_{時間}.md
        |
        v
    【腳本】complete_appointment.py
        Planner 調用，將 CHECKLIST.md + PLANNER_REPORT 回傳 coordinator
        統一存放到 user skill assets 目錄
        |
        v
    Main Agent（L0）接收產出
        不做任何修改
        |
        v
    【腳本】create_appointment.py
        生成新委任狀：Evaluator L1
        傳遞：CHECKLIST.md（Planner 產出，一字不改）+ 原始需求 + 評估標準
        |
        v
    Evaluator L1 執行 → 生成 EVALUATOR_REPORT_{時間}.md
        |
        v
    【腳本】complete_appointment.py
        Evaluator 調用，將 EVALUATOR_REPORT 回傳 coordinator
        |
        v
    （反覆論證階段：Planner ↔ Evaluator，直到達成共識）
        每次反覆均由 coordinator 通過腳本重新委任
        |
        v
    達成共識後 → 任命 Generator L1
        傳遞：最終版 CHECKLIST.md + EVALUATOR_REPORT + 原始需求 + 經驗約束
        |
        v
    Generator L1 執行 → 生成產出 + GENERATOR_REPORT_{時間}.md
        |
        v
    【腳本】complete_appointment.py
        Generator 調用，將產出 + GENERATOR_REPORT 回傳 coordinator
        |
        v
    任命 Finishing L1
        傳遞：所有產出 + CHECKLIST.md + 原始需求
        |
        v
    Finishing L1 執行 → 最終交付
        |
        v
    【腳本】mission_complete.py
        標記任務完成，歸檔所有 report 到 user skill assets 目錄

### 關鍵改進（相對於 v1.2.0）

| 改進項 | v1.2.0（舊） | v1.3.0（新） | 解決問題 |
|--------|-------------|-------------|----------|
| 委任狀生成 | 手寫文字，無固定格式 | **腳本 create_appointment.py 統一生成** | #5 任命書過於簡陋 |
| 委任狀內容 | 僅複製原始需求 | **增加專家模擬、驗察需求、P0 清單、任務性質** | #5、#9 |
| Planner 產出 | 僅 CHECKLIST.md | **CHECKLIST.md + PLANNER_REPORT_{時間}.md** | #13 混亂 |
| Evaluator 產出 | 臨時 evaluator.md | **EVALUATOR_REPORT_{時間}.md** | #16 臨時創造物 |
| Generator 產出 | 直接輸出 | **產出 + GENERATOR_REPORT_{時間}.md** | #13、#18 |
| 產出回收 | 無統一機制 | **complete_appointment.py 統一回傳** | #13 混亂 |
| 文件存放 | 散落各處（Claw/assets/） | **統一放到 user skill assets 目錄** | #20、#22 |

## 任命書詳盡規範（新增 v1.3.0）

### 任命書必須包含的 8 個欄位

任命書不是「複製貼上」，而是結構化的任務定義。以下 8 個欄位缺一不可：

| 欄位 | 說明 | 示例 |
|------|------|------|
| **1. 原始需求** | 用戶輸入一字不改 | 「請執行 currency-exchange-tracker 技能，追蹤 HKD/CNY 匯率」 |
| **2. 任務性質** | 新增 / 修改 / 優化 / 調查 / 整合 | 「修改現有技能，更新版本號並加入新功能」 |
| **3. 目標描述** | 具體要達成什麼 | 「將 agent-conversation-mode 從 v3.2.0 升級到 v3.3.1，加入主動備份機制」 |
| **4. P0 禁止清單** | 從 SKILL_CORRECTIONS.md 提取的絕對禁止項 | 「禁止修改 SOUL.md / 禁止 hardcode 值 / 禁止跳過 skills」 |
| **5. 專家模擬** | 這個角色需要模擬什麼類型的專家 | 「戰略大師：具備系統分析師背景，擅長將複雜需求拆解為可執行子任務」 |
| **6. 驗察需求** | 執行過程中需要特別驗證什麼 | 「驗證 checklist 的可完成率是否 ≥ 80% / 驗證子任務粒度是否適中」 |
| **7. 注意事項** | 這個任務的特殊風險或歷史教訓 | 「上次執行時發現腳本不存在，本次需先確認技能包完整性」 |
| **8. 家族手冊確認** | 必須載入的技能清單 | 「agent-bootstrap + agent-conversation-mode + agent-coordination-mode + agent-mission-planning」 |

### 為何需要「專家模擬」？

Sub-Agent 不是通用 AI，而是「被任命的專家」。如果任命書只說「你是 Planner」，Sub-Agent 可能以為自己只是「寫清單的人」。但如果任命書說「你是一位具備系統分析師背景的戰略大師，擅長將複雜需求拆解為可執行子任務，並預判技術風險」，Sub-Agent 會以更高的標準執行。

### 為何需要「驗察需求」？

過去的問題：Evaluator 收到 checklist 後，不知道該驗證什麼，只能泛泛地說「看起來可以」。如果在任命書中就明確「驗證 checklist 的可完成率是否 ≥ 80%」「驗證子任務粒度是否適中（每個子任務 30 字以內描述）」，Evaluator 會有明確的檢查標準。

### 為何需要「注意事項」？

每個任務都有歷史教訓。如果上次執行時發現「腳本不存在」「路徑寫錯」「API 密鑰過期」，這些信息必須傳遞給下一個專家，避免重複踩坑。

## P0 禁止清單的來源（新增 v1.3.0）

### 問題

過去的任命書中，P0 禁止清單寫「從 SKILL_CORRECTIONS.md 提取」。但實際執行時，Agent 經常：
- 不知道 SKILL_CORRECTIONS.md 在哪裡
- 提取了錯誤的內容（把整個文件複製過去，而不是提取當前適用的禁止項）
- 憑空創造禁止項（自己編造「禁止修改 XXX」）

### 解決方案

P0 禁止清單的**唯一合法來源**：

| 來源文件 | 內容 | 提取方式 |
|----------|------|----------|
| **SKILL_CORRECTIONS.md** | 通用技能錯誤模式（如「禁止修改 SOUL.md」「禁止 hardcode 值」） | 讀取文件 → 提取與當前任務相關的禁止項 |
| **SCRIPT_CORRECTIONS.md** | 腳本相關錯誤模式（如「禁止創建臨時 .py」「禁止用反斜線硬編碼路徑」） | 讀取文件 → 提取與當前任務相關的禁止項 |
| **歷史 CORRECTION.md** | 本次會話或上次會話累積的錯誤記錄 | 讀取 assets/CORRECTION.md → 提取未解決的錯誤項 |

**禁止行為**：
- 禁止憑空創造 P0 禁止項（Agent 自己編造）
- 禁止複製整個 SKILL_CORRECTIONS.md（只提取相關項）
- 禁止忽略歷史 CORRECTION.md（上次踩的坑這次必須避開）

**腳本化提取**：

理想情況下，應由腳本 `extract_p0_banlist.py` 統一提取：

```
輸入：任務描述 + 相關技能名稱
處理：
  1. 讀取 SKILL_CORRECTIONS.md → 匹配關鍵詞 → 提取相關禁止項
  2. 讀取 SCRIPT_CORRECTIONS.md → 匹配關鍵詞 → 提取相關禁止項
  3. 讀取 assets/CORRECTION.md → 提取未解決項
輸出：結構化 P0 清單（Markdown 列表）
```

## 委任素材清單（新增 v1.3.0）

### 每個階段傳遞給 Sub-Agent 的素材

**任命 Planner L1 時傳遞**：
- 委任狀（APPOINTMENT_{任務ID}_PLANNER.md）
- 原始需求（一字不改）
- P0 禁止清單（從上述來源提取）
- 家族手冊確認（必須載入的技能清單）

**任命 Evaluator L1 時傳遞**：
- 委任狀（APPOINTMENT_{任務ID}_EVALUATOR.md）
- CHECKLIST.md（Planner 產出，一字不改）
- 原始需求（一字不改）
- PLANNER_REPORT_{時間}.md（Planner 的執行報告）
- 評估標準（來自委任狀的「驗察需求」欄位）

**任命 Generator L1 時傳遞**：
- 委任狀（APPOINTMENT_{任務ID}_GENERATOR.md）
- 最終版 CHECKLIST.md（經 Evaluator 批准）
- EVALUATOR_REPORT_{時間}.md（Evaluator 的評估報告）
- 原始需求（一字不改）
- 經驗約束（SKILL_CORRECTIONS.md + SCRIPT_CORRECTIONS.md 相關項）
- 歷史 CORRECTION.md（本次會話累積的錯誤）

**任命 Finishing L1 時傳遞**：
- 委任狀（APPOINTMENT_{任務ID}_FINISHING.md）
- 所有產出（Generator 的執行結果）
- GENERATOR_REPORT_{時間}.md（Generator 的執行報告）
- 最終版 CHECKLIST.md
- 原始需求（一字不改）

### 素材傳遞規則

| 規則 | 說明 |
|------|------|
| **一字不改** | 原始需求、CHECKLIST.md、各 REPORT 傳遞時禁止任何修改 |
| **相對路徑** | 所有文件引用使用相對路徑，禁止絕對路徑 |
| **統一目錄** | 所有委任狀與報告放在 user skill assets 目錄 |
| **時間戳命名** | REPORT 文件必須包含 {時間}，避免覆蓋 |

## 產出文件命名規範（新增 v1.3.0）

所有由 coordination-mode 管理或產生的文件，必須遵循以下命名規則：

| 文件類型 | 命名格式 | 示例 |
|----------|----------|------|
| 委任狀 | `APPOINTMENT_{任務ID}_{角色}.md` | `APPOINTMENT_T20260510_PLANNER.md` |
| Planner 報告 | `PLANNER_REPORT_{YYYYMMDD_HHMMSS}.md` | `PLANNER_REPORT_20260510_143022.md` |
| Evaluator 報告 | `EVALUATOR_REPORT_{YYYYMMDD_HHMMSS}.md` | `EVALUATOR_REPORT_20260510_143022.md` |
| Generator 報告 | `GENERATOR_REPORT_{YYYYMMDD_HHMMSS}.md` | `GENERATOR_REPORT_20260510_143022.md` |
| 任務完成標記 | `MISSION_COMPLETE_{任務ID}.md` | `MISSION_COMPLETE_T20260510.md` |

**禁止**：
- 禁止使用 `evaluator.md` 這類無時間戳的臨時文件名（#16 問題）
- 禁止把文件寫入 Claw/assets/ 或家目錄（#2、#20 問題）
- 禁止大小寫混用（`CHECKLIST.md` vs `checklist.md`）

## 與其他技能的關係

### 架構定位

| 技能 | 角色 | 說明 |
|------|------|------|
| agent-harness-engineering | 架構總圖 | 定義全部技能集合的 LAYER 0-4 架構 |
| agent-bootstrap | 唯一進入口 | 強制第一個載入，鎖定執行鏈順序 |
| agent-conversation-mode | 持續記錄器 | 記錄路由決策與任命過程 |
| **agent-coordination-mode** | **任務路由器 + 專家任命者** | **本技能。判斷任務類型，任命 Sub-Agent，傳遞素材** |
| agent-mission-planning | 戰略大師 | 拆解任務為 checklist |
| agent-mission-evaluating | 專業調查員 | 驗證 checklist 可執行性 |
| agent-mission-crafting | 系統工程師 | 執行子任務 |
| agent-mission-finishing | 收尾專員 | 最終交付 |

### 與 conversation-mode 的交互

每次任命、每次接收產出、每次階段切換，都必須記錄到 conversation.md：

| 時機 | 記錄內容 |
|------|----------|
| 路由決策後 | `[COORDINATION] 任務判定：{簡單/複雜}，{直接回覆/啟動 Pipeline}` |
| 任命 Sub-Agent 後 | `[APPOINTMENT] L{層級} {角色} 已任命，任務：{摘要}` |
| 接收產出後 | `[L0] 接收 {角色} 產出，轉交 {下一角色}` |
| 反覆論證時 | `[COORDINATION] Planner ↔ Evaluator 第 {輪次} 輪，狀態：{進行中/達成共識}` |

### 與各 Mission Pipeline 節點的關係

 coordination-mode 不執行實質任務，只做「郵差」：

| 節點 | coordination-mode 的動作 | 禁止的行為 |
|------|--------------------------|------------|
| Planner | 傳遞原始需求 + P0 清單 + 委任狀 | 修改需求、幫忙拆解任務 |
| Evaluator | 傳遞 CHECKLIST.md + 原始需求 | 修改 checklist、幫忙評估 |
| Generator | 傳遞最終版 checklist + 經驗約束 | 修改 checklist、幫忙執行 |
| Finishing | 傳遞所有產出 + 原始需求 | 修改產出、幫忙收尾 |

## 常見誤解糾偏

### 誤解 1：「協調者是大腦，可以修改需求」

**錯誤理解**：Main Agent 收到任務後，會「理解」需求，然後把「理解後的版本」傳給 Planner。

**後果**：Planner 執行的是 Main Agent 的理解，而不是用戶的真實需求。如果用戶說「幫我修改這個檔案」，Main Agent 理解為「幫我優化這個檔案」，Planner 就會朝優化方向執行，而不是修改。

**正確理解**：Main Agent 是「郵差」，只傳遞不修改。原始需求必須一字不改地傳遞給 Planner。

### 誤解 2：「任命書只需要複製原始需求」

**錯誤理解**：任命書寫「你的任務是：{原始需求}」就夠了。

**後果**：Sub-Agent 不知道自己是什麼類型的專家、需要驗證什麼、有什麼歷史教訓。執行時頻繁反問 Main Agent，效率低下。

**正確理解**：任命書必須包含 8 個欄位（見上文），特別是「專家模擬」「驗察需求」「注意事項」。

### 誤解 3：「P0 禁止清單可以憑空創造」

**錯誤理解**：Agent 根據自己的理解編造幾條「禁止項」。

**後果**：禁止項可能與 SKILL_CORRECTIONS.md 不一致，或遺漏關鍵禁止項（如「禁止修改 SOUL.md」）。

**正確理解**：P0 禁止清單必須從 SKILL_CORRECTIONS.md、SCRIPT_CORRECTIONS.md、歷史 CORRECTION.md 提取，禁止憑空創造。

### 誤解 4：「產出文件隨便放，能找到就行」

**錯誤理解**：Planner 把 checklist 寫到 Claw/assets/，Evaluator 把報告寫到家目錄，Generator 把產出寫到臨時目錄。

**後果**：coordinator 無法統一回收，Finishing 找不到文件，主人無法追溯。

**正確理解**：所有產出必須通過腳本統一管理，放在 user skill assets 目錄，使用相對路徑。

## 版本鎖定說明

🔒 LOCK v1.3.0 PERMANENT — 路由規則（「你」字判斷）與層級限制機制禁止修改。

如需調整，必須經用戶（主人）直接授權。LLM 無權自行修改。

---

*最後更新：2026-05-11*
*本檔案為人類可讀解釋書，LLM 執行指令請參考根目錄 SKILL.md*
*詳細路由規則見 reference/ROUTING_RULES.md*
*溝通協議見 reference/SUB_AGENT_PROTOCOLS.md*
*任命模板見 reference/ASSIGNMENT_TEMPLATE.md*
