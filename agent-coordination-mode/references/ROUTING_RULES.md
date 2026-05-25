---
title: Coordinator Routing Rules
name: agent-coordination-mode
description: Detailed routing rules for agent-coordination-mode. Documents 'you' keyword judgment logic, Mission Pipeline launch flow, manual override mechanism, layer limits, and coordinator memory protection.
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
  local_path: "{baseDir}/ROUTING_RULES.md"
  github_path: "agent-coordination-mode/references/ROUTING_RULES.md"
---

# ROUTING_RULES.md — 協調者路由規範

## 文件定位

| 檔案 | 讀者 | 用途 |
|------|------|------|
| agent-coordination-mode/assets/SKILL.md | LLM 執行 | 執行指令集（精簡版） |
| 本檔（reference/ROUTING_RULES.md） | 主人/開發者 | 詳細路由規則展開、設計意圖說明 |

本檔為 reference/ 下的詳細展開文件，供人類理解路由規則的設計意圖。LLM 執行時以 assets/SKILL.md 為準。

## 路由判斷（唯一依據）

### 適用範圍（重要）

**「你」字判斷僅限「用戶 → Main Agent」層級。**

| 層級 | 誰做判斷 | 判斷依據 | 結果 |
|------|---------|---------|------|
| **用戶 → Main Agent** | `agent-coordination-mode` | 「你」字 | 簡單 / 複雜 |
| **Main Agent → Sub-Agent** | **不需要判斷** | 任務已分配 | **直接執行** |
| **Sub-Agent → Sub-Sub-Agent** | **不需要判斷** | 任務已分配 | **直接執行** |

**Sub-Agent 禁止執行「你」字判斷。** 身份判斷由 SOUL.md / agent-bootstrap 統一處理。

### 判斷邏輯

```python
# 僅 Main Agent（L0）執行
if "你" in user_input:
    mode = "DIRECT"      # 簡單任務，直接回覆
else:
    mode = "COORDINATION"  # 複雜任務，啟動 Mission Pipeline
```

**無需語義理解**：不需要判斷任務大小、複雜度、是否需要多專家。
**無需進一步確認**：規則只有一條，不存在模糊地帶。

### 手動覆蓋機制

「你」字判斷是**默認機制**，但允許主人**手動覆蓋**：

| 主人指令 | 效果 | 覆蓋「你」字判斷？ |
|---------|------|------------------|
| 「啟動 Pipeline」 | 強制進入 Mission Pipeline | 是 |
| 「直接回覆」 | 強制直接回覆 | 是 |
| 無明確指令 | 用「你」字判斷作為默認 | 否 |

## 含「你」時的處理流程

1. 直接執行任務或回覆問題
2. 對話記錄到 CONVERSATION.md（由 agent-conversation-mode 處理）
3. 結束

**為何簡單任務不走 Pipeline？**
- 簡單任務（如「查天氣」「翻譯這段話」）不需要 Planner + Evaluator + Generator 協作
- 強制走 Pipeline 會浪費 token，且延遲回覆速度
- 「你」字是快速篩選器，80% 的日常對話都是簡單任務

## 不含「你」時的 Mission Pipeline 啟動流程

```
Step 1: 任命 Planner（戰略大師）
  → 傳遞：原始需求 + P0 禁止清單 + 角色定義 + 層級標記 L1 + 家族手冊確認
  → 接收：CHECKLIST.md

Step 2: 任命 Evaluator（專業調查員）
  → 傳遞：CHECKLIST.md + 原始需求 + 角色定義 + 層級標記 L1 + 家族手冊確認
  → 接收：評估報告 + MEMORY.md 寫入確認

Step 3: 任命 Generator（系統工程師）
  → 傳遞：CHECKLIST.md + 原始需求 + 經驗約束 + 角色定義 + 層級標記 L1 + 家族手冊確認
  → 接收：執行結果 + CORRECTION.md

Step 4: 任命 Finishing（收尾專員）
  → 傳遞：所有輸出 + 原始需求 + 層級標記 L1
  → 接收：最終交付 + CONVERSATION.md
```

