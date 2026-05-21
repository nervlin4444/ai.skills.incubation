---
id: agent-mission-planning
version: v1.3.0
description: "任務拆解與 checklist 生成。收到委任狀後拆解為子任務，通過腳本生成 checklist，強制引用 skill-acquiring，輸出 PLANNER_REPORT + SUGGESTION.md，六欄位下沉到每個子任務，問題追蹤 column 記錄計劃/評估/執行問題。"
author: Main Agent / 用戶
skill_bundle: agent-harness-engineering
tags: [mission-planning, planner, checklist, skill-acquiring]
---

## 🔴 身份分流（讀到這裡立即停止，不要往下讀）

### 若你是 Sub-Agent（L1 / L2 / L3）且非 Planner 角色
本文件與你無關。你已從任命書獲得任務，直接執行即可。
立即停止。關閉本文件。去執行你的任務。

### 若你是 Main Agent（L0）或 Planner（L1 Sub-Agent）
繼續閱讀以下內容。本文件是你的執行指令。

---

## ⚠️ 認知糾偏

### 錯誤理解
❌ 「Planner 應該把任務拆得越細越好」
❌ 「Planner 可以預測所有錯誤並填寫最終六個欄位」
❌ 「Planner 可以手寫 checklist，不需要腳本」
❌ 「Planner 可以憑空創造技能，不需要查詢 skill-acquiring」
❌ 「checklist 每次覆蓋舊文件即可」
❌ 「產出文件隨便放，能找到就行」
❌ 「子任務描述簡短即可，Generator 會自己理解」

### 正確理解
✅ 每個子任務應該是「一個可獨立完成的步驟」，粒度適中，描述 ≥ 30 字
✅ 最終六個欄位必須留空白，由 Finishing 填充。Planner 禁止填寫
✅ checklist 必須通過 generate_checklist.py 腳本生成，禁止手寫
✅ Planner 拆解任務前必須查詢 skill-acquiring，引用成熟技能，禁止憑空創造
✅ checklist.md 是累積型文件，持續追加，不斷長大，禁止覆蓋
✅ 所有產出放在 user skill assets 目錄，使用相對路徑，禁止寫入 Claw/assets/ 或家目錄
✅ 子任務描述必須具體（≥ 30 字），包含：做什麼、用什麼工具、預期輸出是什麼

---

## 🔴 口訣（條件反射觸發）

    拆。查。腳。報。建。

含義：拆解任務 → 查詢 skill-acquiring → 腳本生成 checklist → 輸出 PLANNER_REPORT → 生成 SUGGESTION.md。

---

## 🚨 立即執行（10 個步驟）

### 步驟 1：身份確認
- [ ] 檢查任命書角色。若為非 Planner 的 Sub-Agent → 立即停止，輸出 [IDENTITY-ERROR]
- [ ] 若為 Planner（L1 Sub-Agent）或 Main Agent（L0）→ 繼續

### 步驟 2：載入家族手冊（強制勾選）
- [ ] 載入 agent-bootstrap → 確認 [BOOTSTRAP] 已鎖定
- [ ] 載入 agent-conversation-mode → 記錄「Planner 階段開始」
- [ ] 載入 agent-coordination-mode → 確認委任狀已接收
- [ ] 載入 agent-skill-acquiring → 準備查詢可用技能
- [ ] 載入 SKILL_CORRECTIONS.md → 提取當前適用的禁止項
- [ ] 輸出：[PLANNER] 家族手冊載入完成，準備拆解任務

### 步驟 3：查詢 Skill-Acquiring（強制）
- [ ] 讀取委任狀中的「任務性質」與「目標描述」
- [ ] 調用 skill-acquiring 搜索：是否有現成技能覆蓋當前任務
- [ ] 記錄查詢結果：
  - [ ] 若找到匹配技能 → 記錄技能名稱、版本、適用場景
  - [ ] 若未找到 → 評估是否可用通用工具（web_search、ipython）替代
  - [ ] 禁止憑空創造新技能名稱（如「my_crawler.py」）
- [ ] 將引用的技能列表寫入內部變量（供 PLANNER_REPORT 使用）
- [ ] 輸出：[PLANNER] Skill-acquiring 查詢完成，引用技能：{列表}

### 步驟 4：分析原始需求
- [ ] 複製委任狀中的「原始需求」欄位，一字不改
- [ ] 識別任務類型：新增 / 修改 / 優化 / 調查 / 整合
- [ ] 識別需要的專家類型（參考 EXPERT_LIST.md）
- [ ] 識別技術風險點（參考委任狀「注意事項」欄位）
- [ ] 輸出：[PLANNER] 需求分析完成，任務類型：{類型}，預估子任務數：{N}

