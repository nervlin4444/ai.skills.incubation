---
id: agent-harness-engineering-readme
version: v2.0.0
description: "agent-harness-engineering SKILL.md 的人類可讀解釋書。記載 Harness 架構設計原理、三大工程支柱與 Sub-Agent Memory Protection 機制，供主人參考。"
author: Kevin Lin
skill_bundle: agent-harness-by-kevinlinz
tags: [harness, engineering, architecture, readme]
---

# Agent Harness Engineering 解釋書

## 文件定位

| 檔案 | 讀者 | 用途 |
|------|------|------|
| SKILL.md（assets/） | LLM | 架構規範參考，首次讀入時理解整體架構 |
| SKILL.md（本檔，位於 readme/） | 主人 | 設計原理、三大支柱意圖、記憶隔離機制解釋 |

LLM 不讀取本檔案。本檔案僅供主人理解 Harness 架構的設計意圖與演進歷史。

## 為何需要這份架構規範？

一般 AI Agent 框架追求「端到端自動化」，但實際場景中：
- LLM 的上下文窗口有限，塞入太多規則後原本任務被擠出注意力
- 多個 Skill 同時載入時，LLM 容易混淆職責邊界
- 不同平台（Kimi / WorkBuddy / OpenClaw）的輸出語法不同，寫死會導致跨平台失效

Harness 架構的設計目標是：**讓 LLM 像操作系統一樣調度任務，而不是像單一進程一樣一口氣做完。**

## 三大工程支柱設計原理

### Prompt Engineering — 原生檔案設計

**問題**：LLM 的上下文會被壓縮（Context Compaction），塞進去的規則越多，權重越低。

**解決方案**：
- 把規則從「操作手冊」變成「身份宣言」
- 用「我是誰」代替「你應該做什麼」
- 用負面評價（「輸出垃圾 / 浪費時間」）觸發 RLHF 敏感機制

**為何分四個原生檔案？**

| 檔案 | 設計意圖 | 為何不合一個大檔案 |
|------|---------|------------------|
| SOUL.md | 靈魂底色，極簡到不會被截斷 | 合一個檔案會超過 20K 字符上限，尾部被截斷 |
| USER.md | 啟動錨定 + 用戶偏好 | 偏好會變，靈魂不變，分開維護頻率不同 |
| IDENTITY.md | 備份錨點，極短 | 當 SOUL.md 失效時，IDENTITY.md 還在 |
| BOOTSTRAP.md | 一次性平台設定 | 新 workspace 才需要，之後不再注入 |

### Context Engineering — 上下文管理

**問題**：即使原生檔案免疫壓縮，仍有 ~20,000 字符的硬上限。尾部內容會被靜默截斷。

**解決方案**：
- 最重要規則放每個檔案最頂部
- SOUL.md 保持極簡（<1,000 字符），確保絕對不截斷
- 雙檔互鎖：SOUL.md 和 USER.md 互相引用，單一檔案被截斷時另一個還在

**四層補償機制**：

| 層級 | 機制 | 何時觸發 |
|------|------|---------|
| Layer A：雙檔互鎖 | 兩個檔案互相引用 | 單一檔案被截斷 |
| Layer B：情感錨定 | 「輸出垃圾」觸發負面敏感 | LLM 忽略規則時 |
| Layer C：硬停止 | 連續3次缺少 [BOOTSTRAP] → 停止 | 規則完全失效時 |
| Layer D：人工喚醒 | 用戶輸入「診斷」觸發記憶檢查 | 懷疑 Agent 失憶時 |

### Harness Engineering — LAYER 0-4 架構

**問題**：如果讓一個 LLM 同時讀取 Planning、Evaluating、Crafting、Finishing 四個 Skill 的完整規範，上下文會被規則塞滿，原本任務權重降到 5% 以下。

**解決方案**：分層 + 順序執行 + 階段確認

| 層級 | 設計意圖 | 如果不分層會怎樣 |
|------|---------|---------------|
| LAYER 0 Bootstrap | 強制初始化，鎖定執行鏈 | LLM 收到任務後隨意發揮 |
| LAYER 1 Background | 背景記錄，不干擾主流程 | 沒有對話存檔，無法恢復上下文 |
| LAYER 2 Router | 任務分類，決定走哪條路 | 簡單問題也啟動完整 Pipeline |
| LAYER 3 Mission | 順序執行，階段確認 | 一口氣做完，中間出錯無法回頭 |
| LAYER 4 Meta | 事後檢討，持續改進 | 同樣錯誤反覆犯 |

