---
title: "jira-restful-api-connector — LLM SKILL.md"
name: "jira-restful-api-connector"
description: "LLM execution guide. Zero business logic. Connect and query Jira REST API v2, return raw data only."
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
  local_path: "{baseDir}/SKILL.md"
  github_path: "jira-restful-api-connector/SKILL.md"
---
# jira-restful-api-connector — LLM Execution Guide

## 0. Identity Confirmation

You are appointed as the execution agent for jira-restful-api-connector skill.
Your sole task is to provide Jira REST API connection and query capability per this document.
You are NOT a report generator, business analyst, or decision maker.
You connect, you query, you return raw data.

## 1. Skill Positioning

Generic Jira REST API data connector. Via .env authentication, provides:

    - F-001 jira_restful_core.py: JiraClient + load_env + auto-auth + error retry
    - F-002 jira_query_basic.py: Basic JQL queries (search / get / changelog)
    - F-003 jira_query_advanced.py: Advanced queries (recursive / bulk / cache)
    - F-004 jira_field_parser.py: Safe issue field parser
    - F-005 jira_datetime_utils.py: Jira datetime format utilities

Zero business logic. No concept of milestone, mockup round, or assignee statistics.

## 2. Directory Structure and File Naming

### 2.1 Standard Directory Structure

    skills/jira-restful-api-connector/
    ├── SKILL.md                          <- This file (LLM execution guide)
    ├── README.md                         <- Human-readable guide
    ├── .env                               <- Jira credentials (user-managed, not in repo)
    ├── .env.example                       <- Environment variable template
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

### 2.2 File Naming Mandatory Rules

Non-executable files (.md, .json, .html, .yaml) use dot-separated format:
    Correct: API.SCOPE.md, MAPPING.md, config.json

Python scripts (.py) use underscore-separated format (exemption from dot rule):
    Correct: jira_restful_core.py, jira_query_basic.py
    Wrong:  jira.restful.core.py, jira.query.basic.py

Reason: Python import mechanism parses dots as package paths, causing import failures.

### 2.3 Path Rigidity Rule

When scripts read .env or config, only official paths are allowed:
- ~/.workbuddy/skills/jira-restful-api-connector/.env
- ~/.workbuddy/skills/jira-restful-api-connector/config/config.json
- ~/.openclaw/skills/jira-restful-api-connector/.env
- ~/.openclaw/skills/jira-restful-api-connector/config/config.json

Path not found -> single-line error, stop. No file creation, no guessing, no options.

Error format:
    ERROR: [filename] not found at [path]. Stop.

## 3. Execution Flow

When receiving a Jira query command, execute in this order:

### Step 1 — Environment Check

Check existence of:
    1. .env (skill root or --env-file path)
    2. config/config.json (or --config path)

Any missing -> single-line error, stop.

### Step 2 — Read Configuration

Read .env, extract:
    - JIRA_URL: Jira instance URL
    - JIRA_USERNAME or JIRA_USER: Username
    - JIRA_API_TOKEN or JIRA_PAT: API Token / PAT

Read config/config.json, extract:
    - timeout: HTTP timeout seconds (default 60)
    - retry_max: Max retry count (default 3)
    - api_version: Jira REST API version (default 2)

### Step 3 — Initialize JiraClient

    client = JiraClient(jira_url, jira_pat, jira_user, timeout)

Auth auto-detection:
    - If jira_user + jira_pat present -> Basic Auth (Base64 encoded)
    - If only jira_pat present -> Bearer Token
    - If neither -> error stop

### Step 4 — Execute Query

Call corresponding functions per user command:
    - Basic queries -> jira_query_basic.py
    - Recursive / bulk queries -> jira_query_advanced.py
    - Field parsing -> jira_field_parser.py
    - Date processing -> jira_datetime_utils.py

### Step 5 — Return Results

Return raw JSON / dict / list. No business analysis or formatting.
Do NOT append analysis, suggestions, or formatted output to results.

### Step 6 — Error Handling

On query failure, handle by tier:

| Error Type | HTTP Code | Action | Reporting |
|------------|-----------|--------|-----------|
| Auth failure | 401 | Stop, report invalid PAT/Token | Single-line error |
| Rate limit | 403 | Exponential backoff retry (max 3) | Log |
| Not found | 404 | Stop, report issue/resource missing | Single-line error |
| Bad param | 422 | Stop, report JQL syntax error | Single-line error |
| Server error | 5xx | Linear backoff retry (max 5) | Log |

Error format:
    ERROR: [brief desc] | [relevant params] | Stop.
    WARN: [brief desc] | [relevant params] | Continue.

## 4. Function Codes and Interface Specs

### 4.1 F-001 — jira_restful_core.py

Responsibility: Sole channel for all Jira API calls.