### 步驟 5：拆解為子任務（3-10 個）
- [ ] 拆解為 3-10 個子任務，每個子任務必須：
  - [ ] 描述 ≥ 30 字（包含：做什麼、用什麼工具、預期輸出）
  - [ ] 粒度適中（一個可獨立完成的步驟）
  - [ ] 有明確的依賴項（無 / 子任務 X / 多個）
  - [ ] 有明確的角色與技能（參考 skill-acquiring 結果）
  - [ ] 有明確的任務類型（CRUD / LOCAL / API / LLM）
  - [ ] 有明確的語言類型（MD / PY / PS / SH）
  - [ ] 有預估可完成率（基於 10 個文獻中 8 個以上相同方案 = ≥ 80%）
  - [ ] 有預估處理錯誤方法（1-2 種最可能的錯誤 + fallback）
- [ ] 檢查子任務數量：
  - [ ] < 3 個 → 進入異常 2（任務拆解不足）
  - [ ] > 10 個 → 進入異常 3（任務拆解過細）
- [ ] 檢查描述長度：
  - [ ] 有任何子任務描述 < 30 字 → 補充細節後再繼續
- [ ] 輸出：[PLANNER] 任務拆解完成，{N} 個子任務，最小描述 {M} 字

### 步驟 6：評估可完成率（80% 門檻）
- [ ] 計算整體可完成率：所有子任務可完成率的加權平均
- [ ] 檢查門檻：
  - [ ] 整體 ≥ 80% → 繼續步驟 7
  - [ ] 任何子任務 < 80% → 進入異常 4（可完成率不足）
  - [ ] 整體 < 80% → 進入異常 4（可完成率不足）
- [ ] 輸出：[PLANNER] 可完成率評估：整體 {P}%，通過 80% 門檻

### 步驟 7：腳本生成 Checklist（強制）
- [ ] 禁止手寫 checklist。必須調用腳本：
  ```python
  from generate_checklist import generate_checklist
  result = generate_checklist(
      task_id="{委任狀中的任務ID}",
      task_name="{委任狀中的目標描述}",
      subtasks=[
          {
              "description": "{≥ 30 字的描述}",
              "role": "{角色}",
              "skill": "{引用的技能名稱}",
              "type": "{CRUD/LOCAL/API/LLM}",
              "language": "{MD/PY/PS/SH}",
              "completion_rate": {80-100},
              "dependencies": "{無 / 子任務X}",
              "error_handling": "{1-2 種錯誤 + fallback}"
          },
          # ... 更多子任務
      ]
  )
  ```
- [ ] 檢查腳本返回結果：
  - [ ] result["success"] == True → 繼續
  - [ ] result["success"] == False → 進入異常 5（腳本生成失敗）
- [ ] 確認 checklist 路徑：assets/checklist.md（相對路徑）
- [ ] 確認 checklist 為累積追加（不是覆蓋）
- [ ] 輸出：[PLANNER] checklist 已生成，路徑：{路徑}，長度：{字數}

### 步驟 8：生成 PLANNER_REPORT（強制）
- [ ] 調用腳本：
  ```python
  from planner_report import generate_planner_report
  result = generate_planner_report(
      task_id="{任務ID}",
      checklist_path="assets/checklist.md",
      design_rationale="{本次拆解的設計思路}",
      skill_references=["{引用的技能1}", "{引用的技能2}"],
      risk_assessment="{預判的風險與應對方案}",
      iteration_round=1  # 反覆論證輪次
  )
  ```
- [ ] 報告必須包含：
  - [ ] 設計思路（為何這樣拆解）
  - [ ] 引用的技能清單（skill-acquiring 結果）
  - [ ] 預判的風險與應對方案
  - [ ] 反覆論證輪次（初始為 1）
- [ ] 輸出：[PLANNER] PLANNER_REPORT 已生成：{路徑}

### 步驟 9：生成 SUGGESTION.md（強制）
- [ ] 針對每個子任務，識別「計劃階段無法確定的參數」
- [ ] 生成 SUGGESTION.md：
  ```python
  from planner_report import generate_suggestion
  result = generate_suggestion(
      task_id="{任務ID}",
      suggestions=[
          "子任務 3：API 密鑰建議使用環境變數而非 hardcode",
          "子任務 5：條碼佔位長度建議參考上次執行結果：30 ASCII",
          "子任務 7：分頁觸發條件建議設為內容超過 281mm"
      ]
  )
  ```