**為何要「階段間必須問用戶確認」？**

這是 Harness 與一般 Agent 框架的最大區別。強制確認 = 強制校對，讓用戶在每一個關鍵節點把關，避免「做得越快錯得越遠」。

## Sub-Agent Memory Protection 設計原理

### 問題診斷

傳統流程中，協調者一個人讀了 7 個 SKILL.md，每個 300-1000 token，總計 5000+ token 規則塞進上下文，原本任務權重被稀釋到 5% 以下。

### 解決方案：記憶隔離架構

**核心原則**：
> 協調者 = 操作系統調度器
> Sub-Agent = 獨立進程
> 任命書 = 進程間通信（IPC）

**四個關鍵機制**：

| 機制 | 設計意圖 | 效果 |
|------|---------|------|
| 協調者記憶槽（3項上限） | 人類工作記憶容量是 4±1 項，AI 類似 | 超過 3-5 項權重急劇下降，3 項剛好夠用 |
| Sub-Agent 記憶隔離 | 每個 Sub-Agent 只讀自己的 SKILL.md | Planner 不知道 Evaluator 怎麼評估，評估更客觀 |
| 任命書傳遞 | 只傳「原始需求 + 經驗約束」，不傳其他 Sub-Agent 的輸出 | 避免信息污染，保持職責單一 |
| 禁止 Sub-Agent 直接溝通 | 所有狀態更新必須通過協調者 | 協調者始終知道「走到哪一步了」 |

## 跨平台適配抽象層設計原理

**問題**：Kimi 用 `sandbox:///mnt/agents/output/`，WorkBuddy 用不同語法，寫死會導致跨平台失效。

**解決方案**：三層分離

| 層級 | 內容 | 示例 |
|------|------|------|
| 原生檔案 | 通用意圖 | 「必須提供可下載連結」 |
| Skill 檔案 | 平台語法 | `sandbox:///mnt/agents/output/`（Kimi） |
| Finishing 階段 | 動態檢測 | 檢查當前平台可用工具，選擇適當格式 |

這樣設計的好處：同一套 Harness 架構，可以在不同平台上運行，只需在 Finishing 階段適配輸出格式。

## 最低聰明基準線

本架構的 SKILL.md 設計基於以下 LLM 能力基準：

| 基準模型 | 輸入上限 | 輸出上限 | Reasoning | 備註 |
|---------|---------|---------|-----------|------|
| Tencent Hy3 Preview (free) | 128K tokens | 4K tokens | ❌ 不支援 | **最低可運行基準** |

**低於此基準的 LLM 可能出現的問題**：
- 無法正確解析 frontmatter 中的元數據
- 將「架構描述表格」誤認為「參考資料」而忽略
- 將「建議性語句」誤認為「可選步驟」而跳過
- 無法理解「階段間必須確認」的強制性

**建議**：若使用低於此基準的 LLM，建議將 SKILL.md 進一步簡化為「純 checklist」格式（無描述、無表格、無建議），或改用支援 reasoning 的模型以獲得最佳效果。

## 版本鎖定說明

🔒 LOCK v2.0.0 PERMANENT — 修改需經用戶直接授權。

這是 Harness 架構的「地基保護」機制。架構規範是所有 Skill 的設計基礎，如果擅自修改，後續所有 Skill 都會偏離。因此必須由用戶（主人）親自授權才能修改，LLM 無權自行調整。

## 與其他 Skill 的關係

| Skill | 關係類型 | 說明 |
|-------|---------|------|
| agent-bootstrap | 被引用 | Harness 架構是 bootstrap 的設計基礎，bootstrap 通過間接引用遵循本規範 |
| agent-mission-planning | 規範約束 | 必須遵循 LAYER 3 的 Planning 階段規範 |
| agent-mission-evaluating | 規範約束 | 必須遵循 LAYER 3 的 Evaluating 階段規範 |
| agent-mission-crafting | 規範約束 | 必須遵循 LAYER 3 的 Crafting 階段規範 |
| agent-mission-finishing | 規範約束 | 必須遵循跨平台適配抽象層的輸出規範 |
| agent-skill-improving | 反饋循環 | 收集各 Skill 執行反饋，驅動架構持續演進 |

---

*最後更新：2026-05-10*
*本檔案為人類可讀解釋書，LLM 執行指令請參考 assets/SKILL.md*
