'''
---
title: "jira.query.basic.py"
name: "jira-restful-api-connector"
description: "F-002: Basic JQL query wrappers (search / get / changelog)."
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
  local_path: "{baseDir}/scripts/jira.query.basic.py"
  github_path: "jira-restful-api-connector/scripts/jira.query.basic.py"
---
'''

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import jira_restful_core as core

VERSION = "v0.1.0"


def fetch_issues_by_jql(client, jql, fields="*all", max_results=500):
    """Generic JQL search. Return issue list extracted from response."""
    result = client.search_issues(jql, fields=fields, max_results=max_results)
    return result.get("issues", [])


def fetch_issue_by_key(client, issue_key, fields="*all"):
    """Fetch single issue by key. Return issue dict."""
    return client.get_issue(issue_key, fields=fields)


def fetch_changelog_by_key(client, issue_key):
    """Fetch single issue changelog. Return changelog dict."""
    detail = client.get_changelog(issue_key)
    return detail.get("changelog", {})


if __name__ == "__main__":
    print(f"jira.query.basic.py {VERSION}")
    print("This is a shared library. Do not run directly.")
