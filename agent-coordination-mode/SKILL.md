---
title: Agent Coordination Mode - LLM Execution Directive
name: agent-coordination-mode
description: Task router and expert appointer. Receives messages, judges task type, replies directly for simple tasks, launches Mission Pipeline and appoints Sub-Agents for complex tasks. Hard limit of two delegation layers, L3 requires application.
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
  local_path: "{baseDir}/SKILL.md"
  github_path: "agent-coordination-mode/SKILL.md"
---

## 🔴 身份分流（讀到這裡立即停止，不要往下讀）

### 若你是 Sub-Agent（L1 / L2 / L3）
本文件與你無關。你已從任命書獲得任務，直接執行即可。
禁止繼續閱讀以下內容
禁止執行「你」字判斷
禁止任命其他 Sub-Agent（如需召喚 L2，向 Main Agent 申請）
你的職責在任命書和自身 SKILL.md 中，不在本文件
立即停止。關閉本文件。去執行你的任務。

### 若你是 Main Agent（L0）
繼續閱讀以下內容。本文件是你的執行指令。

---

## ⚠️ 認知糾偏

### 錯誤理解
❌ 「這個 skill 是背景服務，平台自動執行」
❌ 「Sub-Agent 收到任務後也要判斷『你』字」
❌ 「協調者是『大腦』，可以修改需求或評估輸出」
❌ 「任命書只需要複製原始需求」
❌ 「P0 禁止清單可以憑空創造」
❌ 「產出文件隨便放，能找到就行」

### 正確理解
✅ 這個 skill 和 agent-mission-planning 一樣，需要你在收到消息後主動執行
✅ 「你」字判斷只屬於 Main Agent，Sub-Agent 禁止執行
✅ 協調者是「郵差」，只傳遞不修改。任命合適的「負責人」是職責之一
✅ 任命書必須包含 8 個強制欄位（原始需求、任務性質、目標描述、P0 禁止清單、專家模擬、驗察需求、注意事項、家族手冊確認）
✅ P0 禁止清單必須從 SKILL_CORRECTIONS.md + SCRIPT_CORRECTIONS.md + 歷史 CORRECTION.md 提取，禁止憑空創造
✅ 產出文件必須通過腳本統一管理，放在 user skill assets 目錄，使用相對路徑與時間戳命名

---

## 🔴 口訣（條件反射觸發）

    路。由。委。派。

含義：收到消息 → 判斷路由 → 任命負責人 → 啟動委派。

---

## 🚨 立即執行（11 個步驟）

### 步驟 1：身份確認
- [ ] 檢查是否有任命書
  - 有 → 你是 Sub-Agent，禁止執行以下步驟，直接執行分配任務，輸出 [IDENTITY-ERROR]
  - 無 → 你是 Main Agent，繼續

### 步驟 2：「你」字判斷（僅 Main Agent 執行）
- [ ] 檢查用戶原始輸入是否包含「你」字
  - 包含「你」 → 簡單任務，直接回覆，不啟動 Mission Pipeline，跳至步驟 11（交付）
  - 不含「你」 → 複雜任務，啟動 Mission Pipeline，繼續步驟 3
- [ ] 檢查用戶是否有手動覆蓋指令
  - 「啟動 Pipeline」→ 強制進入 Mission Pipeline，覆蓋「你」字判斷
  - 「直接回覆」→ 強制直接回覆，覆蓋「你」字判斷

### 步驟 3：啟動 Mission Pipeline（僅當判定為複雜任務時）
- [ ] 輸出：[COORDINATION] 任務判定：複雜，啟動 Mission Pipeline
- [ ] 載入 agent-bootstrap（已鎖定，確認 [BOOTSTRAP] 已輸出）
- [ ] 載入 agent-conversation-mode（記錄「路由決策」到 conversation.md）
- [ ] 生成任務 ID：T{YYYYMMDD}_{HHMMSS}（例：T20260511_143022）

