---
title: "Agent Skill Improving - Scripts Usage Guide"
name: agent-skill-improving
description: "技能改進腳本使用教程。涵蓋合規檢查器、Patch驗證器、文件設計器（含提取模組）、文件夾設計器。人類可讀的操作指南。v1.3.0 更新 skill_files_designer 提取功能說明。"
version: v1.3.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-23T16:10:00+08:00
fixes: []
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: ".env"
file_mapping:
  local_path: scripts/USAGE.md
  github_path: agent-skill-improving/scripts/USAGE.md
---

# Agent Skill Improving — 腳本使用教程 v1.3.0

> 本文件是給人類閱讀的腳本使用教程。
> LLM 應該閱讀 SKILL.md（執行指令），而非本文件。
> v1.3.0 更新：skill_files_designer 合併 SkillFrontmatterExtractor，統一讀取與生成入口。

---

## 腳本清單

| 腳本 | 功能 | 觸發時機 |
|------|------|----------|
| skill_integrity_checker.py | 合規檢查（30+ 項 + 9 項紅線） | 改進前後必須執行 |
| skill_patch_validator.py | Patch 應用、驗證、回滾 | 主人確認改進後 |
| skill_files_designer.py | 文件 frontmatter 生成 + 攔截寫入 + **統一提取** | 創建/修改/讀取任何技能文件時 |
| skill_folder_designer.py | 初始化技能目錄結構 | 創建新技能時 |

---

## 1. skill_integrity_checker.py（合規檢查器）

### 功能
掃描技能目錄，執行 30+ 項合規檢查 + 9 項架構紅線。

### 檢查項（v1.3.0）
- frontmatter 字段完整性（title, name, description, version, github_repository, target_branch, updated_at, auth_config, file_mapping, fixes）
- github_path 前導 / 檢查（禁止前導斜杠）
- updated_at ISO 8601 格式驗證
- version 一致性（所有文件 version 必須相同）
- file_mapping 完整性（local_path 和 github_path 必須成對）
- 文件名規範（xxx.yyy.zzz.ext，禁止 - 和 _）
- 必要文件結構（SKILL.md、README.md 等）
- fixes 欄位必須存在（key 必須在，值可為 []）
- Fixes 聲明一致性（代碼與 frontmatter 匹配）

### 用法
```bash
# 基礎檢查
python skill_integrity_checker.py --skill-dir ./github-skill-organizer/

# 嚴格模式（9 項紅線全部啟用）
python skill_integrity_checker.py --skill-dir ./github-skill-organizer/ --strict

# 輸出報告到文件
python skill_integrity_checker.py --skill-dir ./github-skill-organizer/ --strict --report-path ./improve/VALIDATION_REPORT.md
```

### 參數

| 參數 | 說明 | 必填 |
|------|------|------|
| --skill-dir | 技能目錄路徑 | 是 |
| --strict | 啟用 9 項架構紅線 | 否 |
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

## 3. skill_files_designer.py（文件設計器 v1.3.0）

### 功能
生成標準 frontmatter，攔截 Agent 直接寫入操作，**統一提取 frontmatter**。

### 核心機制
- Agent 禁止直接 `open()` / `write_text()` 創建 .md/.py/.json/.html
- 必須通過 `skill_files_designer.py` 生成 frontmatter 後再寫入
- 自動填充 github_repository、target_branch、file_mapping
- **自動檢測代碼中的 Fixes 聲明**（如 `# Fixes #5`）並寫入 frontmatter `fixes` 欄位
- `fixes` 欄位必須存在（key 必須在），值可為空列表 `[]` 或整數列表 `[5, 6]`
- 支持 .py 文件的 docstring YAML 塊格式
- **v1.3.0 新增：SkillFrontmatterExtractor 統一提取接口**
  - `extract(file_path)` → 自動根據後綴選擇提取方式（.md/.py/.json/.html/.env）
  - `get_github_path(frontmatter)` → 支持 dict/list 格式
  - `get_fixes(frontmatter)` → 支持 list/int/str 格式
  - `validate(frontmatter)` → 檢查 10 個強制欄位

### 用法（生成 - Python API）
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

### 用法（提取 - Python API）
```python
from skill_files_designer import SkillFrontmatterExtractor

# 提取任意技能文件的 frontmatter
fm = SkillFrontmatterExtractor.extract("scripts/sync_engine.py")
print(fm['version'])  # 輸出版本號

# 提取 github_path（自動處理 dict/list 格式）
github_path = SkillFrontmatterExtractor.get_github_path(fm)

# 提取 fixes（自動處理 list/int/str 格式）
fixes = SkillFrontmatterExtractor.get_fixes(fm)

# 驗證 frontmatter 完整性
ok, missing = SkillFrontmatterExtractor.validate(fm)
if not ok:
    print("缺少欄位:", missing)
```

### 用法（命令行）
```bash
# 驗證現有文件 frontmatter
python skill_files_designer.py --validate-only --skill-dir ./github-skill-organizer/

# 生成單個文件的 frontmatter（不寫入，僅輸出到 stdout）
python skill_files_designer.py --generate-frontmatter --file-type md --skill-name github-skill-organizer --title "New Module"

# 提取指定文件的 frontmatter（v1.3.0 新增）
python skill_files_designer.py --extract-only --file-path ./github-skill-organizer/scripts/sync_engine.py
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

## 常見問題

**Q1：舊腳本 skill_validate.py 和 skill_improving.py 還能用嗎？**
A：不能。v1.2.5 已全面更名，舊腳本已廢棄。請使用 skill_integrity_checker.py 和 skill_patch_validator.py。

**Q2：fixes 欄位什麼時候填 []，什麼時候填 [5]？**
A：
- `fixes: []` → 新增功能、優化重構、文檔更新、常規維護（無關聯 Issue）
- `fixes: [5]` → 修復 Issue #5（代碼中寫入 `# Fixes #5`，skill_files_designer.py 自動檢測）
- **fixes 欄位必須存在**，不能省略。省略 = 報錯拒絕上傳。

**Q3：skill_integrity_checker.py 和舊版 skill_validate.py 有什麼區別？**
A：skill_integrity_checker.py 是 v1.2.5 更名後的版本，檢查項從 23+ 增加到 30+，新增 fixes 欄位檢查、Fixes 一致性檢查、github_path 前導斜杠檢查、updated_at ISO 格式驗證等。

**Q4：為什麼禁止 Agent 直接寫入文件？**
A：v1.0.4-1.0.11 的教訓證明，Agent 會反覆生成沒有 frontmatter 的文件。只有通過腳本強制插入 frontmatter，才能保證 100% 合規。

**Q5：skill_frontmatter_extractor.py 去哪了？**
A：v1.3.0 已合併入 skill_files_designer.py。所有提取功能統一從 skill_files_designer 導入 SkillFrontmatterExtractor。舊的獨立檔案已廢棄。

**Q6：如何初始化新技能目錄？**
A：使用 skill_folder_designer.py --name ... --description ...，默認輸出到當前目錄。

---

## 版本記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| v1.1.0 | 2026-05-11 | 初始版本，涵蓋 skill_validate 和 skill_improving |
| v1.2.5 | 2026-05-22 | 腳本全面更名，新增 fixes 欄位規範，更新所有用法說明 |
| **v1.3.0** | **2026-05-23** | **skill_files_designer 合併 SkillFrontmatterExtractor，新增 --extract-only 命令行參數，統一文件讀取與生成入口** |
