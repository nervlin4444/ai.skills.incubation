---
title: "GitHub Skill Organizer"
name: github-skill-organizer
description: "GitHub 技能倉庫同步管理工具。批量上傳、比對、同步技能目錄到 GitHub。支持自動創建倉庫、衝突檢測、安全克隆、CHANGELOG 同步、標準 Issue 報告。v1.0.13 統一 frontmatter 格式並新增 fixes 欄位支持。"
version: "1.0.13"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T10:55:00+08:00"
fixes: []

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"

file_mapping:
  local_path: "README.md"
  github_path: "github-skill-organizer/README.md"
---

# github-skill-organizer

> 當前版本：1.0.13
> 核心變更：v1.0.13 統一 frontmatter 格式，新增 fixes 欄位支持，skill_issue_reporter.py 改為調用 github-restful-api-connector 統一接口。

---

## 功能

| 功能 | 說明 | 狀態 |
|------|------|------|
| 批量同步上傳 | 本地技能目錄 → GitHub 倉庫子目錄 | ✅ |
| 自動讀取倉庫 | 從 SKILL.md frontmatter 讀取 github_repository | ✅ |
| 自動創建倉庫 | 不存在時自動創建（auto_init=False） | ✅ |
| 衝突檢測 | 比較本地與遠程文件 SHA，避免覆蓋 | ✅ |
| 安全克隆 | Token 不進入命令行，支持 credential helper | ✅ |
| 技能名稱自動檢測 | 從 SKILL.md 讀取 name 欄位 | ✅ |
| 子目錄過濾 | compare_skill 只比對該技能子目錄 | ✅ v1.0.11 |
| 文件排除 | 自動排除 .backups、__pycache__、LICENSE | ✅ v1.0.11 |
| CHANGELOG 同步 | 檢查並同步 CHANGELOG.md frontmatter | ✅ v1.0.11 |
| 標準 Issue 報告 | skill_issue_reporter.py 強制格式輸出 | ✅ v1.0.12 |
| **fixes 欄位支持** | **自動讀取文件 frontmatter fixes 生成 Fixes #N commit** | **✅ v1.0.13** |

---

## 使用方法

### 1. 配置環境變數

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
export GITHUB_OWNER="nervlin4444"
```

### 2. 同步技能到 GitHub

```bash
python scripts/github_repo_sync.py \
  --local-dir ~/.workbuddy/skills/my-skill \
  --repo-name ai.skills.incubation
```

### 3. 克隆倉庫到本地

```bash
python scripts/github_repo_sync.py \
  --clone \
  --repo-name ai.skills.incubation \
  --clone-method credential
```

### 4. 查看同步狀態

```bash
# 比較本地與遠程差異
python scripts/sync_engine.py compare --skill-dir ~/.workbuddy/skills/my-skill
```

### 5. Issue 報告（v1.0.12 新增）

當發現同步問題或技能缺陷需要上報時，使用標準 Issue 報告器：

```bash
# 交互式生成 Issue
python scripts/skill_issue_reporter.py \
  --skill-dir ~/.workbuddy/skills/my-skill \
  --interactive \
  --output-dir ./improve/issues

# 程序化生成（Agent 推薦）
cat issue_input.json | python scripts/skill_issue_reporter.py \
  --skill-dir ~/.workbuddy/skills/my-skill \
  --from-stdin
```

**配套文件**：
- `references/CONTRIBUTING.md` — 標準 Issue 報告格式規範（結構化模板 + JSON）
- `scripts/skill_issue_reporter.py` — Issue 報告生成器（強制格式、自動分類、字數驗證）

**分類標準**：
| 分類 | 說明 | 處理方式 |
|------|------|----------|
| [FRAMEWORK] | 架構決策問題 | 上報主人 |
| [RUNTIME] | 運行時邏輯錯誤 | Agent 自行修復 |
| [AGENT-BUG] | Agent 違反規範 | Agent 自行修復，記錄日誌 |

---

## fixes 欄位說明（v1.0.13 新增）

所有技能文件的 frontmatter 必須包含 `fixes` 欄位：

```yaml
fixes: []        # 無關聯 Issue（新增/優化/文檔）
fixes: [4]       # 修復 Issue #4
fixes: [4, 5]    # 一次修復多個 Issue
```

上傳腳本會自動掃描所有文件的 fixes，合併去重後在 commit message 中附加 `Fixes #N`，GitHub 自動關閉對應 Issue。

---

## 版本記錄

| 版本 | 日期 | 變更 | 作者 | 驗證 |
|------|------|------|------|------|
| 1.0.13 | 2026-05-23 | 統一 frontmatter 格式（fixes 欄位、移除 {baseDir}、單一 file_mapping）；skill_issue_reporter.py 改為調用 github-restful-api-connector 統一接口 | Kevin Lin | ✅ |
| 1.0.12 | 2026-05-22 | 新增 skill_issue_reporter.py（標準 Issue 報告器）和 CONTRIBUTING.md（Issue 格式規範），從 agent-skill-improving 遷移至此 | Kevin Lin | ✅ |
| 1.0.11 | 2026-05-22 | 新增 compare_skill 子目錄過濾、local_only 判定、強制 CLI 上傳、skill_dir_name 修正、expanduser 路徑展開、_is_excluded_path 過濾、CHANGELOG 同步、LICENSE 排除 | Kevin Lin | ✅ |
| 1.0.10 | 2026-05-21 | 修復 local_dir 指向 skills 父目錄導致上傳所有技能 bug | Kevin Lin | ✅ |
| 1.0.9 | 2026-05-21 | 緊急修復 local_dir 計算錯誤 | Kevin Lin | ✅ |
| 1.0.8 | 2026-05-21 | 新增 CHANGELOG.md CI 後處理、sync_changelog() | Kevin Lin | ✅ |
| 1.0.7 | 2026-05-21 | 修復 upload_skill 循環驗證錯誤 | Kevin Lin | ✅ |
| 1.0.6 | 2026-05-21 | 修復 upload_skill 重複讀取 frontmatter | Kevin Lin | ✅ |
| 1.0.5 | 2026-05-21 | 修復 compare_skill 路徑前綴未對齊、action 判定遺漏 local_only | Kevin Lin | ✅ |
| 1.0.4 | 2026-05-21 | 初始版本，基礎同步功能 | Kevin Lin | ✅ |

---

## 配套文件

| 文件 | 說明 |
|------|------|
| scripts/github_repo_sync.py | 批量同步上傳腳本（github-restful-api-connector 技能） |
| scripts/sync_engine.py | 核心同步引擎（compare/upload/sync） |
| scripts/skill_issue_reporter.py | 標準 Issue 報告生成器（v1.0.12 新增，v1.0.13 改為調用統一接口） |
| references/CONTRIBUTING.md | 標準 Issue 報告格式規範（v1.0.12 新增） |
| .github/workflows/release.yml | semantic-release 配置 |
| .releaserc.json | 版本發布規則 |
