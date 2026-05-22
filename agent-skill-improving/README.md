---
title: Skill Improvement Operations Manual
name: agent-skill-improving
description: 技能改進操作手冊。涵蓋Guardian Pattern事前強制架構、腳本更名規範、Patch應用策略分級、強制合規驗證、跨平台兼容檢查、長內容處理檢查、臨時文件管理檢查。融入conversation_append.py v1.4.0長文件經驗及github-skill-organizer v1.0.4-v1.0.12教訓。
version: v1.2.5
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-22T16:44:06+08:00
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: ".env"
file_mapping:
  - local_path: "README.md"
    github_path: "agent-skill-improving/README.md"
---

# agent-skill-improving — 技能改進操作手冊

> 當前版本：v1.2.5
> 配套文件：SKILL.md v1.2.5 + CONTRIBUTING.md（已遷移至 github-skill-organizer）+ SOUL.md v5.0 + IDENTITY.md v5.0
> **核心變更：v1.2.5 引入 Guardian Pattern 事前強制架構，腳本全面更名。注意：Issue 報告器已遷移至 github-skill-organizer 技能。**

---

## 一、定位與原則

agent-skill-improving **不是給 Agent 自由發揮的技能**，而是**框架守衛**。

| 角色 | 說明 |
|------|------|
| Agent | 執行改進操作（Patch 應用、合規驗證）|
| 主人 | 現場定框架、審核 [FRAMEWORK] 級 Issue |
| 本技能 | **用代碼強制 Agent 遵守規範**，而非語言勸說 |

**核心原則：用代碼約束 Agent，而非語言。**
Agent 不會記住規則，但 Agent 會調用腳本。Guardian Pattern 確保 Agent 在犯錯之前就被阻止。

---

## 二、Guardian Pattern 架構（v1.2.5 新增）

### 2.1 三層防禦

```
Agent 想創建/修改文件
        ↓
┌─────────────────────────────────────────┐
│ 第一層：Framework Guard（框架守衛）      │
│ 腳本：skill_files_designer.py           │
│ 作用：Agent 禁止直接 open()/write_text() │
│       必須通過腳本生成 frontmatter       │
│ 結果：無法生成沒有身份證的文件            │
└─────────────────────────────────────────┘
        ↓ PASS
┌─────────────────────────────────────────┐
│ 第二層：Self-Diagnosis（自我診斷）       │
│ 腳本：skill_integrity_checker.py        │
│ 作用：修改後自動執行 28+ 項合規檢查      │
│ 結果：發現問題立即報錯，不上傳            │
└─────────────────────────────────────────┘
        ↓ PASS
┌─────────────────────────────────────────┐
│ 第三層：Issue Classifier（問題分類）     │
│ 作用：區分 [FRAMEWORK] / [RUNTIME] / [AGENT-BUG]│
│ 結果：只有 [FRAMEWORK] 上報主人           │
└─────────────────────────────────────────┘
```

### 2.2 腳本更名對照表（v1.2.5）

| 舊名稱 | 新名稱 | 功能 |
|--------|--------|------|
| skill_validate.py | **skill_integrity_checker.py** | 合規檢查器（23+ 項檢查 + 8 項紅線）|
| skill_improving.py | **skill_patch_validator.py** | Patch 應用與驗證 |
| frontmatter_generator.py + file_creation_guard.py | **skill_files_designer.py** | 文件設計器（生成 frontmatter + 攔截直接寫入）|
| skill_bootstrap.py | **skill_folder_designer.py** | 文件夾設計器（初始化技能目錄結構）|

**舊名稱腳本已廢棄，Agent 必須使用新名稱。**

### 2.3 身份證制度（強制）

所有技能文件（.md / .py / .json / .html）必須包含統一 frontmatter/docstring。
沒有身份證的文件是**非法的**，不能上傳，必須報錯。

```yaml
---
title: 描述性標題（≠ name）
name: 技能名（固定）
description: 描述
version: x.x.x
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-22T16:44:06+08:00
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: ".env"
file_mapping:
  local_path: "文件名.擴展名"
  github_path: "技能名/文件名.擴展名"
---
```

**注意：github_path 禁止前導 "/"，必須是相對路徑。**

---

## 三、操作手冊

### Step 1：確認改進目標（主人審核）

Agent 確認改進目標：

- 目標技能：**{技能名稱}** v{版本}
- 改進類型：**{patch / refactor / docs}**
- 跨平台：**{Windows / Linux/macOS / 通用}**
- 長內容：**{是 / 否}**

**[SUGGEST] agent-skill-improving**
Skill: **{技能名}** v{版本}
Defect: **{缺陷描述}**
Impact: **{影響範圍}**
Cross-Platform: **{平台}**
Long-Content: **{是否長內容}**
Proposed Fix: **{建議修復}**
Confirm: [YES / NO / DEFER]

**確認後執行：**

### Step 2：改進執行（Agent 操作）

```bash
# 1. 合規檢查（改進前）
python skill_integrity_checker.py --skill-dir ./{skill_name}/ --strict

# 2. 應用 Patch
python skill_patch_validator.py --skill-dir ./{skill_name}/ --patch-file ./improve/{skill_name}/PATCH.md

# 3. 合規檢查（改進後）
python skill_integrity_checker.py --skill-dir ./{skill_name}/ --strict --report-path ./improve/{skill_name}/VALIDATION_REPORT.md

# 4. 上傳驗證（通過後）
python skill_files_designer.py --validate-only --skill-dir ./{skill_name}/
```

### Step 3：上傳與閉環

```bash
# 上傳改進後的技能
# commit message 必須包含 Fixes #{issue_number} 以自動關閉 Issue
```

