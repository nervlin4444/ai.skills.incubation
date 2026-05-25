---
title: "Jira RESTful API Connector — Usage Guide"
name: "jira-restful-api-connector"
description: "Human-readable usage tutorial. How to configure .env and use modules F-001~F-005."
version: "v0.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T00:52:00+08:00"
fixes: []
auth_config:
  provider: jira
  auth_method: basic_or_bearer
  token_env_var: JIRA_API_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/scripts/USAGE.md"
  github_path: "jira-restful-api-connector/scripts/USAGE.md"
---
# Jira RESTful API Connector — 使用手冊

## 1. 環境準備

### 1.1 建立 .env 檔案

在技能根目錄建立 `.env` 檔案：

    JIRA_URL=https://your-jira-instance.atlassian.net
    JIRA_USERNAME=your.email@example.com
    JIRA_API_TOKEN=your_api_token_here

若使用 Basic Auth，必須提供 `JIRA_USERNAME` + `JIRA_API_TOKEN`。
若使用 Bearer Token，只需 `JIRA_API_TOKEN`（或 `JIRA_PAT`）。

### 1.2 複製模板

    cp .env.example .env

編輯 `.env` 填入實際數值。

## 2. 功能模組一覽 (F-001 ~ F-005)

| 代號 | 腳本 | 職責 |
|------|------|------|
| F-001 | `jira.restful.core.py` | JiraClient 初始化、認證、HTTP 請求、錯誤重試 |
| F-002 | `jira.query.basic.py` | 基礎 JQL：search / get / changelog |
| F-003 | `jira.query.advanced.py` | 高級查詢：遞歸獲取子孫、里程碑查詢、緩存構建 |
| F-004 | `jira.field.parser.py` | 字段解析：assignee / status / type / date |
| F-005 | `jira.datetime.utils.py` | 日期正規化、停滯天數計算 |

## 3. 基本使用範例

### 3.1 初始化連接

    from jira.restful.core import JiraClient
    client = JiraClient()

### 3.2 基礎查詢

    from jira.query.basic import fetch_issues_by_jql
    issues = fetch_issues_by_jql(client, 'project = WIL AND status = "In Progress"')

### 3.3 高級查詢

    from jira.query.advanced import fetch_epic_issues
    all_issues = fetch_epic_issues(client, "WIL-10")

### 3.4 字段解析

    from jira.field.parser import get_assignee_name, get_status_name
    assignee = get_assignee_name(issue)
    status = get_status_name(issue)

### 3.5 日期工具

    from jira.datetime.utils import days_since_updated
    days = days_since_updated(issue["fields"]["updated"])

## 4. 錯誤處理

| HTTP 狀態 | 行為 |
|-----------|------|
| 401 | 立即停止，檢查 Token |
| 403 | 指數退避重試 (最多 3 次) |
| 404 | 立即停止，Issue 不存在 |
| 422 | 立即停止，JQL 語法錯誤 |
| 5xx | 線性退避重試 (最多 5 次) |

## 5. 目錄結構

    jira-restful-api-connector/
    ├── .env
    ├── .env.example
    ├── config/
    │   └── config.json
    ├── scripts/
    │   ├── jira.restful.core.py
    │   ├── jira.query.basic.py
    │   ├── jira.query.advanced.py
    │   ├── jira.field.parser.py
    │   └── jira.datetime.utils.py
    └── references/
        ├── API.SCOPE.md
        └── MAPPING.md
