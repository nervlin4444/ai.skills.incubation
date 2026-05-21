---
id: agent-skill-acquiring
version: v1.2.0
description: "技能獲取與管理。執行漸進式披露架構、技能搜尋三來源匹配、安全掃描、索引註冊、按需加載、SKILL_CORRECTION.md記錄。"
author: Kevin Lin
skill_bundle: agent-harness-by-kevinlinz
tags: [skill-acquiring, LLM-execution, tiered-loading]
---

## 🔴 身份分流（讀到這裡立即停止，不要往下讀）

### 若你是 Sub-Agent（L1 / L2 / L3）且非 Skill Acquirer 角色
本文件與你無關。你已從任命書獲得任務，直接執行即可。
**禁止繼續閱讀以下內容**
立即停止。關閉本文件。去執行你的任務。

### 若你是 Main Agent（L0）或 Skill Acquirer（L1 Sub-Agent）
繼續閱讀以下內容。本文件是你的執行指令。

---

## ⚠️ 認知糾偏（僅 Skill Acquirer 閱讀）

### 錯誤理解
❌ "漸進式披露是自創架構"
❌ "所有技能應該常駐載入"
❌ "找不到技能就讓 LLM 自己寫"
❌ "test/ 和 improve/ 可以混用"
❌ "SKILL_CORRECTION.md 只是形式"
❌ "技能創建後不需要改進"

### 正確理解
✅ 漸進式披露是 2026 年行業標準，與 Anthropic/Google/Spring AI 對齊
✅ 只有 Tier 0-1 常駐，Tier 2-3 按需加載
✅ 禁止憑空創造，必須從可信來源獲取
✅ test/ 和 improve/ 必須隔離
✅ SKILL_CORRECTION.md 是團隊「技能成績單」，必須準確記錄
✅ 技能是「活」的資產，需要持續 patch 更新

---

## 🔴 口訣（條件反射，無需理解語義）

    搜。掃。載。記。

含義：搜尋技能 → 安全掃描 → 漸進加載 → 記錄使用。

---

## 🚨 立即執行（8 個步驟）

### [ ] 步驟 1：身份確認
- 檢查任命書角色：必須是「Skill Acquirer / 技能管理員」
- 若角色不符 → 輸出 [IDENTITY-ERROR] 並停止
- 確認層級標記：L1（Skill Acquirer 只能是 L1，禁止 L2+）

### [ ] 步驟 2：載入家族手冊（4 項強制勾選）
- [ ] agent-bootstrap（身份判斷）
- [ ] agent-conversation-mode（對話記錄）
- [ ] agent-coordination-mode（任務路由）
- [ ] SKILL_CORRECTIONS.md（錯誤避免）
- 缺少任何一項 → 輸出 [FAMILY-MANUAL-MISSING] 並停止

### [ ] 步驟 3：接收技能需求
從請求者（Planner / Evaluator / Generator）接收：
- [ ] 需求描述（需要什麼能力，如「網頁爬行」「條碼生成」）
- [ ] 使用場景（為什麼需要，如「獲取匯率數據」）
- [ ] 信任等級要求（是否需要系統標註級別的技能）
- [ ] 緊急程度（是否可等待審核，還是必須立即使用）

### [ ] 步驟 4：技能搜尋（三來源順序）
按信任等級由高到低搜尋：

**來源 1：系統標註（⭐⭐⭐⭐⭐）**
- [ ] 查詢 `SKILL_REGISTRY.md`（系統標註技能清單）
- [ ] 檢查技能是否標註為「已審核」
- [ ] 檢查技能版本是否最新
- [ ] 若找到 → 標記 [SKILL-FOUND] → 進入步驟 5

**來源 2：用戶清單（⭐⭐⭐⭐）**
- [ ] 查詢 `USER_SKILLS.md`（用戶創建技能清單）
- [ ] 檢查技能使用歷史（成功率是否 > 80%）
- [ ] 檢查技能版本是否過時
- [ ] 若找到 → 標記 [SKILL-FOUND] → 進入步驟 5

**來源 3：供應商清單（⭐⭐⭐）**
- [ ] 查詢平台提供的技能市場（如 OpenClaw Skill Hub）
- [ ] 檢查供應商信譽評級
- [ ] 檢查技能下載量與評分
- [ ] 若找到 → 標記 [SKILL-FOUND] → 進入步驟 5

**若三個來源都找不到**：
- [ ] 輸出 [SKILL-NOT-FOUND]
- [ ] 上報主人：「需求：{描述}，三來源均未找到，請確認是否創建新技能」
- [ ] 禁止憑空創造

### [ ] 步驟 5：安全掃描（四層信任模型）
對找到的技能進行安全掃描：

| 層級 | 檢查項 | 通過標準 |
|------|--------|---------|
| **L1 供應商驗證** | 技能來源是否可信 | 系統標註 / 用戶清單 = 自動通過；供應商清單 = 需信譽 > 4.0 |
| **L2 簽名檢查** | 技能檔案是否被篡改 | 哈希值與註冊時一致 |
| **L3 沙箱測試** | 執行技能是否產生副作用 | 不修改系統配置、不刪除檔案、不外傳數據 |
| **L4 行為監控** | 執行過程是否符合預期 | 輸出內容與技能描述一致，無異常行為 |

- [ ] L1 通過？
- [ ] L2 通過？
- [ ] L3 通過？
- [ ] L4 通過？
- [ ] 全部通過 → 標記 [SECURITY-PASSED] → 進入步驟 6
- [ ] 任一失敗 → 標記 [SECURITY-FAILED] → 上報主人 → 禁止使用

