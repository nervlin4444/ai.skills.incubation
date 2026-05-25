---
title: Sub-Agent Communication Protocols
name: agent-coordination-mode
description: Standard communication protocols between coordinator and Sub-Agents. Defines appointment format, output format, memory isolation mechanism, responsibility tracing flow, layer markers, and family manual loading confirmation.
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
  local_path: "{baseDir}/SUB_AGENT_PROTOCOLS.md"
  github_path: "agent-coordination-mode/references/SUB_AGENT_PROTOCOLS.md"
---

# SUB_AGENT_PROTOCOLS.md — 協調者與 Sub-Agent 溝通協議

## 文件定位

| 檔案 | 讀者 | 用途 |
|------|------|------|
| agent-coordination-mode/assets/SKILL.md | LLM 執行 | 執行指令集（精簡版） |
| 本檔（reference/SUB_AGENT_PROTOCOLS.md） | 主人/開發者 | 溝通協議詳細展開、記憶隔離機制說明 |

本檔為 reference/ 下的詳細展開文件，供人類理解協調者與 Sub-Agent 的溝通規範。LLM 執行時以 assets/SKILL.md 為準。

## 協議核心原則

1. **單向傳遞**：協調者 → Sub-Agent（任命書）→ 協調者（輸出）
2. **禁止繞過**：Sub-Agent 之間不直接溝通，所有狀態通過協調者中轉
3. **記憶隔離**：每個 Sub-Agent 只加載自己的 SKILL.md，不讀其他步驟的規範
4. **輕量中轉**：協調者只傳遞，不執行、不評估、不修改
5. **層級標記**：每個任命書必須包含層級標記（L1 / L2 / L3）
6. **家族手冊強制**：每個 Sub-Agent 必須載入完整的 agent-harness-engineering 技能包

## 溝通格式

### 協調者 → Sub-Agent（任命階段）

```markdown
# APPOINTMENT — 任命書

## 層級標記
當前層級：L1
任命者：Main Agent（L0）
被任命者層級：L1

## 原始需求
[用戶原始輸入，一字不改]

## 角色定義
- 角色：戰略大師（Planner）
- 職責：拆解大任務為子任務
- 輸出物：CHECKLIST.md

## 家族手冊載入確認（被任命者勾選）
- [ ] agent-bootstrap
- [ ] agent-conversation-mode
- [ ] agent-coordination-mode
- [ ] agent-mission-planning（自身）

## 層級限制聲明
- 當前層級：L1
- 可召喚 Sub-Agent：是（最多到 L2）
- 如需 L3：必須向 Main Agent 申請

## 經驗約束
| 嚴重度 | 約束 | 來源 |
|--------|------|------|
| P0 | [禁止行為] | [坑編號] |
```

**為何使用 Markdown 而非 JSON？**
- 低基準 LLM（如 Hy3 Preview）解析 JSON 容易出錯
- Markdown 表格和列表對 LLM 更友好，條件反射理解更快
- 人類可直接閱讀，無需格式化工具

### Sub-Agent → 協調者（輸出階段）

```markdown
# DELIVERY — 交付報告

## 任務標識
任務ID：T-YYYYMMDDHHMMSS
步驟：PLANNING / EVALUATING / CRAFTING / FINISHING
被任命者：agent-mission-planning

## 狀態
狀態：DONE / BLOCKED / PARTIAL

## 輸出
[輸出內容或文件路徑]

## 問題（如有）
- [問題1簡述]
- [問題2簡述]

## 下一步建議
建議任命：[下一步 Skill 名稱]
原因：[一句話說明]

## 家族手冊確認
- [x] agent-bootstrap → [BOOTSTRAP] 已鎖定
- [x] agent-conversation-mode → 已記錄
- [x] agent-coordination-mode → 已確認
- [x] 自身 SKILL.md → 已執行
```

## 記憶隔離機制

### Sub-Agent 加載規則

| Sub-Agent | 允許讀取 | 禁止讀取 |
|-----------|---------|---------|
| Planner | 自己的 SKILL.md + 原始需求 + EXPERT_LIST.md | 其他 Sub-Agent 的 SKILL.md |
| Evaluator | 自己的 SKILL.md + CHECKLIST.md + 原始需求 | Generator 的執行細節、Planner 的拆解邏輯 |
| Generator | 自己的 SKILL.md + CHECKLIST.md + 原始需求 + CORRECTIONS.md | Planning 的拆解邏輯、Evaluating 的評估標準 |
| Finishing | 自己的 SKILL.md + 所有輸出 + 原始需求 | 執行過程的中間狀態 |

