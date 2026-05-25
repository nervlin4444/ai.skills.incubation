'''
---
title: "jira_query_advanced.py"
name: "jira-restful-api-connector"
description: "F-003: Advanced queries (recursive descendants, bulk search, changelog cache)."
version: "v0.1.3"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T23:28:00+08:00"
fixes: []
auth_config:
  provider: jira
  auth_method: basic_or_bearer
  token_env_var: JIRA_API_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/scripts/jira_query_advanced.py"
  github_path: "jira-restful-api-connector/scripts/jira_query_advanced.py"
---
'''
import json
from pathlib import Path


def fetch_all_descendants(client, parent_keys, visited=None):
    """Recursively fetch all linked child issues."""
    if visited is None:
        visited = set()
    results = []
    for pk in parent_keys:
        if pk in visited:
            continue
        visited.add(pk)
        issue = fetch_issue_by_key(client, pk, fields="issuelinks")
        results.append(issue)
        links = issue.get("fields", {}).get("issuelinks", [])
        children = []
        for link in links:
            if link.get("type", {}).get("inward") == "is child of" or link.get("type", {}).get("outward") == "has child":
                child = link.get("inwardIssue") or link.get("outwardIssue")
                if child and child.get("key") not in visited:
                    children.append(child["key"])
        if children:
            results.extend(fetch_all_descendants(client, children, visited))
    return results


def fetch_epic_issues(client, epic_key):
    """Fetch all issues under an Epic (including descendants)."""
    epic = fetch_issue_by_key(client, epic_key)
    descendants = fetch_all_descendants(client, [epic_key])
    return [epic] + [d for d in descendants if d.get("key") != epic_key]


def fetch_milestone_issues_v2(client, milestone_key, other_milestone_keys=None):
    """Fetch milestone + all descendants, excluding other milestones."""
    milestone = fetch_issue_by_key(client, milestone_key)
    descendants = fetch_all_descendants(client, [milestone_key])
    all_issues = [milestone] + [d for d in descendants if d.get("key") != milestone_key]
    if other_milestone_keys:
        exclude = set(other_milestone_keys)
        all_issues = [i for i in all_issues if i.get("key") not in exclude]
    return all_issues


def fetch_issues_by_summary_keywords(client, project_key, keywords, max_results=1000):
    """Fetch issues where summary contains any of the keywords."""
    conditions = " OR ".join([f'summary ~ "{k}"' for k in keywords])
    jql = f'project = {project_key} AND ({conditions})'
    return fetch_issues_by_jql(client, jql, max_results=max_results)


def build_changelog_cache(client, epic_key, cache_path):
    """Build and save changelog cache for all issues under epic."""
    issues = fetch_epic_issues(client, epic_key)
    cache = {}
    for issue in issues:
        key = issue.get("key")
        if key:
            cache[key] = fetch_changelog_by_key(client, key)
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    return cache


def load_changelog_cache(cache_path):
    """Load changelog cache from file.

    Args:
        cache_path: Path to the cache JSON file.

    Returns:
        dict: {issue_key: changelog_dict} if file exists and is valid JSON.
        None: if file does not exist or JSON is invalid.
    """
    p = Path(cache_path)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


# Circular import helpers (called at runtime)
def fetch_issue_by_key(client, key, fields="*all"):
    from jira_query_basic import fetch_issue_by_key as _f
    return _f(client, key, fields)


def fetch_issues_by_jql(client, jql, max_results=1000):
    from jira_query_basic import fetch_issues_by_jql as _f
    return _f(client, jql, max_results=max_results)


def fetch_changelog_by_key(client, issue_key):
    from jira_query_basic import fetch_changelog_by_key as _f
    return _f(client, issue_key)