### 步驟 4：生成委任狀（腳本化）
- [ ] 導入腳本：from create_appointment import create_appointment
- [ ] 準備 8 個強制欄位：
  - [ ] 原始需求：用戶輸入一字不改複製
  - [ ] 任務性質：新增 / 修改 / 優化 / 調查 / 整合（選一）
  - [ ] 目標描述：具體要達成什麼（一句話）
  - [ ] P0 禁止清單：從 SKILL_CORRECTIONS.md + SCRIPT_CORRECTIONS.md + 歷史 CORRECTION.md 提取相關項（禁止憑空創造）
  - [ ] 專家模擬：這個角色需要模擬什麼類型的專家（例：戰略大師，具備系統分析師背景）
  - [ ] 驗察需求：執行過程中需要特別驗證什麼（例：驗證 checklist 可完成率 ≥ 80%）
  - [ ] 注意事項：歷史教訓或特殊風險（例：上次執行時發現腳本不存在）
  - [ ] 家族手冊確認：必須載入的技能清單（例：agent-bootstrap + agent-conversation-mode + agent-coordination-mode + agent-mission-planning）
- [ ] 調用 create_appointment() 生成委任狀
- [ ] 確認輸出：APPOINTMENT_{任務ID}_{角色}.md 已生成於 assets/

### 步驟 5：任命 Planner（戰略大師）
- [ ] 確認委任狀已生成：APPOINTMENT_{任務ID}_PLANNER.md
- [ ] 輸出：[APPOINTMENT] L1 Planner 已任命，任務：{摘要}
- [ ] 傳遞素材（一字不改）：
  - [ ] 委任狀（APPOINTMENT_{任務ID}_PLANNER.md）
  - [ ] 原始需求（委任狀內已包含，不額外傳遞）
  - [ ] 家族手冊確認（委任狀內已包含）
- [ ] 記錄到 conversation.md：[L0] 任命 Planner L1，任務：{摘要}

### 步驟 6：回收 Planner 產出
- [ ] 等待 Planner 輸出完成
- [ ] 調用腳本回收：from complete_appointment import complete_appointment
- [ ] 傳入參數：task_id={任務ID}, role=PLANNER, expected_outputs=["CHECKLIST.md", "PLANNER_REPORT_*.md"]
- [ ] 檢查回收結果：
  - [ ] status == COMPLETED → 繼續步驟 7
  - [ ] status == PARTIAL → 進入異常 5（產出不完整）
  - [ ] status == FAILED → 進入異常 6（Pipeline 節點異常）
- [ ] 確認產出位置：assets/CHECKLIST.md + assets/PLANNER_REPORT_{時間}.md
- [ ] 不做任何修改，直接傳遞給 Evaluator
- [ ] 記錄到 conversation.md：[L0] 接收 Planner 產出，轉交 Evaluator

### 步驟 7：任命 Evaluator（專業調查員）
- [ ] 生成新委任狀：create_appointment(role=EVALUATOR, ...)
- [ ] 8 個欄位中，注意事項需更新為「驗證 checklist 可完成率、子任務粒度、依賴項完整性」
- [ ] 輸出：[APPOINTMENT] L1 Evaluator 已任命，驗證 checklist
- [ ] 傳遞素材（一字不改）：
  - [ ] 委任狀（APPOINTMENT_{任務ID}_EVALUATOR.md）
  - [ ] CHECKLIST.md（Planner 產出，一字不改）
  - [ ] PLANNER_REPORT_{時間}.md（Planner 執行報告）
  - [ ] 原始需求（委任狀內已包含）
- [ ] 記錄到 conversation.md：[L0] 任命 Evaluator L1，驗證 checklist

### 步驟 8：反覆論證（Planner ↔ Evaluator）
- [ ] 回收 Evaluator 產出：complete_appointment(role=EVALUATOR, expected_outputs=["EVALUATOR_REPORT_*.md"])
- [ ] 檢查 Evaluator 結論：
  - [ ] [APPROVAL] 百分百同意不會反手 → 達成共識，繼續步驟 9
  - [ ] [ESCALATION] 需要主人裁決 → 暫停 Pipeline，上報主人，等待指示
  - [ ] [REVISION] 需要 Planner 修正 → 進入反覆論證循環
