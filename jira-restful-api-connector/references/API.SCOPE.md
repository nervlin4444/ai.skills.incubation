---
title: "Jira REST API Scope"
name: "jira-restful-api-connector"
description: "Jira REST API v2 scope definition and error code mapping."
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
  local_path: "{baseDir}/references/API.SCOPE.md"
  github_path: "jira-restful-api-connector/references/API.SCOPE.md"
---
# Jira REST API Scope

## API Version

Fixed to Jira REST API v2.

    Base URL: {JIRA_URL}/rest/api/2

## Authentication Methods

| Method | Condition | Header Format |
|--------|-----------|---------------|
| Basic Auth | username + token both present | Authorization: Basic {Base64(username:token)} |
| Bearer Token | token only present | Authorization: Bearer {token} |

## Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /search | GET | JQL search |
| /issue/{key} | GET | Single issue query |
| /issue/{key}?expand=changelog | GET | Issue changelog |

## Error Code Mapping

| HTTP Code | Meaning | Handling |
|-----------|---------|----------|
| 401 | Unauthorized | Stop, report auth failure |
| 403 | Forbidden / Rate Limited | Exponential backoff retry (max 3) |
| 404 | Not Found | Stop, report resource missing |
| 422 | Validation Failed | Stop, report JQL syntax error |
| 429 | Too Many Requests | Exponential backoff retry (max 3) |
| 500 | Internal Server Error | Linear backoff retry (max 5) |
| 502 | Bad Gateway | Linear backoff retry (max 5) |
| 503 | Service Unavailable | Linear backoff retry (max 5) |