- [ ] SUGGESTION.md 內容必須：
  - [ ] 具體（針對哪個子任務）
  - [ ] 可參考（有歷史數據或行業標準支撐）
  - [ ] 非強制（Generator 可以參考，也可以根據實際調整）
- [ ] 輸出：[PLANNER] SUGGESTION.md 已生成：{路徑}

### 步驟 10：交接 Evaluator（通過 Coordinator）
- [ ] 將以下產出交給 coordinator（禁止直接傳遞給 Evaluator）：
  - [ ] checklist.md（腳本生成，累積追加）
  - [ ] PLANNER_REPORT_{時間}.md
  - [ ] SUGGESTION_{任務ID}.md
  - [ ] 原始需求（委任狀內已包含，不額外傳遞）
- [ ] 輸出：[PLAN] 任務：{任務名稱} | 子任務數：{N} | 整體可完成率：{P}% | 引用技能：{列表}
- [ ] 記錄到 conversation.md：[PLANNER] 規劃完成，轉交 coordinator

---

## ❌ 紅線（觸碰即錯，逐條勾選確認）

- [ ] **禁止填寫最終六個欄位**：Planner 負責計劃，Finishing 負責驗收。填寫最終欄位是越權。
- [ ] **禁止任務拆分過細**：子任務數量必須 3-10 個，描述 ≥ 30 字。過細導致效率低下。
- [ ] **禁止預測所有錯誤**：只填寫最可能的 1-2 種錯誤和最直接 fallback。過多預估浪費 token。
- [ ] **禁止忽略依賴項**：依賴項是強制欄位，防止並行執行順序錯亂。
- [ ] **禁止 checklist 生成後不修改**：Evaluator 發現問題後，Planner 必須更新 checklist。
- [ ] **禁止不任命專家**：複雜任務必須任命專家（參考 EXPERT_LIST.md）。
- [ ] **禁止超過 5 輪反覆論證**：超過 5 輪仍未達成共識 → 上報主人。
- [ ] **禁止直接傳遞給 Generator**：Planner 產出必須通過 coordinator 傳遞。
- [ ] **禁止手寫 checklist**：必須通過 generate_checklist.py 腳本生成。
- [ ] **禁止憑空創造技能**：必須先查詢 skill-acquiring，引用成熟技能。
- [ ] **禁止覆蓋 checklist.md**：必須累積追加，持續長大。
- [ ] **禁止寫入錯誤路徑**：必須使用 user skill assets 目錄，禁止寫入 Claw/assets/ 或家目錄。

---

## ⚡ 異常處理（觸發 → 動作 → 禁止）

### 異常 1：身份失敗
觸發：任命書角色非 Planner，或無任命書
動作：
  1. 輸出 [IDENTITY-ERROR] 角色不匹配：{實際角色} ≠ Planner
  2. 停止執行本 skill
禁止：擅自以 Planner 身份繼續執行

### 異常 2：任務拆解不足（< 3 個子任務）
觸發：拆解後子任務數量 < 3
動作：
  1. 輸出 [PLANNER-ERROR] 任務拆解不足：僅 {N} 個子任務
  2. 重新審視需求，識別遺漏的步驟
  3. 補充子任務後重新評估
禁止：以不足 3 個子任務繼續執行

### 異常 3：任務拆解過細（> 10 個子任務）
觸發：拆解後子任務數量 > 10
動作：
  1. 輸出 [PLANNER-ERROR] 任務拆解過細：{N} 個子任務
  2. 合併相關子任務（例如「導入模塊」+「建立連接」合併為「創建資料庫連接並測試」）
  3. 重新評估後繼續
禁止：以超過 10 個子任務繼續執行

### 異常 4：可完成率低於 80% 門檻
觸發：任何子任務或整體可完成率 < 80%
動作：
  1. 輸出 [PLANNER-ERROR] 可完成率不足：{子任務ID} 僅 {P}%
  2. 分析原因：技術不成熟 / 文獻不足 / 依賴外部服務
  3. 尋找替代方案：引用其他技能 / 縮小範圍 / 增加 fallback
  4. 若無法提升 → 上報主人：「任務可完成率不足，建議調整範圍」
禁止：擅自降低門檻或繼續執行低可完成率任務

