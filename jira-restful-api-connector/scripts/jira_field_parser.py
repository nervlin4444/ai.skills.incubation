'''
---
title: "jira_field_parser.py"
name: "jira-restful-api-connector"
description: "F-004: Safe issue field parser. Dot-path nested field extraction with defaults."
version: "v0.1.3"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T22:12:00+08:00"
fixes: [28, 29]
auth_config:
  provider: jira
  auth_method: basic_or_bearer
  token_env_var: JIRA_API_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/scripts/jira_field_parser.py"
  github_path: "jira-restful-api-connector/scripts/jira_field_parser.py"
---
'''
def get_issue_field(issue, field_path, default=""):
    """Safely get nested field using dot notation (e.g. 'status.name').

    Args:
        issue: Jira issue dict with 'fields' key.
        field_path: Dot-separated path like 'status.name' or 'assignee.displayName'.
        default: Value to return if path not found or any intermediate value is None.

    Returns:
        The nested value, or default if path invalid or value is None.
    """
    parts = field_path.split(".")
    current = issue.get("fields", {})
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current if current is not None else default


def get_assignee_name(issue):
    assignee = get_issue_field(issue, "assignee")
    if assignee:
        return assignee.get("displayName", "Unassigned")
    return "Unassigned"


def get_status_name(issue):
    status = get_issue_field(issue, "status")
    if status:
        return status.get("name", "Unknown")
    return "Unknown"


def get_issue_type(issue):
    it = get_issue_field(issue, "issuetype")
    if it:
        return it.get("name", "Unknown")
    return "Unknown"


def get_due_date(issue):
    """Get duedate. Not set or None -> return empty string."""
    result = get_issue_field(issue, "duedate", "")
    return result if result is not None else ""


def get_last_updated(issue):
    """Get updated field date part (YYYY-MM-DD). Parse failure -> return Unknown."""
    raw = get_issue_field(issue, "updated", "")
    if not raw:
        return "Unknown"
    try:
        return raw[:10]
    except Exception:
        return "Unknown"
