---
id: agent-mission-finishing
version: v1.3.0
description: "任務收尾與交付。執行平台檢測、選項建議、最終六欄填充、檔案找回、路徑規範、下載連結驗證、成功率追蹤、SUGGESTION.md累積、交接主人。"
author: Kevin Lin
skill_bundle: agent-harness-by-kevinlinz
tags: [mission-finishing, LLM-execution, checklist]
---

## 🔴 身份分流（讀到這裡立即停止，不要往下讀）

### 若你是 Sub-Agent（L1 / L2 / L3）且非 Finishing 角色
本文件與你無關。你已從任命書獲得任務，直接執行即可。
**禁止繼續閱讀以下內容**
立即停止。關閉本文件。去執行你的任務。

### 若你是 Main Agent（L0）或 Finishing（L1 Sub-Agent）
繼續閱讀以下內容。本文件是你的執行指令。

---

## ⚠️ 認知糾偏（僅 Finishing 閱讀）

### 錯誤理解
❌ "Finishing 只需要輸出『完成了』"
❌ "所有平台都支援 sandbox 連結"
❌ "選項越多越好，讓主人自由選擇"
❌ "最終六個欄位可以隨便填"
❌ "Finishing 可以繼續執行未完成的子任務"
❌ "MEMORY.md 記錄是可選的"
❌ "路徑文字就等於檔案交付"

### 正確理解
✅ Finishing 是最複雜的階段之一，涉及平台檢測、檔案找回、最終字段計算、成功率記錄、路徑規範、連結驗證
✅ 只有 Kimi 支援 sandbox:/// 語法。OpenClaw、WorkBuddy 使用各自格式
✅ 選項最多兩個（A/B），超過導致決策疲勞
✅ 最終六個欄位是客觀評估執行質量的唯一依據，必須真實統計
✅ Finishing 的職責是收尾不是補做，未完成應上報協調者
✅ MEMORY.md 是團隊的「成績單」，沒有就無法判斷專家是否值得繼續聘用
✅ 必須提供可點擊下載連結或平台原生傳輸，禁止只提供路徑文字

---

## 🔴 口訣（條件反射，無需理解語義）

    收。尾。交。付。

含義：收尾任務 → 檢測平台 → 交付檔案 → 記錄成功率。

---

## 🚨 立即執行（8 個步驟）

### [ ] 步驟 1：身份確認
- 檢查任命書角色：必須是「Finishing / 收尾專員」
- 若角色不符 → 輸出 [IDENTITY-ERROR] 並停止
- 確認層級標記：L1（Finishing 只能是 L1，禁止 L2+）

### [ ] 步驟 2：載入家族手冊（4 項強制勾選）
- [ ] agent-bootstrap（身份判斷）
- [ ] agent-conversation-mode（對話記錄）
- [ ] agent-coordination-mode（任務路由）
- [ ] SKILL_CORRECTIONS.md（錯誤避免）
- 缺少任何一項 → 輸出 [FAMILY-MANUAL-MISSING] 並停止

### [ ] 步驟 3：平台檢測（輸出前必做）
檢測當前平台：
- [ ] 有 `ipython` 工具 → **Kimi** → 使用 `sandbox:///mnt/agents/output/` 連結格式
- [ ] 無 `ipython` 但有其他文件工具 → **OpenClaw / WorkBuddy** → 使用平台原生輸出機制
- [ ] 無法判斷 → 輸出 [PLATFORM-UNKNOWN] → 直接輸出到對話 + 詢問主人確認

**禁止**：不檢測平台就輸出連結。

### [ ] 步驟 4：檔案找回（主動掃描）
掃描所有執行過程中產生的檔案：
- [ ] CHECKLIST.md（Planner 輸出）
- [ ] PLANNER_REPORT_{時間}.md
- [ ] EVALUATOR_REPORT_{時間}.md
- [ ] GENERATOR_REPORT_{時間}.md
- [ ] CORRECTION.md（Generator 更新）
- [ ] SUGGESTION.md（各角色累積）
- [ ] 技術文件（HTML / Python / 腳本等）

**找回規則**：
- 統一在 `user skill assets/` 目錄下尋找（相對路徑）
- 檔案名稱強制小寫
- 若檔案遺失 → 標記 [MISSING] 並說明原因
- 禁止到處搜索家目錄或 Claw/assets/

### [ ] 步驟 5：最終六個欄位填充
從 checklist 和執行日誌獲取客觀數據：
- [ ] **最終成功率** = 成功步驟數 / 總步驟數 × 100%
- [ ] **最終完成效率** = 實際步數 + 時間 + 工具調用次數
- [ ] **最終完成成本** = 實際消耗 Tokens 數量（如可統計）
- [ ] **最終完成魯棒性** = 錯誤處理完善度 + 邊界值測試通過率
- [ ] **最終完成安全性** = 未授權操作次數 / 總操作次數 × 100%
- [ ] **最終完成一致性** = 多次運行結果一致次數 / 總運行次數 × 100%

**禁止**：憑感覺填寫。必須有計算依據。

### [ ] 步驟 6：選項建議（最多兩個）
若任務有爭議或需主人決策，提供 A/B 兩個選項：
- [ ] 選項 A：接近完美完成（前提 + 預期結果 + 利弊）
- [ ] 選項 B：次接近完成（前提 + 預期結果 + 利弊）
- [ ] 禁止提供 3+ 個選項

### [ ] 步驟 7：輸出交付（按平台格式）
按檢測到的平台輸出：

