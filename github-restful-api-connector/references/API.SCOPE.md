---
title: "API Permission Scope"
name: "github-restful-api-connector"
description: "API 權限與端點定義。鎖定本技能所需最小權限原則。"
version: "0.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/references/API.SCOPE.md"
    github_path: "/github-restful-api-connector/references/API.SCOPE.md"
---

# API.SCOPE.md — 權限與端點定義

## 1. 認證方式

### 1.1 Personal Access Token (Classic)

| 範圍 | 用途 | 是否必要 |
|------|------|----------|
| **repo** | **讀取倉庫內容、創建 Issue、讀取 Sessions** | **是（必要）** |
| read:project | 讀取 Projects v2 數據 | 是 |
| write:project | 創建/更新/刪除 Project 卡片與欄位 | 是 |
| read:org | 讀取組織級 Project（若 Owner 為組織） | 條件必要 |

### 1.2 Fine-grained Personal Access Token（推薦）

| 權限類別 | 權限名稱 | 存取級別 | 用途 |
|----------|----------|----------|------|
| Repository permissions | Issues | Read and write | Sessions 追蹤需讀寫 Issue |
| Repository permissions | Contents | Read | 讀取倉庫文件（如 .env） |
| Account permissions | Projects | Read and write | Project 看板全部操作 |
| Organization permissions | Projects | Read and write | 組織級 Project 操作 |

## 2. REST API 端點（已鎖定）

| 端點 | 方法 | 用途 | 對應功能 |
|------|------|------|----------|
| /user | GET | 驗證 Token 有效性 | F-001 |
| /repos/{owner}/{repo}/issues | GET/POST | Issue 列表與創建 | F-004 |
| /repos/{owner}/{repo}/issues/{issue_number} | GET/PATCH | Issue 更新 | F-004 |
| /projects/{project_id} | GET | Project 元數據 | F-002 |

## 3. GraphQL API 查詢（Projects v2 專用）

GitHub Projects v2 主要透過 GraphQL 操作。以下為核心查詢與變更：

### 3.1 查詢 Project 欄位與卡片

    query($owner: String!, $number: Int!) {
      userOrOrganization(login: $owner) {
        projectV2(number: $number) {
          id
          fields(first: 20) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name
                options { id name }
              }
            }
          }
          items(first: 100) {
            nodes {
              id
              content {
                ... on Issue { title number }
              }
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue { name }
                }
              }
            }
          }
        }
      }
    }

### 3.2 更新卡片狀態欄位

    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId
        itemId: $itemId
        fieldId: $fieldId
        value: { singleSelectOptionId: $optionId }
      }) {
        projectV2Item { id }
      }
    }

### 3.3 創建 Draft Issue 卡片

    mutation($projectId: ID!, $title: String!, $body: String) {
      addProjectV2DraftIssue(input: {
        projectId: $projectId
        title: $title
        body: $body
      }) {
        projectItem { id }
      }
    }

## 4. Agent Sessions API（2026 原生功能）

| 端點 | 方法 | 用途 | 對應功能 |
|------|------|------|----------|
| /repos/{owner}/{repo}/issues/{issue_number}/agent-sessions | GET | 列出 Issue 的 Sessions | F-004 |
| /repos/{owner}/{repo}/issues/{issue_number}/agent-sessions | POST | 創建新 Session | F-004 |
| /repos/{owner}/{repo}/agent-sessions/{session_id} | GET | 讀取 Session 詳情 | F-004 |
| /repos/{owner}/{repo}/agent-sessions/{session_id} | PATCH | 更新 Session 狀態 | F-004 |

注意：Sessions API 目前為 GitHub Copilot Agent 功能的一部分，需組織層級開啟。

## 5. 速率限制

| API 類型 | 限制 | 認證影響 |
|----------|------|----------|
| REST API | 5000 requests/hour | PAT 獨立計算 |
| GraphQL API | 5000 points/hour | 複雜查詢消耗更多 points |
| Search API | 10 requests/minute | 本技能原則上不使用 |

## 6. API 版本標頭

所有請求必須攜帶：

    Accept: application/vnd.github+json
    X-GitHub-Api-Version: 2022-11-28
    Authorization: Bearer {GITHUB_TOKEN}

## 7. 錯誤碼映射

| HTTP 狀態碼 | GraphQL 錯誤 | 含義 | 處理方式 |
|-------------|--------------|------|----------|
| 200 | — | 成功 | 繼續 |
| 401 | — | 認證失敗 | 停止，報錯 Token |
| 403 | RATE_LIMITED | 速率限制 | 指數退避重試 |
| 404 | NOT_FOUND | 資源不存在 | 停止，報錯路徑 |
| 422 | VALIDATION_FAILED | 參數錯誤 | 停止，報錯參數 |
| 500+ | — | 服務器錯誤 | 線性退避重試 |
