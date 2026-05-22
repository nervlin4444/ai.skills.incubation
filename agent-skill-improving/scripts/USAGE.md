---
title: "Agent Skill Improving - Scripts Usage Guide"
name: agent-skill-improving
description: 技能改進腳本使用教程。涵蓋合規檢查器、Patch驗證器、文件設計器、文件夾設計器、Issue報告器。人類可讀的操作指南。
version: "v1.2.5"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-22T16:25:32+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "scripts/USAGE.md"
  github_path: "agent-skill-improving/scripts/USAGE.md"
---

# Agent Skill Improving — 腳本使用教程 v1.2.5

> 本文件是給人類閱讀的腳本使用教程。
> LLM 應該閱讀 SKILL.md（執行指令），而非本文件。
> v1.2.5 更新：腳本全面更名，新增 skill_issue_reporter.py。

---

## 腳本清單

| 腳本 | 功能 | 觸發時機 |
|------|------|----------|
| skill_integrity_checker.py | 合規檢查（28+ 項 + 8 項紅線） | 改進前後必須執行 |
| skill_patch_validator.py | Patch 應用、驗證、回滾 | 主人確認改進後 |
| skill_files_designer.py | 文件 frontmatter 生成 + 攔截寫入 | 創建/修改任何技能文件時 |
| skill_folder_designer.py | 初始化技能目錄結構 | 創建新技能時 |
| skill_issue_reporter.py | 標準 Issue 報告生成 | 發現問題需報告時 |

---

## 1. skill_integrity_checker.py（合規檢查器）

### 功能
掃描技能目錄，執行 28+ 項合規檢查 + 8 項架構紅線。

### 檢查項（v1.2.5）
- frontmatter 字段完整性（title, name, description, version, github_repository, target_branch, updated_at, auth_config, file_mapping）
- github_path 前導 "/" 檢查（禁止前導斜杠）
- updated_at ISO 8601 格式驗證
- version 一致性（所有文件 version 必須相同）
- file_mapping 完整性（local_path 和 github_path 必須成對）
- 文件名規範（xxx.yyy.zzz.ext，禁止 - 和 _）
- 必要文件結構（SKILL.md、README.md 等）

### 用法

```bash
# 基礎檢查
python skill_integrity_checker.py --skill-dir ./github-skill-organizer/

# 嚴格模式（8 項紅線全部啟用）
python skill_integrity_checker.py --skill-dir ./github-skill-organizer/ --strict

# 輸出報告到文件
python skill_integrity_checker.py --skill-dir ./github-skill-organizer/ --strict --report-path ./improve/VALIDATION_REPORT.md
```

### 參數

| 參數 | 說明 | 必填 |
|------|------|------|
| --skill-dir | 技能目錄路徑 | 是 |
| --strict | 啟用 8 項架構紅線 | 否 |
| --report-path | 報告輸出路徑 | 否 |

---

## 2. skill_patch_validator.py（Patch 驗證器）

### 功能
讀取 Patch 文件，驗證合法性，應用變更，自動備份，支持回滾。

### 策略分級
| 策略 | 風險 | 說明 |
|------|------|------|
| A replace_in_file | 低 | 精確替換，可逆 |
| B 多行插入 | 中 | 需確認上下文匹配 |
| C write_to_file 覆蓋 | 高 | 強制備份，超過 3 次需主人確認 |

### 用法

```bash
# 應用 Patch
python skill_patch_validator.py --skill-dir ./github-skill-organizer/ --patch-file ./improve/PATCH.md

# 預覽模式（不實際修改）
python skill_patch_validator.py --skill-dir ./github-skill-organizer/ --patch-file ./improve/PATCH.md --dry-run

# 回滾上一次 Patch
python skill_patch_validator.py --skill-dir ./github-skill-organizer/ --rollback

# 僅驗證 Patch，不應用
python skill_patch_validator.py --skill-dir ./github-skill-organizer/ --patch-file ./improve/PATCH.md --validate-only
```

### 參數

| 參數 | 說明 | 必填 |
|------|------|------|
| --skill-dir | 技能目錄路徑 | 是 |
| --patch-file | Patch 文件路徑 | 是（--rollback 時不需要） |
| --dry-run | 預覽模式 | 否 |
| --rollback | 回滾上一次 Patch | 否 |
| --validate-only | 僅驗證不應用 | 否 |

---

## 3. skill_files_designer.py（文件設計器）

### 功能
生成標準 frontmatter，攔截 Agent 直接寫入操作。

### 核心機制
- Agent 禁止直接 `open()` / `write_text()` 創建 .md/.py/.json/.html
- 必須通過 `SkillFileWriter` 上下文管理器生成
- 自動填充 github_repository、target_branch、file_mapping

### 用法（Python API）

```python
from skill_files_designer import SkillFileWriter

# 創建 .md 文件
with SkillFileWriter(
    file_path="scripts/new_module.md",
    skill_name="github-skill-organizer",
    description="Handles new feature"
) as writer:
    writer.write("# 業務代碼...")
    # 自動在文件開頭插入 YAML frontmatter

# 創建 .py 文件（自動使用 docstring YAML 塊格式）
with SkillFileWriter(
    file_path="scripts/new_module.py",
    skill_name="github-skill-organizer",
    description="Core logic"
) as writer:
    writer.write("import os\n# 業務代碼...")
    # 自動在文件開頭插入 docstring 包裹的 YAML frontmatter
```

