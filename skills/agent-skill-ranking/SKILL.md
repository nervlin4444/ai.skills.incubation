---
name: agent-skill-ranking
description: >
  技能效能評分與優先級排序（LAYER 4: Meta Skill — 按需獨立調用）。
  定期或在 finishing 後讀取 SKILL_CORRECTION.md 的歷史記錄，
  計算各 skill 的成功率、效率、成本、魯棒性、安全性、一致性，
  生成 skill 推薦清單供未來任務優先選用。
  當用戶要求評估技能生態健康度，或 finishing 完成後自動觸發。

license: PROPRIETARY

metadata:
  version: "1.1.0"
  version_date: "2026-05-06"
  previous_version: "1.0.0"
  memory_policy: "SKILL.md 為準，MEMORY.md 僅供狀態追溯"
  change_summary: "徹底重寫 description，聚焦評分排序；明確 LAYER 4 Meta Skill 定位；與 improving 區分職責。"
  author: "Kevin Lin"
  skill_bundle: "agent-harness-by-kevinlinz"
  file_role: "skill-ranking"

  confidence: "HIGH"
  confidence_reason: "評分機制經主人直接定義，基於 SKILL_CORRECTION.md 數據進行客觀計算。"

  provenance_state: "EVOLVING"
  provenance_reason: "v1.1.0 明確按需調用定位，評分維度可能隨實戰經驗擴充。"

  contradicted_by: []
  inferred_paragraph: false
  inferred_reason: null

  layer: "LAYER 4"
  layer_name: "Meta Skill"
  invocation_mode: "on-demand"

  input_source: "SKILL_CORRECTION.md"
  output_artifact: "SKILL_RANKING.md"

  allowed_tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
  requires:
    env: []
    bins: []

  related_skills:
    - "agent-skill-acquiring"
    - "agent-skill-improving"
    - "agent-mission-planning"
    - "agent-mission-finishing"
    - "agent-conversation-mode"

  estimated_tokens:
    frontmatter: 320
    body: 700
    total: 1020

---

# Agent Skill Ranking — 技能效能評分與優先級排序（LAYER 4）

## 架構定位

本 skill 屬於 **LAYER 4: Meta Skill**，是**按需獨立調用**的工具書：

| 層級 | 名稱 | 運行方式 | 代表 Skill |
|------|------|---------|-----------|
| LAYER 0 | Bootstrap | 強制第一個載入 | agent-bootstrap |
| LAYER 1 | Background | 持續運行，透明 | agent-conversation-mode |
| LAYER 2 | Router | 每次任務觸發 | agent-coordination-mode |
| LAYER 3 | Mission | 按需順序執行 | planning / evaluating / crafting / finishing |
| **LAYER 4** | **Meta** | **按需獨立調用** | **acquiring / improving / ranking** |

**與 LAYER 4 其他 Meta Skills 的職責區分**：

| Meta Skill | 核心職責 | 輸出物 | 與 Ranking 的關係 |
|-----------|---------|--------|------------------|
| agent-skill-acquiring | 搜尋並確認可用技能 | 技能清單 | Ranking 的輸入來源之一 |
| agent-skill-improving | 收集反饋，生成改善建議 | SKILL_CORRECTION.md | **Ranking 的主要輸入源** |
| **agent-skill-ranking** | **評分排序，推薦技能** | **SKILL_RANKING.md** | — |

**調用示例**：
- Finishing 後需要評估本次任務使用的技能表現 → **調用 Ranking**
- 定期獨立運行，審視整體技能生態健康度 → **調用 Ranking**
- 用戶主動要求「看看哪些技能最可靠」 → **調用 Ranking**
- **不是固定順序**：按需調用

**與 LAYER 1 的間接關聯**：
- agent-skill-ranking 會讀取 `assets/CONVERSATION.md`（由 conversation-mode 生成）
- 進行統計分析，計算各 skill 的綜合評分
- **這不是顯式調用關係**，而是「記錄者 → 消費者」的數據流

## 1. 評分維度

從 SKILL_CORRECTION.md 讀取歷史記錄，計算以下 6 個維度：