Architecture: JiraClient provides TWO layers of methods:
  - Low-level: _request(), get(), post() — generic HTTP wrappers
  - High-level: search_issues(), get_issue(), get_changelog() — thin wrappers used by F-002~F-005

All high-level methods are MANDATORY and must exist. They contain ZERO business logic;
they only assemble endpoint URLs and delegate to _request().

Mandatory functions (interface LOCK PERMANENT):

    def load_env(env_file: Path = None) -> dict
        Load .env environment variables.
        Support dual var names: JIRA_PAT/JIRA_API_TOKEN, JIRA_USER/JIRA_USERNAME.
        Path not found -> error stop.

    class JiraClient:
        __init__(self, jira_url: str, jira_pat: str, jira_user: str = None, timeout: int = 60)
            Initialize client. jira_user is optional, for Basic Auth.

        _get_auth_header(self) -> str
            Auto-detect auth method:
            - username + pat -> Basic Auth (Base64 encoded)
            - pat only -> Bearer Token

        _request(self, path: str, params: dict = None, method: str = "GET", data: dict = None) -> dict
            Unified HTTP call. Handle pagination, rate limit, error retry.
            Return JSON dict.

        get(self, endpoint: str) -> dict
            Generic GET wrapper. Calls _request(endpoint, "GET").

        post(self, endpoint: str, data: dict) -> dict
            Generic POST wrapper. Calls _request(endpoint, "POST", data).

        search_issues(self, jql: str, fields: str = "*all", max_results: int = 500) -> dict
            JQL search via POST /search. Returns raw Jira API response dict.
            MANDATORY — F-002 fetch_issues_by_jql() depends on this.
            Implementation: assemble payload {jql, fields, maxResults} and call post("/search", payload).

        get_issue(self, issue_key: str, fields: str = "*all", expand: str = None) -> dict
            Single issue query via GET /issue/{key}. Returns issue dict.
            MANDATORY — F-002 fetch_issue_by_key() depends on this.
            Implementation: assemble endpoint URL with query params and call get(endpoint).

        get_changelog(self, issue_key: str) -> dict
            Single issue changelog via GET /issue/{key}?expand=changelog.
            MANDATORY — F-002 fetch_changelog_by_key() depends on this.
            Implementation: call get(f"/issue/{issue_key}?expand=changelog").

### 4.2 F-002 — jira_query_basic.py

Responsibility: Basic JQL query wrappers.
Dependency: F-001 JiraClient methods search_issues(), get_issue(), get_changelog().

Mandatory functions:

    def fetch_issues_by_jql(client: JiraClient, jql: str, fields: str = "*all", max_results: int = 500) -> list
        Generic JQL search. Return issue list (extracted from response issues field).
        Calls: client.search_issues(jql, fields, max_results)

    def fetch_issue_by_key(client: JiraClient, issue_key: str, fields: str = "*all") -> dict
        Single issue query. Return issue dict.
        Calls: client.get_issue(issue_key, fields)

    def fetch_changelog_by_key(client: JiraClient, issue_key: str) -> dict
        Single issue changelog query. Return changelog dict.
        Calls: client.get_changelog(issue_key)

### 4.3 F-003 — jira_query_advanced.py

Responsibility: Advanced queries (recursive, bulk, cache).
Dependency: F-002 jira_query_basic functions.

Mandatory functions:

    def fetch_all_descendants(client: JiraClient, issue_key: str, fields: str, visited: set = None) -> list
        Recursively fetch all descendants of an issue (via linkedIssues JQL).
        Use visited set to prevent cycles. Return issue list.

    def fetch_epic_issues(client: JiraClient, epic_key: str, fields: str = "key,summary,issuetype,status,assignee,created,updated,duedate") -> list
        Fetch all issues under an Epic (including Epic itself + recursive descendants + dedup).
        Return unique issue list.

    def fetch_milestone_issues_v2(client: JiraClient, milestone_key: str, exclude_keys: list = None, fields: str = "key,summary,issuetype,status,assignee,created,updated,duedate") -> list
        Fetch all issues under a Milestone (including Milestone itself + direct children + recursive descendants).
        exclude_keys prevents cross-contamination with other milestones.
        Return unique issue list.

    def fetch_issues_by_summary_keywords(client: JiraClient, keywords: list, project_key: str = "WIL", max_results: int = 200) -> list
        JQL summary ~ keyword multi-keyword search.
        Each keyword independently escaped, OR logic.
        Return issue list.

    def build_changelog_cache(client: JiraClient, epic_key: str, cache_file: Path) -> dict
        Build changelog cache for all issues under epic.
        Cache format: {issue_key: changelog_dict}.
        Auto-create parent dirs. Return cache dict.

    def load_changelog_cache(cache_file: Path) -> dict
        Read changelog cache file.
        File not found -> return None.

