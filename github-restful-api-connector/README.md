---
title: "GitHub RESTful API Connector"
name: "github-restful-api-connector"
description: "人類閱讀版。連接 GitHub RESTful API，將本地技能包自動同步到 GitHub 倉庫的同名子目錄。支援 PAT 診斷、雙向驗證、衝突檢測與安全克隆。v0.3.2 修復 Issue #4 計數異常，統一 frontmatter 格式。"
version: "0.3.2"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T11:28:00+08:00"
fixes: [4]

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"

file_mapping:
  local_path: "README.md"
  github_path: "github-restful-api-connector/README.md"
---

# GitHub RESTful API Connector

版本：v0.3.2
更新時間：2026-05-23 11:28:00
核心修復：Issue #4 計數異常（upload_file 返回明確狀態字典），統一 frontmatter 格式（fixes 欄位、移除 {baseDir}）。

## 這是什麼？

這個技能包讓 AI Agent 能夠將本地的技能目錄（如 `github-restful-api-connector/`）自動同步到 GitHub 倉庫的**同名子目錄**下。

設計目標是「一個大貨倉，多個技能」——所有技能放在同一個倉庫 `ai.skills.incubation` 中，各自獨立子目錄，互不干擾。

## 倉庫結構範例

    nervlin4444/ai.skills.incubation/ ← 大貨倉（一個 GitHub repo）
    ├── github-restful-api-connector/ ← 技能 A 子目錄
    │   ├── SKILL.md
    │   ├── README.md
    │   ├── scripts/
    │   │   ├── github_restful_core.py
    │   │   ├── github_repo_sync.py
    │   │   ├── github_repo_verify.py
    │   │   ├── github_repo_pull.py
    │   │   └── USAGE.md
    │   └── references/
    │       ├── API.SCOPE.md
    │       └── MAPPING.md
    ├── jira-project-report/ ← 技能 B 子目錄（日後新增）
    │   ├── SKILL.md
    │   └── ...
    └── another-skill/ ← 技能 C 子目錄（日後新增）
        ├── SKILL.md
        └── ...

## 核心特性

| 特性 | 說明 |
|------|------|
| **強制子目錄** | 所有文件自動上傳到 `{skill_name}/` 子目錄，禁止根目錄散放 |
| **自動檢測技能名稱** | 從本地 `SKILL.md` 的 frontmatter `name` 欄位讀取 |
| **PAT 診斷** | `--test-pat` 獨立診斷 Token 有效性，區分「Token 無效」vs「倉庫不存在」 |
| **倉庫自動創建** | 目標倉庫不存在時自動創建（private，無 init.md 垃圾文件） |
| **衝突檢測** | 比對 Git blob sha，倉庫文件較新時警告，需 `--force` 才覆蓋 |
| **雙向驗證** | 本地 → 倉庫、倉庫 → 本地，兩方向比對確保同步完整 |
| **安全克隆** | Token 通過環境變數傳遞，不暴露於 Shell 歷史 |
| **懶加載設計** | `load_env()` 和 `get_session()` 首次調用時才執行，避免模組導入時崩潰 |
| **fixes 欄位支持** | 文件 frontmatter 中 `fixes: [N]` 自動生成 `Fixes #N` commit message |

## 快速開始

### 1. 配置 .env

在技能包根目錄創建 `.env`：

    GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    GITHUB_OWNER=nervlin4444
    GITHUB_REPO=ai.skills.incubation

Token 需要 `repo` scope。

### 2. 測試 PAT（必做）

    cd ~/.workbuddy/skills/github-restful-api-connector
    python scripts/github_repo_verify.py --test-pat

預期輸出：

    [Authentication] Auth success: YES
    [Repository Check] Repo exists: NO
    RESULT: PAT valid, repo missing — sync will auto-create repo.

若 `Auth success: NO`，檢查 Token 值和 `repo` scope。

### 3. 同步上傳

    python scripts/github_repo_sync.py --repo-name ai.skills.incubation --local-dir .

文件會自動上傳到 `ai.skills.incubation/github-restful-api-connector/` 子目錄。

### 4. 雙向驗證

    python scripts/github_repo_verify.py --repo-name ai.skills.incubation --local-dir . --direction both

## 腳本清單

| 腳本 | 版本 | 職責 |
|------|------|------|
| `github_restful_core.py` | 0.1.2 | 統一 HTTP 客戶端、認證、分頁、速率限制、錯誤重試 |
| `github_repo_sync.py` | 0.3.2 | 批量上傳（本地 → 倉庫）。強制子目錄、自動創建倉庫、衝突檢測、fixes 欄位支持 |
| `github_repo_verify.py` | 0.2.0 | 雙向驗證 + PAT 診斷。`--test-pat` 獨立診斷 Token |
| `github_repo_pull.py` | 0.1.0 | 下載同步（倉庫 → 本地）。拉取更新、初始化本地目錄 |

## 常見問題

### Q: 為什麼文件必須放在子目錄？

大貨倉 `ai.skills.incubation` 容納多個技能。如果所有文件放在根目錄，不同技能的 `SKILL.md`、`scripts/` 會互相覆蓋。子目錄隔離確保每個技能獨立。

### Q: 如何新增第二個技能？

1. 本地準備新技能目錄（如 `jira-project-report/`），內含 `SKILL.md`（frontmatter 有 `name: "jira-project-report"`）
2. 執行：

    python scripts/github_repo_sync.py --repo-name ai.skills.incubation --local-dir ./jira-project-report

3. 自動上傳到 `ai.skills.incubation/jira-project-report/`

### Q: 更新已上傳的文件？

修改本地文件後重新執行 sync。sync.py 會比對 sha，只上傳變更的文件。

### Q: 如何確認 Agent 使用的是最新版本？

檢查腳本內的時間戳：

    grep "生成日期" scripts/github_repo_sync.py
    grep "updated_at" SKILL.md

### Q: 排除哪些文件？

自動跳過：`.git`, `__pycache__`, `.env`, `*.pyc`, `.DS_Store`, `temp`, `tmp`, `cache`, `logs`, `.gitkeep`, `.env.template`, `.backups`, `.backup`

## 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 0.3.2 | 2026-05-23 | 修復 Issue #4 計數異常（upload_file 返回明確狀態字典）；統一 frontmatter 格式（fixes 欄位、移除 {baseDir}、單一 file_mapping） |
| 0.3.1 | 2026-05-20 | 加入 .backups / .backup 排除；新增 --test-conventional-commit 參數 |
| 0.3.0 | 2026-05-17 | 強制子目錄上傳、自動檢測技能名稱、PAT 診斷、setdefault bug 修復 |
| 0.2.0 | 2026-05-17 | 新增 F-007 下載同步、拆分驗證腳本、安全克隆 |
| 0.1.0 | 2026-05-16 | 初始框架：core / agent / task / session / sync |

## 相關文件

| 文件 | 位置 | 用途 |
|------|------|------|
| `SKILL.md` | 根目錄 | LLM 執行指令版（給 Agent 閱讀） |
| `README.md` | 根目錄 | 人類閱讀版（本文件） |
| `USAGE.md` | `scripts/` | CLI 命令參考與常見問題 |
| `API.SCOPE.md` | `references/` | GitHub API 權限範圍定義 |
| `MAPPING.md` | `references/` | 看板欄位映射規則 |