| 維度 | 欄位名 | 說明 | 權重建議 |
|------|--------|------|---------|
| 成功率 | 最終成功率 | 成功步驟數 / 總步驟數 | 30% |
| 效率 | 最終完成效率 | 步數、時間、工具調用次數綜合評估 | 20% |
| 成本 | 最終完成成本 | LLM Tokens 消耗量 | 15% |
| 魯棒性 | 最終完成魯棒性 | 環境變化時的穩定性 | 15% |
| 安全性 | 最終完成安全性 | 是否出現越權操作 | 10% |
| 一致性 | 最終完成一致性 | 多次運行結果的穩定性 | 10% |

## 2. 計算方法

### 2.1 單 Skill 評分

```
Skill Score = (成功率 × 0.30) + (效率 × 0.20) + (成本 × 0.15) + 
              (魯棒性 × 0.15) + (安全性 × 0.10) + (一致性 × 0.10)
```

- 每個維度取值範圍：0-100%
- 最終得分範圍：0-100%
- 保留小數點後 1 位

### 2.2 多任務加權平均

如果同一 skill 有多次執行記錄：

```
Weighted Score = Σ(單次得分 × 該次任務權重) / Σ(任務權重)
```

- 最近 7 天的任務權重：1.0
- 最近 30 天的任務權重：0.7
- 超過 30 天的任務權重：0.3

## 3. 輸出格式

### 3.1 SKILL_RANKING.md 結構

```markdown
# SKILL_RANKING.md - 技能效能評分與推薦

**生成時間**: [YYYY-MM-DD HH:mm]  
**Ranking Agent**: agent-skill-ranking  
**數據來源**: SKILL_CORRECTION.md + CONVERSATION.md  

---

## 📊 技能評分總覽

| 排名 | Skill 名稱 | 綜合得分 | 成功率 | 效率 | 成本 | 魯棒性 | 安全性 | 一致性 | 推薦等級 |
|------|-----------|---------|--------|------|------|--------|--------|--------|---------|
| 1 | [skill-name] | [X.X] | [X]% | [X]% | [X]% | [X]% | [X]% | [X]% | ⭐⭐⭐⭐⭐ |
| 2 | [skill-name] | [X.X] | [X]% | [X]% | [X]% | [X]% | [X]% | [X]% | ⭐⭐⭐⭐ |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

---

## 🏆 推薦清單（按任務類型）

### 任務類型：[類型名稱]

| 推薦順序 | Skill 名稱 | 適用場景 | 預期表現 |
|---------|-----------|---------|---------|
| 1 | [skill-name] | [場景描述] | [預期成功率]% |
| 2 | [skill-name] | [場景描述] | [預期成功率]% |

---

## 📈 趨勢分析

### 上升趨勢（最近 7 天得分提升）
- [skill-name]: [舊得分] → [新得分] (+[X.X])

### 下降趨勢（最近 7 天得分下降）
- [skill-name]: [舊得分] → [新得分] (-[X.X])

### 需關注（得分低於 60 分）
- [skill-name]: [得分] — 建議：[改善建議]

---

## 📝 歸檔資訊

- **SKILL_CORRECTION.md 路徑**: `[路徑]`
- **CONVERSATION.md 路徑**: `[路徑]`
- **SKILL_RANKING.md 路徑**: `skills/agent-skill-ranking/assets/SKILL_RANKING.md`

---

## 📅 版本記錄

| 版本 | 日期 | 修改內容 | 修改者 |
|------|------|----------|--------|
| v1.0 | [日期] | 初始版本 | agent-skill-ranking |
```

## 4. 輸出規範

- 輸出 SKILL_RANKING.md 完整內容
- 提供下載連結
- 標註數據來源（SKILL_CORRECTION.md 的時間範圍）
- 如發現得分異常低的 skill，輸出警告與改善建議

## 5. 版本記錄

| 版本 | 日期 | 修改內容 | 修改者 |
|------|------|----------|--------|
| v1.0 | 2026-05-01 | 初始版本（description 複製 improving） | agent-skill-ranking |
| v1.1 | 2026-05-06 | 徹底重寫 description，聚焦評分排序；明確 LAYER 4 Meta Skill 定位；與 improving 區分職責 | agent-skill-ranking |