---

## 四、腳本詳細說明

### 4.1 skill_integrity_checker.py（合規檢查器）

**功能**：掃描技能目錄，執行 28+ 項合規檢查 + 8 項架構紅線。

**檢查項（v1.2.5 新增）**：
- frontmatter 字段完整性（所有必填字段是否存在）
- github_path 前導 "/" 檢查（禁止前導斜杠）
- updated_at ISO 8601 格式驗證
- version 一致性（所有文件 version 必須相同）
- file_mapping 完整性（local_path 和 github_path 必須成對）
- 文件名規範（xxx.yyy.zzz.ext，禁止 - 和 _）
- 必要文件結構（SKILL.md、README.md 等）

**用法**：
```bash
python skill_integrity_checker.py --skill-dir ./{skill_name}/ --strict
```

### 4.2 skill_patch_validator.py（Patch 驗證器）

**功能**：應用 Patch、驗證、回滾保護。

**策略分級**：
| 策略 | 風險 | 說明 |
|------|------|------|
| A replace_in_file | 低 | 精確替換，可逆 |
| B 多行插入 | 中 | 需確認上下文匹配 |
| C write_to_file 覆蓋 | 高 | 強制備份，超過 3 次需主人確認 |

**用法**：
```bash
python skill_patch_validator.py --skill-dir ./{skill_name}/ --patch-file PATCH.md
```

### 4.3 skill_files_designer.py（文件設計器）

**功能**：生成標準 frontmatter + 攔截直接寫入操作。

**核心機制**：
- Agent 禁止直接 `open()` / `write_text()` 創建 .md/.py/.json/.html
- 必須通過 `skill_files_designer.py` 生成 frontmatter 後再寫入
- 自動填充 github_repository、target_branch、file_mapping
- 支持 .py 文件的 docstring YAML 塊格式

**用法**：
```python
from skill_files_designer import SkillFileWriter

with SkillFileWriter(
    file_path="scripts/new_module.py",
    skill_name="github-skill-organizer",
    description="Handles new feature"
) as writer:
    writer.write("# 業務代碼...")
    # 自動在文件開頭插入 frontmatter
```

### 4.4 skill_folder_designer.py（文件夾設計器）

**功能**：初始化新技能目錄結構，自動生成所有必要文件的 frontmatter。

**生成結構**：
```
new-skill/
├── README.md（含 frontmatter）
├── LLM/SKILL.md（含 frontmatter）
├── scripts/（可選）
├── config/（可選）
└── assets/（可選）
```

**用法**：
```bash
python skill_folder_designer.py --name "new-skill" --description "..." --version "1.0.0"
```

---

## 五、版本迭代記錄

| 版本 | 日期 | 變更內容 |
|------|------|---------|
| v1.2.0 | 2026-05-11 | 初始版本，涵蓋 Patch 應用策略分級 |
| v1.2.1 | 2026-05-11 | 新增 skill_integrity_checker.py（原 skill_validate.py）合規驗證 |
| v1.2.2 | 2026-05-12 | Patch 應用策略細化（replace_in_file vs write_to_file）|
| v1.2.3 | 2026-05-13 | 新增跨平台兼容檢查、長內容處理檢查、臨時文件管理檢查 |
| v1.2.4 | 2026-05-13 | 新增強制合規驗證、frontmatter 統一規範、身份證制度 |
| **v1.2.5** | **2026-05-22** | **引入 Guardian Pattern 事前強制架構、腳本全面更名、github_path 前導 "/" 防禦處理。注意：Issue 報告器後續遷移至 github-skill-organizer** |

---

## 六、常見問題（Q&A）

**Q1：為什麼要更名腳本？**
A：舊名稱（skill_validate、skill_improving）語義模糊，Agent 容易誤解。新名稱（skill_integrity_checker、skill_patch_validator）明確表達功能，減少誤用。

**Q2：為什麼禁止 Agent 直接寫入文件？**
A：v1.0.4-1.0.11 的教訓證明，Agent 會反覆生成沒有 frontmatter 的文件。只有通過腳本強制插入 frontmatter，才能保證 100% 合規。

**Q3：什麼是 [FRAMEWORK] Issue？**
A：涉及架構決策的問題（如"是否需要新增文件類型？"、"semantic-release 配置如何調整？"）。這類問題 Agent 不能自行決定，必須上報主人。

**Q4：如何做到 Issue 自動閉環？**
A：Agent 發現 [RUNTIME] 問題 → 創建 Issue → 自行修復 → Commit message 包含 `Fixes #{issue_number}` → GitHub 自動關閉 Issue → Agent 本地驗證。只有 [FRAMEWORK] 問題需要主人介入。

---

## 七、配套文件

| 文件 | 說明 |
|------|------|
| SKILL.md | LLM 執行指令（含 LOCK-009~012）|
| SOUL.md v5.0 | 人格定義 |
| IDENTITY.md v5.0 | 身份定義 |
| scripts/USAGE.md | 腳本使用教程 |
| scripts/skill_integrity_checker.py | 合規檢查器 |
| scripts/skill_patch_validator.py | Patch 驗證器 |
| scripts/skill_files_designer.py | 文件設計器 |
| scripts/skill_folder_designer.py | 文件夾設計器 |
| assets/SKILL.CORRECTIONS.md | 技能修正記錄 |
| assets/SCRIPT.CORRECTIONS.md | 腳本修正記錄 |

> 注意：Issue 報告相關功能（skill_issue_reporter.py、CONTRIBUTING.md）已遷移至 **github-skill-organizer** 技能。
