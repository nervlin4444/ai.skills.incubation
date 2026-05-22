---
title: "GitHub RESTful API Connector - CLI Usage Reference"
name: "github-restful-api-connector"
description: "腳本 CLI 用法教程。供人類和 Agent 參考的命令範例與常見問題。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T15:36:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/scripts/USAGE.md"
  github_path: "github-restful-api-connector/scripts/USAGE.md"
---

# github-restful-api-connector — CLI 用法教程

版本：v0.3.0
更新時間：2026-05-17 20:46:00

## 快速開始

### 1. 配置 .env

在技能包根目錄創建 `.env`：

    GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    GITHUB_OWNER=nervlin4444
    GITHUB_REPO=ai.skills.devops

### 2. 測試 PAT（必做）

    python scripts/github_repo_verify.py --test-pat

預期輸出：

    [Authentication] Auth success: YES
    [Repository Check] Repo exists: NO
    RESULT: PAT valid, repo missing — sync will auto-create repo.

### 3. 同步上傳

    python scripts/github_repo_sync.py       --repo-name ai.skills.devops       --local-dir .

文件會自動上傳到 `ai.skills.devops/github-restful-api-connector/` 子目錄。

### 4. 雙向驗證

    python scripts/github_repo_verify.py       --repo-name ai.skills.devops       --local-dir .       --direction both

## 完整命令參考

### github_restful_core.py（F-001）

    # 查看版本
    python scripts/github_restful_core.py --version

    # 測試連通性
    python scripts/github_restful_core.py --test-connection

### github_repo_sync.py（F-005）

    # 基本同步（自動檢測技能名稱 → 上傳到子目錄）
    python scripts/github_repo_sync.py --repo-name ai.skills.devops --local-dir .

    # 預覽模式
    python scripts/github_repo_sync.py --repo-name ai.skills.devops --local-dir . --dry-run

    # 強制覆蓋
    python scripts/github_repo_sync.py --repo-name ai.skills.devops --local-dir . --force

    # 手動指定路徑前綴（覆蓋自動檢測）
    python scripts/github_repo_sync.py --repo-name ai.skills.devops --local-dir . --repo-base-path my-custom-path

    # 上傳到根目錄（慎用，需主人授權）
    python scripts/github_repo_sync.py --repo-name ai.skills.devops --local-dir . --no-auto-name

    # 安全克隆倉庫
    python scripts/github_repo_sync.py --repo-name ai.skills.devops --local-dir . --clone

    # 使用 credential helper 克隆（Token 不進入命令行）
    python scripts/github_repo_sync.py --repo-name ai.skills.devops --local-dir . --clone --clone-method credential

### github_repo_verify.py（F-006）

    # PAT 診斷（獨立，不需要 repo-name/local-dir）
    python scripts/github_repo_verify.py --test-pat

    # PAT 診斷 JSON 輸出
    python scripts/github_repo_verify.py --test-pat --json

    # 雙向完整驗證
    python scripts/github_repo_verify.py --repo-name ai.skills.devops --local-dir . --direction both

    # 只驗證本地 → 倉庫
    python scripts/github_repo_verify.py --repo-name ai.skills.devops --local-dir . --direction local-to-repo

    # 只驗證倉庫 → 本地
    python scripts/github_repo_verify.py --repo-name ai.skills.devops --local-dir . --direction repo-to-local

    # JSON 輸出
    python scripts/github_repo_verify.py --repo-name ai.skills.devops --local-dir . --direction both --json

### github_repo_pull.py（F-007）

    # 從倉庫拉取技能目錄到本地
    python scripts/github_repo_pull.py       --repo-name ai.skills.devops       --repo-path github-restful-api-connector       --local-dir ~/.workbuddy/skills/github-restful-api-connector

    # 預覽模式
    python scripts/github_repo_pull.py       --repo-name ai.skills.devops       --repo-path github-restful-api-connector       --local-dir ./test       --dry-run

    # 強制覆蓋本地較新文件
    python scripts/github_repo_pull.py       --repo-name ai.skills.devops       --repo-path github-restful-api-connector       --local-dir ./test       --force

## 常見問題

### Q1: sync 上傳後文件在根目錄，不在子目錄？

檢查 sync.py 版本：

    python scripts/github_repo_sync.py --version

必須顯示 v0.3.0+。若為舊版本，更新後重新上傳。

### Q2: verify --test-pat 顯示 Auth success: NO？

1. 確認 `.env` 中 GITHUB_TOKEN 值正確（ghp_ 開頭，40 字符）
2. 確認 Token 有 `repo` scope
3. 確認使用的是最新 core.py（v0.1.1+，修復了 setdefault bug）

### Q3: sync 時顯示 "SKILL.md not found"？

必須在 `--local-dir` 指定的目錄中包含 SKILL.md，且 frontmatter 中有 `name: "技能名稱"`。

### Q4: 如何同時管理多個技能？

大貨倉 `ai.skills.devops` 的結構：

    ai.skills.devops/
    ├── github-restful-api-connector/
    │   ├── SKILL.md
    │   ├── scripts/
    │   └── ...
    ├── jira-project-report/
    │   ├── SKILL.md
    │   ├── scripts/
    │   └── ...
    └── another-skill/
        ├── SKILL.md
        └── ...

每個技能獨立執行 sync，自動上傳到各自的子目錄。

### Q5: 如何更新已上傳的文件？

直接修改本地文件後重新執行 sync。sync.py 會比對 sha，只上傳變更的文件。

## 排除規則

以下文件/目錄自動跳過，不會上傳：

    .git, __pycache__, .env, *.pyc, .DS_Store,
    temp, tmp, cache, logs, .gitkeep, .env.template
