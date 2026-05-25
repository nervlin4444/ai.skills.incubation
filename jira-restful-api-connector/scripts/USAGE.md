---
title: "Jira RESTful API Connector — Usage Guide"
name: "jira-restful-api-connector"
description: "Human-readable usage tutorial. How to configure .env and use modules F-001~F-005."
version: "v0.1.3"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T22:05:00+08:00"
fixes: [26, 27, 28, 31]
auth_config:
  provider: jira
  auth_method: basic_or_bearer
  token_env_var: JIRA_API_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/scripts/USAGE.md"
  github_path: "jira-restful-api-connector/scripts/USAGE.md"
---
# Jira RESTful API Connector — Usage Guide

## 1. Environment Setup

### 1.1 Create .env File

Create `.env` in skill root.

**IMPORTANT**: Jira Cloud and Jira Server/DC use DIFFERENT authentication values.

#### Option A: Jira Cloud (xxx.atlassian.net)

    JIRA_URL=https://your-domain.atlassian.net
    JIRA_USERNAME=your.email@example.com
    JIRA_API_TOKEN=your_cloud_api_token_here

Get API Token from: https://id.atlassian.net/manage-profile/security/api-tokens

#### Option B: Jira Server / Data Center (self-hosted, e.g. IP:8080)

    JIRA_URL=http://your-server:8080
    JIRA_USERNAME=your_jira_login_username
    JIRA_API_TOKEN=your_jira_login_password

**WARNING**: Server/DC does NOT have "API Tokens". The `JIRA_API_TOKEN` field must contain your **login PASSWORD** (or a Personal Access Token if your admin enabled PAT). Do NOT put a Cloud API Token here.

### 1.2 Copy Template

    cp .env.example .env

Edit `.env` with actual values.

## 2. Module Overview (F-001 ~ F-005)

| Code | Script | Responsibility |
|------|--------|---------------|
| F-001 | `jira_restful_core.py` | JiraClient init, auth, HTTP requests, error retry |
| F-002 | `jira_query_basic.py` | Basic JQL: search / get / changelog |
| F-003 | `jira_query_advanced.py` | Advanced queries: recursive descendants, milestone queries, cache build |
| F-004 | `jira_field_parser.py` | Field parsing: assignee / status / type / date |
| F-005 | `jira_datetime_utils.py` | Datetime normalization, stale days calculation |

## 3. Basic Usage Examples

### 3.1 Initialize Connection

    from jira_restful_core import JiraClient
    client = JiraClient()

### 3.2 Basic Query

    from jira_query_basic import fetch_issues_by_jql
    issues = fetch_issues_by_jql(client, 'project = WIL AND status = "In Progress"')

### 3.3 Advanced Query

    from jira_query_advanced import fetch_epic_issues
    all_issues = fetch_epic_issues(client, "WIL-10")

### 3.4 Field Parsing

    from jira_field_parser import get_assignee_name, get_status_name
    assignee = get_assignee_name(issue)
    status = get_status_name(issue)

### 3.5 Datetime Utilities

    from jira_datetime_utils import days_since_updated
    days = days_since_updated(issue["fields"]["updated"])

## 4. Error Handling

| HTTP Status | Behavior |
|-------------|----------|
| 401 | Stop immediately, check token. If Server/DC, verify JIRA_API_TOKEN is your PASSWORD. |
| 403 | Exponential backoff retry (max 3). If persistent, check auth per Section 1.1. |
| 404 | Stop immediately, issue does not exist |
| 422 | Stop immediately, JQL syntax error |
| 5xx | Linear backoff retry (max 5) |

## 5. Directory Structure

    jira-restful-api-connector/
    ├── .env
    ├── .env.example
    ├── config/
    │   └── config.json
    ├── scripts/
    │   ├── jira_restful_core.py
    │   ├── jira_query_basic.py
    │   ├── jira_query_advanced.py
    │   ├── jira_field_parser.py
    │   └── jira_datetime_utils.py
    └── references/
        ├── API.SCOPE.md
        └── MAPPING.md