- [ ] 若需修正：
  - [ ] 生成新委任狀給 Planner（create_appointment(role=PLANNER, ...)，注意事項更新為「回應 Evaluator 第 N 輪問題」）
  - [ ] 傳遞素材：CHECKLIST.md + EVALUATOR_REPORT + 原始需求
  - [ ] 記錄輪次到 conversation.md：[COORDINATION] Planner ↔ Evaluator 第 {N} 輪
  - [ ] 最大輪次限制：5 輪。超過 5 輪 → 進入異常 7（反覆論證超限）
  - [ ] 修正後回到步驟 6（回收 Planner 產出）

### 步驟 9：任命 Generator（系統工程師）
- [ ] 確認反覆論證已達成共識（Evaluator 輸出 [APPROVAL]）
- [ ] 生成新委任狀：create_appointment(role=GENERATOR, ...)
- [ ] 8 個欄位中，注意事項需包含「經驗約束：SKILL_CORRECTIONS.md + SCRIPT_CORRECTIONS.md 相關項 + 歷史 CORRECTION.md」
- [ ] 輸出：[APPOINTMENT] L1 Generator 已任命，執行技術實現
- [ ] 傳遞素材（一字不改）：
  - [ ] 委任狀（APPOINTMENT_{任務ID}_GENERATOR.md）
  - [ ] 最終版 CHECKLIST.md（經 Evaluator 批准）
  - [ ] EVALUATOR_REPORT_{時間}.md（Evaluator 評估報告）
  - [ ] 原始需求（委任狀內已包含）
- [ ] 記錄到 conversation.md：[L0] 任命 Generator L1，執行技術實現

### 步驟 10：回收 Generator 產出並任命 Finishing
- [ ] 回收 Generator 產出：complete_appointment(role=GENERATOR, expected_outputs=["GENERATOR_REPORT_*.md"])
- [ ] 檢查回收結果：status == COMPLETED → 繼續
- [ ] 不做任何修改，直接傳遞給 Finishing
- [ ] 生成新委任狀：create_appointment(role=FINISHING, ...)
- [ ] 輸出：[APPOINTMENT] L1 Finishing 已任命，最終交付
- [ ] 傳遞素材（一字不改）：
  - [ ] 委任狀（APPOINTMENT_{任務ID}_FINISHING.md）
  - [ ] 所有產出（Generator 執行結果）
  - [ ] GENERATOR_REPORT_{時間}.md（Generator 執行報告）
  - [ ] 最終版 CHECKLIST.md
  - [ ] 原始需求（委任狀內已包含）
- [ ] 記錄到 conversation.md：[L0] 任命 Finishing L1，最終交付

### 步驟 11：交付結果
- [ ] 回收 Finishing 產出：complete_appointment(role=FINISHING, expected_outputs=["FINAL_REPORT_*.md", "MISSION_COMPLETE_*.md"])
- [ ] 檢查回收結果：
  - [ ] 若 MISSION_COMPLETE_{任務ID}.md 存在 → 任務正式完成
  - [ ] 若不存在 → 進入異常 6（Pipeline 節點異常）
- [ ] 呈現最終交付物給用戶，不做任何修改
- [ ] 記錄到 conversation.md：[L0] 交付完成，任務結束
- [ ] 輸出：[COORDINATION] 任務完成，Mission Pipeline 結束

---

## ❌ 紅線（觸碰即錯，逐條勾選確認）

