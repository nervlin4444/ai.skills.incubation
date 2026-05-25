---
title: "jira-restful-api-connector — README.md"
name: "jira-restful-api-connector"
description: "Human-readable skill guide. Generic Jira REST API data connector with zero business logic. Reusable by any Jira-related skill."
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
  local_path: "{baseDir}/README.md"
  github_path: "jira-restful-api-connector/README.md"
---
# jira-restful-api-connector — Skill Guide

## 1. Skill Positioning

Generic Jira REST API data connector. Provides Jira instance connection, JQL queries, issue field parsing, datetime handling, and other foundational capabilities.

**Design Principle: Zero Business Logic**. No concept of milestone, mockup round, or assignee statistics. Only responsible for "connecting" and "querying", returning raw data.

**Separation Background**: This skill was split from jira-project-report v1.0.1 core library (jira_report_core.py), making generic API capabilities an independent reusable component.

## 2. Directory Structure and File Naming

### 2.1 Standard Directory Structure

    skills/jira-restful-api-connector/
    ├── SKILL.md                          <- LLM execution guide (not for human reading)
    ├── README.md                         <- This file (human guide)
    ├── .env                               <- Jira credentials (user-managed, not in repo)
    ├── .env.example                       <- Environment variable template (copy and fill)
    ├── config/
    │   └── config.json                    <- Skill-level config (timeout, retry strategy)
    ├── scripts/
    │   ├── jira_restful_core.py           <- F-001: Unified HTTP client
    │   ├── jira_query_basic.py            <- F-002: Basic JQL queries
    │   ├── jira_query_advanced.py         <- F-003: Advanced queries
    │   ├── jira_field_parser.py           <- F-004: Field parser
    │   └── jira_datetime_utils.py         <- F-005: Datetime utilities
    └── references/
        ├── API.SCOPE.md                  <- Jira REST API scope
        └── MAPPING.md                    <- Status / field mapping rules

### 2.2 File Naming Rules

Non-executable files (.md, .json) use dot-separated format:
    Correct: API.SCOPE.md, MAPPING.md, config.json

Python scripts (.py) use underscore-separated format:
    Correct: jira_restful_core.py, jira_query_basic.py
    Wrong:  jira.restful.core.py, jira.query.basic.py

Reason: Python import mechanism parses dots as package paths, causing import failures.

## 3. Module Division

| Module File | Type | Purpose |
|-------------|------|---------|
| jira_restful_core.py | Shared library | JiraClient class, load_env(), auto-auth detection, HTTP error retry |
| jira_query_basic.py | Shared library | Basic JQL query wrappers (search / get / changelog) |
| jira_query_advanced.py | Shared library | Advanced queries (recursive descendants, bulk keyword search, cache build) |
| jira_field_parser.py | Shared library | Safe issue field parsing (assignee, status, duedate, etc.) |
| jira_datetime_utils.py | Shared library | Jira datetime format handling (+0800 -> +08:00, day calculation) |

## 4. Authentication

### 4.1 .env Environment Variables

Create .env in skill root:

    JIRA_URL=http://your-jira-instance.com:8080
    JIRA_USERNAME=your_username
    JIRA_API_TOKEN=your_api_token

Or (backward compatible old var names):

    JIRA_URL=http://your-jira-instance.com:8080
    JIRA_USER=your_username
    JIRA_PAT=your_api_token

### 4.2 Auto Auth Detection

JiraClient auto-detects authentication method:

| Condition | Auth Method | Description |
|-----------|-------------|-------------|
| username + token both present | Basic Auth | Base64 encoded (username:token) |
| token only present | Bearer Token | Use token directly |
| Neither present | Error stop | Single-line error |

### 4.3 Security Reminder

.env file must be added to .gitignore. Do NOT commit to version control.

## 5. Config File Format

### 5.1 config/config.json

    {
      "timeout": 60,
      "retry_max": 3,
      "api_version": 2,
      "rate_limit": {
        "backoff_strategy": "exponential",
        "backoff_max": 3
      }
    }

### 5.2 .env.example (Template)

    JIRA_URL=http://your-jira-instance.com:8080
    JIRA_USERNAME=your_username
    JIRA_API_TOKEN=your_api_token

## 6. Error Handling

### 6.1 Error Tiers

| Error Type | HTTP Code | Action |
|------------|-----------|--------|
| Auth failure | 401 | Stop, report PAT/Token invalid |
| Rate limit | 403 | Exponential backoff retry (max 3) |
| Not found | 404 | Stop, report issue/resource missing |
| Bad param | 422 | Stop, report JQL syntax error |
| Server error | 5xx | Linear backoff retry (max 5) |

### 6.2 Error Format

    ERROR: [brief desc] | [relevant params] | Stop.
    WARN: [brief desc] | [relevant params] | Continue.

## 7. Collaboration with Consumer Skills

### 7.1 wilson-project-report (Report Generation Layer)

wilson-project-report as the first consumer of this skill, references it via:

    import sys
    from pathlib import Path
    SKILL_ROOT = Path(__file__).parent.parent
    sys.path.insert(0, str(SKILL_ROOT / "../jira-restful-api-connector/scripts"))
    import jira_restful_core as jira_core

Or declare dependency via skill package manager (WorkBuddy / OpenClaw).

### 7.2 Responsibility Boundary

| Layer | Responsibility | Config Location |
|-------|----------------|-----------------|
| jira-restful-api-connector | Connect Jira API, execute JQL, parse fields, manage cache | .env + config/config.json |
| wilson-project-report | Report generation, HTML rendering, history records, business stats | config/config.json + report.*.py top-level constants |

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| v0.1.0 | 2026-05-21 | Initial version. Split from jira-project-report v1.0.1 core. F-001~F-005, path rigidity, tiered error handling |
| v0.1.1 | 2026-05-25 | Fix: Python scripts renamed to underscore format per naming rules. Fixed broken import statements. All .py content verified ASCII-only. |
| v0.1.2 | 2026-05-25 | Fix: Added missing high-level methods search_issues(), get_issue(), get_changelog() to JiraClient. Enhanced Section 4.1 docs to clarify two-layer architecture and F-002 dependency. Fixes #26. |

## 9. Related Skills

| Skill | Relationship |
|-------|-------------|
| wilson-project-report | Consumer (report generation layer) |
| agent-skill-improving | Defect discovery and correction flow |
| github-restful-api-connector | Reference architecture (LAYER architecture, function codes, error tiers) |

---

*This file is a human-readable guide. LLM execution guide see SKILL.md.*
*Generated: 2026-05-25*