**關鍵規則**：
- Sub-Agent 之間不直接溝通，所有狀態通過協調者中轉
- 每個 Sub-Agent 只加載自己的 SKILL.md，不讀其他步驟的規範
- 協調者只傳遞，不執行、不評估、不修改

## 層級限制與路由

### 硬性限制兩層

| 層級 | 名稱 | 可召喚層級 | 禁止行為 |
|------|------|-----------|---------|
| **L0** | Main Agent | L1 | 執行實質任務 |
| **L1** | Sub-Agent | L2 | 執行「你」字判斷 |
| **L2** | Sub-Sub-Agent | 無（需申請 L3） | 未經批准召喚 L3 |
| **L3** | 已批准 | 無 | 任何召喚 |

### 第三層申請機制

若任務極度複雜，L2 Sub-Sub-Agent 可向 Main Agent 申請第三層：

```
L2 Sub-Sub-Agent：「需要申請第三層委派：{角色名稱}」
    |
    v
Main Agent 評估：
  - 檢查當前 Token 消耗
  - 檢查 checklist.md 複雜度
  - 判斷是否確實需要 L3
    |
    v
批准 / 拒絕：
  - 批准：在 checklist.md 記錄「已批准 L3：{角色名稱}」
  - 拒絕：要求 L2 在現有層級內完成
```

**禁止第四層**：無論任何理由，不得超過三層。

## 協調者記憶保護細則

### 記憶槽（3 項上限）

協調者只保留 3 項記憶，遵循 Miller's Law（人類短期記憶上限 7±2，但協調者只需記住「誰在等誰」）：

```
[Slot 1] 當前任務摘要：「查香港天氣」
[Slot 2] 當前步驟：「Planning → Evaluating → Crafting → Finishing」
[Slot 3] 下一步任命：「Planner」
```

### 禁止載入的內容

- ❌ 不讀具體執行規範（如 Python 語法、API 調用方式）
- ❌ 不讀詳細用法示例
- ❌ 不讀歷史坑的詳細案例
- ❌ 不生成代碼、不評估質量、不修改需求
- ❌ 不執行「你」字判斷（這是 Main Agent 的專利）

### 允許載入的內容

- ✅ 各技能 SKILL.md 頂部 5 行（版本 + 一句話職責）
- ✅ P0 禁止清單（3 項以內）
- ✅ 任命書模板（固定格式）
- ✅ 層級標記與家族手冊確認狀態

## 常見誤解糾偏

### 誤解 1：「『你』字判斷需要語義理解」

**錯誤理解**：分析用戶輸入的意圖，判斷是否「在對 Agent 說話」。

**正確理解**：純機械式字符串包含檢查，`if "你" in user_input:`，不需要語義理解。這是為了速度——語義理解需要 100+ token，字符串檢查只需要 1 token。

### 誤解 2：「Sub-Agent 也需要『你』字判斷」

**錯誤理解**：Sub-Agent 收到任務後，應該判斷這個任務是簡單還是複雜。

**正確理解**：Sub-Agent **禁止**執行「你」字判斷。任務已由 Main Agent 分配，Sub-Agent 的職責是「執行」，不是「路由」。身份判斷由 SOUL.md / agent-bootstrap 統一處理。

### 誤解 3：「協調者可以修改需求」

**錯誤理解**：協調者作為「大腦」，應該在傳遞過程中優化需求。

**正確理解**：協調者是「郵差」，只負責傳遞，不負責拆信、讀信、改信。原始需求一字不改傳遞給 Planner。

## 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|---------|
| v1.0.0 | 2026-05-07 | 初始版本，定義基本路由規則 |
| v1.1.0 | 2026-05-10 | 加入「你」字判斷適用範圍（僅限 Main Agent）、手動覆蓋機制、層級限制（硬性兩層）、Sub-Agent 禁用路由判斷；與 agent-coordination-mode LLM 版 v1.2.0 對齊 |

---

*最後更新：2026-05-10*
*本檔案為 reference/ 詳細展開，LLM 執行指令請參考 agent-coordination-mode/assets/SKILL.md*