### 用法（命令行）

```bash
# 驗證現有文件 frontmatter
python skill_files_designer.py --validate-only --skill-dir ./github-skill-organizer/

# 生成單個文件的 frontmatter（不寫入，僅輸出到 stdout）
python skill_files_designer.py --generate-frontmatter --file-type md --skill-name github-skill-organizer --title "New Module"
```

---

## 4. skill_folder_designer.py（文件夾設計器）

### 功能
初始化新技能目錄結構，自動生成所有必要文件並嵌入 frontmatter。

### 生成結構

```
new-skill/
├── README.md              (含 frontmatter)
├── SKILL.md               (含 frontmatter)
├── .env.example           (含 frontmatter)
├── scripts/
│   ├── USAGE.md
│   └── new_skill_core.py  (含 docstring frontmatter)
└── assets/
    └── .gitkeep
```

### 用法

```bash
# 創建新技能
python skill_folder_designer.py --name "new-skill" --description "A new skill for ..."

# 指定基礎目錄（默認 ~/skills）
python skill_folder_designer.py --name "new-skill" --description "..." --skills-dir ~/workbuddy/skills

# 列出現有技能
python skill_folder_designer.py --list --skills-dir ~/workbuddy/skills
```

### 參數

| 參數 | 說明 | 必填 |
|------|------|------|
| --name | 技能名稱 | 是 |
| --description | 技能描述 | 是 |
| --skills-dir | 技能基礎目錄 | 否（默認 ~/skills） |
| --author | 作者名 | 否 |
| --list | 列出現有技能 | 否 |

---

## 5. skill_issue_reporter.py（Issue 報告器）— v1.2.5 新增

### 功能
強制按 CONTRIBUTING.md v1.2.5 規範生成標準 Issue 報告。

### 核心機制
- Agent 禁止自由發揮撰寫 Issue，必須通過此腳本生成
- 自動分類 [FRAMEWORK] / [RUNTIME] / [AGENT-BUG]
- 強制驗證每 Section >= 50 個中文字符
- 輸出 Markdown + JSON 雙格式

### 用法（程序化 — Agent 推薦）

```bash
# 從 stdin 讀取完整 JSON（Agent 生成後直接管道輸入）
cat issue_input.json | python skill_issue_reporter.py \
    --skill-dir ./github-skill-organizer/ \
    --from-stdin \
    --output-dir ./improve/issues
```

### 用法（交互式 — 人手觸發）

```bash
python skill_issue_reporter.py \
    --skill-dir ./github-skill-organizer/ \
    --interactive \
    --output-dir ./improve/issues
```

### 用法（命令行參數模式）

```bash
python skill_issue_reporter.py \
    --skill-dir ./github-skill-organizer/ \
    --classification "[RUNTIME]" \
    --summary "upload_skill 計數異常" \
    --repro-json ./repro.json \
    --root-cause-json ./root_cause.json \
    --proposed-fix-json ./proposed_fix.json \
    --output-dir ./improve/issues
```

### 參數

| 參數 | 說明 | 必填 |
|------|------|------|
| --skill-dir | 技能目錄路徑（必須包含 SKILL.md） | 是 |
| --output-dir | Issue 輸出目錄 | 否（默認 ./improve/issues） |
| --interactive | 交互式模式 | 否 |
| --dry-run | 預覽模式：驗證輸入但不寫入文件 | 否 |
| --from-stdin | 從 stdin 讀取完整 JSON | 否 |
| --classification | [FRAMEWORK] / [RUNTIME] / [AGENT-BUG] | 否（交互式/stdin 時不需要） |
| --summary | 問題摘要 | 否（交互式/stdin 時不需要） |
| --repro-json | 復現步驟 JSON 文件 | 否 |
| --root-cause-json | 根因分析 JSON 文件 | 否 |
| --proposed-fix-json | 建議修復 JSON 文件 | 否 |
| --attempted-json | 已嘗試修復 JSON 文件（可選） | 否 |
| --verification-json | 驗證結果 JSON 文件（可選） | 否 |

---

## 常見問題

**Q1：舊腳本 skill_validate.py 和 skill_improving.py 還能用嗎？**
A：不能。v1.2.5 已全面更名，舊腳本已廢棄。請使用 skill_integrity_checker.py 和 skill_patch_validator.py。

**Q2：為什麼 Issue 必須通過腳本生成？**
A：確保不同 LLM 輸出格式完全一致，減少主人審核成本。自由撰寫會導致格式、詳細程度、分類判斷不一致。

**Q3：skill_issue_reporter.py 生成的文件在哪裡？**
A：默認輸出到 `./improve/issues/ISSUE_{標題}_{時間戳}.md` 和 `.json`。可以通過 `--output-dir` 指定其他目錄。

**Q4：交互式模式和程序化模式有什麼區別？**
A：交互式模式通過問答收集信息，適合人手觸發。程序化模式通過 JSON 輸入，適合 Agent 自動化調用。

---

## 版本記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| v1.1.0 | 2026-05-11 | 初始版本，涵蓋 skill_validate 和 skill_improving |
| v1.2.5 | 2026-05-22 | 腳本全面更名，新增 skill_issue_reporter.py，更新所有用法說明 |
