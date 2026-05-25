---
title: "Jira Status & Field Mapping"
name: "jira-restful-api-connector"
description: "Jira status name and internal field mapping rules."
version: "v0.1.2"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T17:09:00+08:00"
fixes: [26]
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

## Status Mapping (Status Name -> Internal Key)

| Display Name | Internal Key | Purpose |
|--------------|--------------|---------|
| Done | done | Completed |
| In Progress | in_progress | In progress |
| Ready for QC | ready_for_qc | Pending test |
| To Do | to_do | Not started |
| Return | returned | Returned |
| On Hold | on_hold | On hold |
| Completed | done | Chinese mapping |
| In Progress | in_progress | Chinese mapping |
| Pending Test | ready_for_qc | Chinese mapping |
| Not Started | to_do | Chinese mapping |
| Returned | returned | Chinese mapping |
| On Hold | on_hold | Chinese mapping |

## Field Path Reference

| Business Meaning | Field Path | Type |
|------------------|------------|------|
| Issue Key | key | string |
| Summary | fields.summary | string |
| Status | fields.status.name | string |
| Assignee | fields.assignee.displayName | string |
| Issue Type | fields.issuetype.name | string |
| Due Date | fields.duedate | string (YYYY-MM-DD) |
| Updated | fields.updated | string (ISO 8601) |
| Priority | fields.priority.name | string |

## JQL Syntax Reference

| Operation | Syntax | Example |
|-----------|--------|---------|
| Equals | = | project = WIL |
| Not equals | != | status != "Done" |
| Contains | ~ | summary ~ "Void Sales" |
| Linked | in linkedIssues | issue in linkedIssues("WIL-10") |
| OR | OR | status = "Done" OR status = "Return" |
| AND | AND | project = WIL AND status = "Done" |