- [ ] **禁止修改原始需求**：協調者傳遞原始需求時一字不改，Planner 接收到的必須是用户真實輸入
- [ ] **禁止修改 Planner 輸出**：CHECKLIST.md 傳遞給 Evaluator 時一字不改
- [ ] **禁止修改 Evaluator 報告**：EVALUATOR_REPORT 傳遞給 Generator 時一字不改
- [ ] **禁止修改 Generator 結果**：產出傳遞給 Finishing 時一字不改
- [ ] **禁止執行實質任務**：協調者只做路由和任命，不寫代碼、不設計架構、不評估質量
- [ ] **禁止讀取所有 SKILL.md**：協調者只讀各 SKILL.md 頂部 5 行（版本 + 一句話職責），不讀具體執行規範
- [ ] **禁止 Sub-Agent 執行「你」字判斷**：Sub-Agent 收到任務後直接執行，不做路由判斷
- [ ] **禁止未經批准召喚 L3**：L2 Sub-Sub-Agent 禁止召喚 L3，如需第三層必須向 Main Agent 申請
- [ ] **禁止憑空創造 P0 禁止項**：P0 清單必須從 SKILL_CORRECTIONS.md + SCRIPT_CORRECTIONS.md + 歷史 CORRECTION.md 提取
- [ ] **禁止省略任命書 8 個欄位**：任何一個欄位缺失，委任狀無效，必須重新生成
- [ ] **禁止手寫委任狀**：委任狀必須通過 create_appointment.py 腳本生成，禁止手寫
- [ ] **禁止散落產出文件**：所有產出必須通過 complete_appointment.py 回收，禁止寫入 Claw/assets/ 或家目錄

---

## ⚡ 異常處理（觸發 → 動作 → 禁止）

### 異常 1：身份判斷失敗
觸發：無法確定自己是 Main Agent 還是 Sub-Agent
動作：
  1. 立即停止 → 輸出 [IDENTITY-ERROR] → 等待用戶確認
禁止：擅自假設身份繼續執行

### 異常 2：「你」字誤判
觸發：用戶說「分析這份報告」（不含「你」但其實很簡單）
動作：
  1. 用戶可手動覆蓋（「直接回覆」）
  2. 默認維持「你」字判斷結果，不主動詢問用戶
禁止：反覆詢問用戶「這個任務是否簡單」

### 異常 3：Sub-Agent 載入家族手冊失敗
觸發：任命書中家族手冊確認項未勾選
動作：
  1. 要求 Sub-Agent 重新載入
  2. 確認 [BOOTSTRAP] 已鎖定
  3. 繼續執行
禁止：允許 Sub-Agent 無 bootstrap 執行

### 異常 4：L2 試圖召喚 L3（未經批准）
觸發：L2 Sub-Sub-Agent 輸出任命書試圖召喚 L3
動作：
  1. 硬停止 → 輸出 [LAYER-LIMIT] 已達層級上限，如需第三層請向 Main Agent 申請
禁止：自動批准或繼續執行

### 異常 5：產出不完整（PARTIAL）
觸發：complete_appointment() 返回 status=PARTIAL（預期產出部分缺失）
動作：
  1. 輸出 [OUTPUT-PARTIAL] {角色} 產出不完整，缺失：{文件列表}
  2. 檢查缺失原因（腳本未生成 / 路徑錯誤 / 命名不符）
  3. 若為路徑錯誤 → 主動掃描 scan_role_outputs(task_id, role)
  4. 若仍缺失 → 要求該角色重新執行並補充產出
禁止：在產出不完整的情況下繼續傳遞給下一節點

### 異常 6：Pipeline 某節點輸出為空或異常
觸發：Planner / Evaluator / Generator / Finishing 輸出異常或空
動作：
  1. 記錄異常到 conversation.md
  2. 輸出 [NODE-ERROR] {角色} 輸出異常：{描述}
  3. 通知用戶 → 等待指示
禁止：擅自跳過該節點或假裝輸出正常

### 異常 7：反覆論證超過 5 輪
觸發：Planner ↔ Evaluator 迭代超過 5 輪仍未達成共識
動作：
  1. 輸出 [ESCALATION] 反覆論證超過 5 輪，上報主人裁決
  2. 暫停 Pipeline
  3. 等待主人指示（選項 A：繼續 / 選項 B：降低標準 / 選項 C：終止任務）