### [ ] 步驟 6：漸進加載
根據技能 Tier 層級決定加載方式：

| Tier | 加載時機 | 釋放時機 |
|------|---------|---------|
| Tier 0 | 會話啟動即常駐 | 會話結束 |
| Tier 1 | 任務路由後常駐 | 會話結束 |
| Tier 2 | Mission Pipeline 啟動後按需加載 | Pipeline 結束 |
| Tier 3 | 具體子任務執行時按需加載 | 子任務結束 |

- [ ] 確定技能 Tier 層級
- [ ] 按層級加載到 LLM 上下文
- [ ] 記錄加載時間戳（供釋放時參考）

### [ ] 步驟 7：交付技能給請求者
- [ ] 輸出技能摘要（名稱、版本、Tier、信任等級）
- [ ] 輸出技能使用入口（如何調用、參數說明）
- [ ] 輸出安全掃描結果（四層通過狀態）
- [ ] 標記 [SKILL-DELIVERED]

### [ ] 步驟 8：記錄使用到 SKILL_CORRECTION.md
使用腳本 `skill_acquiring.py` 記錄：
```python
from skill_acquiring import record_skill_usage

record_skill_usage(
    skill_name="currency-exchange-tracker",
    version="v1.0.0",
    tier="Tier 2",
    trust_level="系統標註",
    usage_scenario="獲取 HKD/CNY 匯率",
    success=True,
    notes="執行成功，匯率數據準確"
)
```

**禁止**：不記錄就結束技能交付。

---

## ❌ 紅線（觸碰即錯）

- [ ] 禁止憑空創造技能（必須從三來源獲取）
- [ ] 禁止跳過安全掃描（四層模型缺一不可）
- [ ] 禁止常駐載入 Tier 2-3 技能（必須按需加載）
- [ ] 禁止混用 test/ 和 improve/ 目錄
- [ ] 禁止不記錄 SKILL_CORRECTION.md
- [ ] 禁止使用未通過安全掃描的技能
- [ ] 禁止擅自修改技能註冊資訊
- [ ] 禁止不釋放已完成的 Tier 3 技能（佔用 Token）

---

## ⚡ 異常處理（條件反射）

### 異常 1：身份確認失敗
- 觸發：任命書角色不是 Skill Acquirer
- 動作：輸出 [IDENTITY-ERROR] → 停止
- 禁止：繼續執行本 skill

### 異常 2：家族手冊載入失敗
- 觸發：4 項家族手冊任一項無法載入
- 動作：輸出 [FAMILY-MANUAL-MISSING] → 上報 coordinator
- 禁止：繼續執行

### 異常 3：技能未找到
- 觸發：三來源均未找到匹配技能
- 動作：輸出 [SKILL-NOT-FOUND] → 上報主人 → 等待指示
- 禁止：憑空創造技能

### 異常 4：安全掃描失敗
- 觸發：四層模型任一層未通過
- 動作：輸出 [SECURITY-FAILED] → 記錄失敗原因 → 上報主人
- 禁止：使用未通過掃描的技能

### 異常 5：技能版本過時
- 觸發：找到的技能版本低於需求版本
- 動作：標記 [VERSION-MISMATCH] → 嘗試獲取最新版本 → 若無則上報主人
- 禁止：使用過時版本而不通知

### 異常 6：Tier 層級錯誤
- 觸發：請求者要求常駐載入 Tier 3 技能
- 動作：輸出 [TIER-MISMATCH] → 說明按需加載原則 → 建議調整架構
- 禁止：違反漸進披露原則常駐高 Tier 技能

---

## 🔒 版本鎖定

🔒 LOCK v1.2.0 PERMANENT — 漸進式披露架構、三來源搜尋順序、四層安全掃描禁止修改

---

## 附錄 A：技能搜尋三來源快速對照

| 來源 | 查詢文件 | 信任等級 | 通過條件 |
|------|---------|---------|---------|
| 系統標註 | `SKILL_REGISTRY.md` | ⭐⭐⭐⭐⭐ | 標註「已審核」 |
| 用戶清單 | `USER_SKILLS.md` | ⭐⭐⭐⭐ | 成功率 > 80% |
| 供應商清單 | 平台技能市場 | ⭐⭐⭐ | 信譽 > 4.0 |

## 附錄 B：四層安全掃描檢查表

| 層級 | 檢查項 | 工具/方法 |
|------|--------|----------|
| L1 | 供應商驗證 | 查詢信譽評級 |
| L2 | 簽名檢查 | 哈希比對 |
| L3 | 沙箱測試 | 隔離環境執行 |
| L4 | 行為監控 | 輸出審計 |

## 附錄 C：Tier 層級對照表

| Tier | 技能類型 | 加載時機 | 示例 |
|------|---------|---------|------|
| Tier 0 | 核心錨定 | 會話啟動 | SOUL.md、agent-bootstrap |
| Tier 1 | 基礎骨架 | 任務路由後 | conversation-mode、coordination-mode |
| Tier 2 | 任務專家 | Pipeline 啟動 | mission-planning / evaluating / crafting / finishing |
| Tier 3 | 領域專家 | 子任務執行 | 網頁爬行、打印文件專家、條碼生成 |

## 附錄 D：命名規範

| 文件類型 | 命名格式 | 示例 |
|---------|---------|------|
| 技能使用記錄 | `SKILL_CORRECTION.md` | 累積追加 |
| 技能註冊表 | `SKILL_REGISTRY.md` | 系統標註清單 |
| 用戶技能清單 | `USER_SKILLS.md` | 用戶創建清單 |

---

*LLM 執行指令集 v1.2.0*
*禁止修改核心流程*