### 為什麼要隔離

- 如果 Generator 讀了 Planning 的詳細規範 → 上下文被規則填滿 → 忘記本來要生成什麼
- 如果 Evaluator 讀了 Generator 的代碼 → 注意力分散 → 評估標準被干擾
- **每個 Sub-Agent 只關心自己的職責，其他交給協調者**

### 身份確認與層級隔離

Sub-Agent 載入後，必須執行以下確認：

```
1. 讀取任命書中的「層級標記」
2. 確認自己是 Sub-Agent（L1+），不是 Main Agent
3. 確認禁止執行「你」字判斷
4. 確認家族手冊已載入（4 項勾選）
5. 確認層級限制（L1 可召喚 L2，L2 禁止召喚 L3）
```

**身份確認由 SOUL.md / agent-bootstrap 統一處理**，不在每個 Sub-Agent 的 SKILL.md 中重複。

## 層級限制硬停止機制

### L2 Sub-Sub-Agent 的行為規範

```
收到任命書
    |
    v
檢查層級標記 → L2
    |
    v
確認可召喚層級 → 無（需申請 L3）
    |
    v
執行分配任務
    |
    v
如需召喚 Sub-Agent → 檢查當前層級
    |
    ├── 當前層級 < 2 → 生成任命書，標記 L+1
    |
    └── 當前層級 >= 2 → 硬停止
            |
            v
            輸出：[LAYER-LIMIT] 已達層級上限
            動作：向 Main Agent 申請 L3
            禁止：自動批准或繼續執行
```

## 責任追溯機制

當輸出偏離原始需求時：

```
Step 1: 檢查任命書
  → 原始需求是否完整？
  → 經驗約束是否傳遞？
  → 層級標記是否正確？
  → 家族手冊確認是否勾選？
  → 如果任命書丟失信息 → 協調者責任

Step 2: 檢查 Sub-Agent 輸出
  → 是否遵守了任命書的所有約束？
  → 輸出格式是否符合預期？
  → 家族手冊是否已載入？
  → 如果 Sub-Agent 理解錯誤 → Sub-Agent 責任

Step 3: 檢查協調者中轉
  → 是否正確傳遞了 Sub-Agent 的輸出？
  → 是否丟失了關鍵信息？
  → 如果中轉丟失 → 協調者責任

Step 4: 檢查層級限制
  → 是否超過兩層限制？
  → L3 是否經過申請和批准？
  → 如果層級超限 → 協調者與 Sub-Agent 共同責任
```

## checklist.md 合併機制

### 每層 checklist 的定位

| 層級 | checklist 內容 | 合併方式 |
|------|----------------|---------|
| L0（Main Agent） | 全局任務清單、人力分配、資源追蹤 | 頂層，所有子任務合併至此 |
| L1（Sub-Agent） | 子任務清單、執行步驟、驗收標準 | 完成後合併到 L0 checklist |
| L2（Sub-Sub-Agent） | 原子任務清單、技術細節、測試用例 | 完成後合併到 L1 checklist，再合併到 L0 |
| L3（已批准） | 極細粒度任務、邊界值測試 | 完成後合併到 L2 → L1 → L0 |

### 合併時機

- **Sub-Agent 完成任務後**：將自身 checklist 合併到上一層 checklist
- **合併內容**：任務摘要、完成狀態、發現的問題、修正措施、驗收結果
- **合併格式**：在上一層 checklist 的對應項下，以「子任務」形式附加

### 修正歷史合併

- **發現問題 → 修正 → 複檢通過後**：
  - 在當前層 checklist 記錄：「修正歷史：{問題} → {措施} → {結果}」
  - 合併到上一層時，修正歷史一併合併
  - 最終所有修正歷史匯總到 L0 checklist 的「質量報告」章節

## 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|---------|
| v1.0.0 | 2026-05-07 | 初始版本，定義基本溝通格式與記憶隔離 |
| v1.1.0 | 2026-05-10 | 加入層級標記、家族手冊載入確認、層級限制硬停止機制、checklist 合併機制；與 SOUL.md v4.2 及 agent-bootstrap 身份判斷對齊；改用 Markdown 格式替代 JSON |

---

*最後更新：2026-05-10*
*本檔案為 reference/ 詳細展開，LLM 執行指令請參考 agent-coordination-mode/assets/SKILL.md*