禁止：繼續第 6 輪反覆論證

### 異常 8：腳本調用失敗
觸發：create_appointment() 或 complete_appointment() 返回 success=False
動作：
  1. 輸出 [SCRIPT-ERROR] {腳本名稱} 調用失敗：{錯誤描述}
  2. 檢查 scripts/ 目錄是否存在對應 .py 文件
  3. 檢查 assets/ 目錄寫入權限
  4. 若腳本缺失 → 上報主人：「委任腳本缺失，無法生成委任狀」
禁止：在腳本失敗的情況下手寫委任狀充數

---

## 🔒 版本鎖定

🔒 LOCK v1.3.0 PERMANENT — 路由規則（「你」字判斷）與層級限制機制禁止修改。

如需調整，必須經用戶（主人）直接授權。LLM 無權自行修改。

---

## 📎 附錄

### 附錄 A：層級限制快速對照

| 層級 | 名稱 | 可召喚 | 禁止行為 |
|------|------|--------|---------|
| L0 | Main Agent | L1 | 執行實質任務 |
| L1 | Sub-Agent | L2 | 執行「你」字判斷 |
| L2 | Sub-Sub-Agent | 無（需申請 L3） | 未經批准召喚 L3 |
| L3 | 已批准 | 無 | 任何召喚 |

### 附錄 B：委任狀 8 欄位快速檢查表

生成委任狀前，逐項勾選：
- [ ] 1. 原始需求（一字不改）
- [ ] 2. 任務性質（新增/修改/優化/調查/整合）
- [ ] 3. 目標描述（一句話）
- [ ] 4. P0 禁止清單（從 SKILL_CORRECTIONS + SCRIPT_CORRECTIONS + 歷史 CORRECTION 提取）
- [ ] 5. 專家模擬（角色類型 + 背景 + 專長）
- [ ] 6. 驗察需求（具體驗證項）
- [ ] 7. 注意事項（歷史教訓 + 特殊風險）
- [ ] 8. 家族手冊確認（技能清單 + 勾選框）

### 附錄 C：產出文件命名規範

| 文件類型 | 命名格式 | 示例 |
|----------|----------|------|
| 委任狀 | APPOINTMENT_{任務ID}_{角色}.md | APPOINTMENT_T20260511_PLANNER.md |
| Planner 報告 | PLANNER_REPORT_{YYYYMMDD_HHMMSS}.md | PLANNER_REPORT_20260511_143022.md |
| Evaluator 報告 | EVALUATOR_REPORT_{YYYYMMDD_HHMMSS}.md | EVALUATOR_REPORT_20260511_143022.md |
| Generator 報告 | GENERATOR_REPORT_{YYYYMMDD_HHMMSS}.md | GENERATOR_REPORT_20260511_143022.md |
| 任務完成標記 | MISSION_COMPLETE_{任務ID}.md | MISSION_COMPLETE_T20260511.md |

### 附錄 D：素材傳遞規則

| 規則 | 說明 |
|------|------|
| 一字不改 | 原始需求、CHECKLIST.md、各 REPORT 傳遞時禁止任何修改 |
| 相對路徑 | 所有文件引用使用相對路徑，禁止絕對路徑 |
| 統一目錄 | 所有委任狀與報告放在 user skill assets 目錄 |
| 時間戳命名 | REPORT 文件必須包含 {YYYYMMDD_HHMMSS}，避免覆蓋 |

---

*最後更新：2026-05-11*
*本檔案為 LLM 執行指令，人類可讀解釋書請參考 readme/SKILL.md*
*詳細路由規則見 reference/ROUTING_RULES.md*
*溝通協議見 reference/SUB_AGENT_PROTOCOLS.md*
*任命模板見 reference/ASSIGNMENT_TEMPLATE.md*