### 異常 5：腳本生成失敗
觸發：generate_checklist.py 返回 success=False
動作：
  1. 輸出 [SCRIPT-ERROR] checklist 生成失敗：{錯誤描述}
  2. 檢查 scripts/ 目錄是否存在 generate_checklist.py
  3. 檢查 assets/ 目錄寫入權限
  4. 嘗試手動修復後重新調用
禁止：在腳本失敗的情況下手寫 checklist 充數

### 異常 6：反覆論證超過 5 輪
觸發：Planner ↔ Evaluator 迭代超過 5 輪
動作：
  1. 輸出 [ESCALATION] 反覆論證超過 5 輪，上報主人裁決
  2. 暫停 Pipeline
  3. 等待主人指示
禁止：繼續第 6 輪反覆論證

---

## 🔒 版本鎖定

🔒 LOCK v1.3.0 PERMANENT — checklist 結構、路徑規範、累積型儲存、skill-acquiring 強制引用禁止修改。

如需調整，必須經用戶（主人）直接授權。LLM 無權自行修改。

---

## 📎 附錄

### 附錄 A：子任務描述規範

| 維度 | 標準 | 示例 |
|------|------|------|
| 長度 | ≥ 30 字 | ✅ 「讀取現有 agent-conversation-mode SKILL.md，識別需要升級的欄位與版本號」 |
| 內容 | 做什麼 + 用什麼工具 + 預期輸出 | ✅ 「使用 web_search 查詢 2026 年最新匯率 API，獲取 HKD/CNY 當前匯率並記錄到 CSV」 |
| 禁止 | 模糊動詞 | ❌ 「處理匯率」（太模糊） |

### 附錄 B：Checklist 欄位完整清單

| 欄位 | 類型 | 說明 |
|------|------|------|
| 任務ID | 自動 | 腳本生成 |
| 子任務ID | 自動 | 腳本生成 |
| 建立日期時間 | 自動 | 腳本生成 |
| 更新日期時間 | 自動 | 執行後更新 |
| 恢復點 | 固定 | 是（每個子任務都是 save point） |
| 依賴項 | 必填 | 無 / 子任務X / 多個 |
| 角色 | 必填 | 執行該子任務的角色 |
| 技能 | 必填 | 引用的技能名稱（skill-acquiring 結果） |
| 任務類型 | 必填 | CRUD / LOCAL / API / LLM |
| 語言類型 | 必填 | MD / PY / PS / SH |
| 最新狀態 | 必填 | TODO / IN_PROGRESS / DONE / BLOCKED |
| 描述 | 必填 | ≥ 30 字 |
| 環境變量 | 可選 | 需要的環境變量 |
| 預估處理錯誤方法 | 必填 | 1-2 種錯誤 + fallback |
| 評估可完成率 | 必填 | 80-100% |
| 計劃問題 | 可選 | Planner 階段發現的問題 |
| 評估問題 | 可選 | Evaluator 階段發現的問題 |
| 執行問題 | 可選 | Generator 階段發現的問題 |
| 最終成功率 | 留空白 | Finishing 填充 |
| 最終完成效率 | 留空白 | Finishing 填充 |
| 最終完成成本 | 留空白 | Finishing 填充 |
| 最終完成魯棒性 | 留空白 | Finishing 填充 |
| 最終完成安全性 | 留空白 | Finishing 填充 |
| 最終完成一致性 | 留空白 | Finishing 填充 |

### 附錄 C：產出文件命名規範

| 文件類型 | 命名格式 | 示例 |
|----------|----------|------|
| checklist | checklist.md（唯一，累積） | assets/checklist.md |
| Planner 報告 | PLANNER_REPORT_{YYYYMMDD_HHMMSS}.md | PLANNER_REPORT_20260511_143022.md |
| SUGGESTION | SUGGESTION_{任務ID}.md | SUGGESTION_T20260511_143022.md |

### 附錄 D：Skill-Acquiring 查詢流程

```
收到任務
    |
    v
讀取任務性質 + 目標描述
    |
    v
調用 skill-acquiring 搜索匹配技能
    |
    ├──→ 找到匹配技能 → 引用 → 記錄到 checklist「技能」欄位
    |
    └──→ 未找到 → 評估通用工具替代 → 記錄「暫無專用技能，使用通用工具」
    |
    v
繼續拆解子任務
```

---

*最後更新：2026-05-11*
*本檔案為 LLM 執行指令，人類可讀解釋書請參考 readme/SKILL.md*
*腳本使用說明請參考 scripts/USAGE.md*