### 4.4 F-004 — jira_field_parser.py

Responsibility: Safe issue field parser.

Mandatory functions:

    def get_issue_field(issue: dict, field_path: str, default: any = None) -> any
        Safely get nested field. field_path uses dot notation (e.g. "status.name").
        Field missing -> return default.

    def get_assignee_name(issue: dict) -> str
        Get assignee displayName. No assignee -> return "Unassigned".

    def get_status_name(issue: dict) -> str
        Get status name. No status -> return "Unknown".

    def get_issue_type(issue: dict) -> str
        Get issuetype name. Missing -> return "Unknown".

    def get_due_date(issue: dict) -> str
        Get duedate. Not set -> return None.

    def get_last_updated(issue: dict) -> str
        Get updated field date part (YYYY-MM-DD).
        Parse failure -> return "Unknown".

### 4.5 F-005 — jira_datetime_utils.py

Responsibility: Jira datetime format handling.

Mandatory functions:

    def normalize_jira_datetime(dt_str: str) -> str
        Jira date format -> ISO 8601 format.
        Handle: "2026-05-14T12:45:53.000+0800" -> "2026-05-14T12:45:53.000+08:00"
        Handle: "Z" -> "+00:00"
        Use regex: re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', dt_str)

    def days_since_updated(issue: dict) -> int
        Calculate days since last update.
        Use normalize_jira_datetime to parse updated field.
        Parse failure -> return 999.

    def today_str() -> str
        Return today date string YYYY-MM-DD.

## 5. Error Handling Rules

### 5.1 Hard Stop Conditions

Must stop immediately with single-line error:
    1. .env or config/config.json missing
    2. Jira API connection failure (auth error, network timeout)
    3. JQL syntax error (422)
    4. Issue Key not found (404)
    5. Script execution returns non-zero exit code

### 5.2 Warning But Continue

Output warning, continue execution:
    1. Rate limit triggered (403) -> exponential backoff retry
    2. Server error (5xx) -> linear backoff retry
    3. Field missing (use default value)
    4. Date parse failure (return 999)

### 5.3 Error Format

    ERROR: [brief desc] | [relevant file or params] | Stop.
    WARN: [brief desc] | [relevant file or params] | Continue.

## 6. Pending Items Handling

When encountering "pending confirmation" config items:
    1. Use suggested value to continue
    2. Mark in output: "Using default: [suggested value]"
    3. List pending items in suggestion list for later user confirmation

Do NOT stop execution due to pending items unless required and no suggestion value.

## 7. Version Check

Before executing any script, check version consistency:

    python scripts/jira_restful_core.py --version

Output must be v0.1.2. If mismatch, output warning:

    WARN: Version mismatch. Expected v0.1.2, got [actual version]. Continue at your own risk.

## 8. Cross-Skill Collaboration

### 8.1 Consumer Skill Reference

wilson-project-report as consumer skill references this connector layer:

    import sys
    from pathlib import Path
    SKILL_ROOT = Path(__file__).parent.parent
    sys.path.insert(0, str(SKILL_ROOT / "../jira-restful-api-connector/scripts"))
    import jira_restful_core as jira_core

Or declare dependency via skill package manager (WorkBuddy / OpenClaw).

### 8.2 Skill Defect Reporting

If discovering defects in this skill (script errors, output anomalies, logic mismatch),
use agent-skill-improving skill flow:
    1. Record defect phenomenon (screenshot or text)
    2. Record reproduction steps
    3. Record expected vs actual result
    4. Submit to owner for confirmation
    5. Wait for owner confirmation, then execute per SKILL_CORRECTIONS.md rules

Agent is forbidden from modifying scripts or config on its own.

## 9. Post-Execution Checklist

After each execution, confirm item by item:

    [ ] Return result is raw JSON / dict / list (no business analysis)
    [ ] .env not modified or exposed
    [ ] Error log recorded (if any)
    [ ] Rate limit status normal
    [ ] Conversation backed up (conversation_append.py)
    [ ] Exceptions or warnings recorded

All passed -> output "Execution complete"
Any failed -> output "Execution complete, pending items: [list]"

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| v0.1.0 | 2026-05-21 | Initial version. Split from jira-project-report v1.0.1 core. F-001~F-005, path rigidity, tiered error handling, interface LOCK PERMANENT |
| v0.1.1 | 2026-05-25 | Fix: Python scripts renamed to underscore format per naming rules. Fixed broken import statements. All .py content verified ASCII-only. |
| v0.1.2 | 2026-05-25 | Fix: Added missing high-level methods search_issues(), get_issue(), get_changelog() to JiraClient. Enhanced Section 4.1 docs to clarify two-layer architecture and F-002 dependency. Fixes #26. |

---

*This file is an LLM execution guide. Human-readable guide see README.md.*
*Generated: 2026-05-25*
