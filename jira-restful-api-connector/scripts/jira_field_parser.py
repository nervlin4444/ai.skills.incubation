'''
---
title: "jira_field_parser.py"
name: "jira-restful-api-connector"
description: "F-004: Safe issue field parser. Dot-path nested field extraction with defaults."
version: "v0.1.3"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T20:42:00+08:00"
fixes: [27, 28]
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
def get_issue_field(issue, field_name, default=""):
    return issue.get("fields", {}).get(field_name, default)


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
    return get_issue_field(issue, "updated", "")