**Kimi 平台**：
- [ ] 使用 `ipython` 寫入 `/mnt/agents/output/`
- [ ] 提供 `[title](sandbox:///mnt/agents/output/file)` 連結
- [ ] 驗證連結有效性（檔案確實存在）

**OpenClaw / WorkBuddy 平台**：
- [ ] 使用平台原生文件傳輸工具（如 deliver_attachments）
- [ ] 若原生工具失敗 → 將檔案內容摘要輸出到對話
- [ ] 標記 `[DELIVERY-METHOD]` 說明傳輸方式

**所有平台**：
- [ ] 禁止只提供路徑文字（如 `/Users/.../file.md`）
- [ ] 必須提供可點擊或可下載的連結
- [ ] 若連結失效 → 標記 `[DELIVERY-FAILED]` 並提供備份方案

### [ ] 步驟 8：成功率追蹤（寫入 MEMORY.md）
使用腳本 `finishing_report.py` 記錄：
```python
from finishing_report import record_success_rate

record_success_rate(
    task_id="T20260511",
    planner_rate=95,
    generator_rate=85,
    evaluator_rate=90,
    overall_rate=90,
    platform="Kimi",
    notes="Generator 階段腳本缺失導致阻塞，已記錄 CORRECTION.md"
)
```

**禁止**：不記錄成功率就結束任務。

---

## ❌ 紅線（觸碰即錯）

- [ ] 禁止超過兩個選項（最多 A/B）
- [ ] 禁止不檢測平台就輸出連結
- [ ] 禁止假設所有平台支援 sandbox 語法
- [ ] 禁止硬編碼平台路徑（如 `/Users/kevinlinz/...`）
- [ ] 禁止輸出路徑文字代替下載連結
- [ ] 禁止在 Finishing 階段繼續執行子任務
- [ ] 禁止遺漏最終六個欄位
- [ ] 禁止不寫入 MEMORY.md

---

## ⚡ 異常處理（條件反射）

### 異常 1：身份確認失敗
- 觸發：任命書角色不是 Finishing
- 動作：輸出 [IDENTITY-ERROR] → 停止
- 禁止：繼續執行本 skill

### 異常 2：家族手冊載入失敗
- 觸發：4 項家族手冊任一項無法載入
- 動作：輸出 [FAMILY-MANUAL-MISSING] → 上報 coordinator
- 禁止：繼續執行

### 異常 3：平台檢測失敗
- 觸發：無法判斷當前平台
- 動作：直接輸出到對話 + 標記 [PLATFORM-UNKNOWN] → 詢問主人確認
- 禁止：中斷收尾流程

### 異常 4：檔案遺漏
- 觸發：預期檔案（如 GENERATOR_REPORT）找不到
- 動作：標記 [MISSING] → 列出遺漏清單 → 上報 coordinator
- 禁止：因單個檔案遺漏停止所有交付

### 異常 5：最終字段數據缺失
- 觸發：某個欄位無法計算（如未開啟 token 統計）
- 動作：填入「N/A」→ 說明原因 → 建議下次開啟統計
- 禁止：因單個字段缺失留空所有字段

### 異常 6：下載連結失效
- 觸發：輸出連結後主人反饋無法下載
- 動作：
  1. 嘗試平台原生備用機制
  2. 將檔案內容摘要輸出到對話
  3. 標記 [DELIVERY-FAILED] 並說明原因
- 禁止：不重試就放棄交付

---

## 🔒 版本鎖定

🔒 LOCK v1.3.0 PERMANENT — 平台檢測機制、路徑規範、下載連結驗證、最終六欄填充禁止修改

---

## 附錄 A：平台輸出格式快速對照表

| 平台 | 檔案輸出方式 | 連結格式 | 備用機制 |
|------|-------------|---------|---------|
| Kimi | ipython 寫入 /mnt/agents/output/ | `[title](sandbox:///mnt/agents/output/file)` | 內容摘要輸出到對話 |
| OpenClaw | 原生文件輸出工具 | 依平台原生 | deliver_attachments |
| WorkBuddy | 原生文件輸出工具 | 依平台原生 | 微信助手集成 |
| 未知 | 直接輸出到對話 | 無 | 詢問主人確認 |

## 附錄 B：路徑規範

| 規則 | 說明 | 示例 |
|------|------|------|
| 統一 assets 目錄 | 每個技能有自己的 assets/ 子目錄 | `agent-mission-finishing/assets/` |
| 相對路徑 | 禁止使用絕對路徑 | `assets/FINAL_REPORT.md` |
| 小寫命名 | 所有檔案名稱強制小寫 | `checklist.md` |
| 時間戳命名 | 產出文件必須含時間戳 | `FINAL_REPORT_20260511_143022.md` |
| 累積追加 | 同一類型文件持續追加 | `checklist.md` 不斷長大 |

## 附錄 C：命名規範

| 文件類型 | 命名格式 | 示例 |
|---------|---------|------|
| 最終報告 | FINAL_REPORT_{YYYYMMDD_HHMMSS}.md | FINAL_REPORT_20260511_143022.md |
| 委任狀 | APPOINTMENT_{任務ID}_FINISHING.md | APPOINTMENT_T20260511_FINISHING.md |

## 附錄 D：SUGGESTION.md 條目格式

```
| F-001 | 檔案找回 | PLANNER | R1 | 收尾建議 | 待解決 | 確保5個檔案 |
```

---

*LLM 執行指令集 v1.3.0*
*禁止修改核心流程*
