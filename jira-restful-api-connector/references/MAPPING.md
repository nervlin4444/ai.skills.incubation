---
title: "Jira Status & Field Mapping"
name: "jira-restful-api-connector"
description: "Jira status name and internal field mapping rules."
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
  local_path: "{baseDir}/references/MAPPING.md"
  github_path: "jira-restful-api-connector/references/MAPPING.md"
---
# Jira Status & Field Mapping

## 狀態映射 (Status Name -> Internal Key)

| 顯示名稱 | 內部 Key | 用途 |
|----------|----------|------|
| Done | done | 已完成 |
| In Progress | in_progress | 進行中 |
| Ready for QC | ready_for_qc | 待測試 |
| To Do | to_do | 待開始 |
| Return | returned | 退回 |
| On Hold | on_hold | 暫停 |
| 已完成 | done | 中文映射 |
| 進行中 | in_progress | 中文映射 |
| 待測試 | ready_for_qc | 中文映射 |
| 待開始 | to_do | 中文映射 |
| 退回 | returned | 中文映射 |
| 暫停 | on_hold | 中文映射 |

## 字段路徑對照

| 業務含義 | 字段路徑 | 類型 |
|----------|----------|------|
| Issue Key | key | string |
| Summary | fields.summary | string |
| Status | fields.status.name | string |
| Assignee | fields.assignee.displayName | string |
| Issue Type | fields.issuetype.name | string |
| Due Date | fields.duedate | string (YYYY-MM-DD) |
| Updated | fields.updated | string (ISO 8601) |
| Priority | fields.priority.name | string |

## JQL 語法參考

| 操作 | 語法 | 範例 |
|------|------|------|
| 等於 | = | project = WIL |
| 不等於 | != | status != "Done" |
| 包含 | ~ | summary ~ "Void Sales" |
| 鏈接 | in linkedIssues | issue in linkedIssues("WIL-10") |
| OR | OR | status = "Done" OR status = "Return" |
| AND | AND | project = WIL AND status = "Done" |
