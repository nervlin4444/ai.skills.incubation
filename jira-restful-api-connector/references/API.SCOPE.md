---
title: "Jira REST API Scope"
name: "jira-restful-api-connector"
description: "Jira REST API v2 scope definition and error code mapping."
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
  local_path: "{baseDir}/references/API.SCOPE.md"
  github_path: "jira-restful-api-connector/references/API.SCOPE.md"
---
# Jira REST API Scope

## API 版本

固定使用 Jira REST API v2。

    Base URL: {JIRA_URL}/rest/api/2

## 認證方式

| 方式 | 條件 | Header 格式 |
|------|------|-------------|
| Basic Auth | username + token 同時存在 | Authorization: Basic {Base64(username:token)} |
| Bearer Token | 僅 token 存在 | Authorization: Bearer {token} |

## 核心端點

| 端點 | 方法 | 用途 |
|------|------|------|
| /search | GET | JQL 搜索 |
| /issue/{key} | GET | 單一 Issue 查詢 |
| /issue/{key}?expand=changelog | GET | Issue Changelog |

## 錯誤碼對照

| HTTP 碼 | 含義 | 處理方式 |
|---------|------|----------|
| 401 | Unauthorized | 停止，報錯認證失敗 |
| 403 | Forbidden / Rate Limited | 指數退避重試 (max 3) |
| 404 | Not Found | 停止，報錯資源不存在 |
| 422 | Validation Failed | 停止，報錯 JQL 語法錯誤 |
| 429 | Too Many Requests | 指數退避重試 (max 3) |
| 500 | Internal Server Error | 線性退避重試 (max 5) |
| 502 | Bad Gateway | 線性退避重試 (max 5) |
| 503 | Service Unavailable | 線性退避重試 (max 5) |
