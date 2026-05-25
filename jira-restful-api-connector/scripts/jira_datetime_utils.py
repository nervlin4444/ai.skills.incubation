'''
---
title: "jira_datetime_utils.py"
name: "jira-restful-api-connector"
description: "F-005: Jira datetime format utilities. Normalize +0800 to +08:00, day calculation."
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
  local_path: "{baseDir}/scripts/jira_datetime_utils.py"
  github_path: "jira-restful-api-connector/scripts/jira_datetime_utils.py"
---
'''
from datetime import datetime, timezone, timedelta
import re


def normalize_jira_datetime(dt_str):
    """Normalize Jira datetime string to ISO 8601 with +08:00."""
    if not dt_str:
        return ""
    dt_str = dt_str.replace("+0000", "+00:00").replace("+0800", "+08:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(dt_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
            return dt.isoformat()
        except ValueError:
            continue
    return dt_str


def days_since_updated(updated_str):
    """Return days since last update."""
    norm = normalize_jira_datetime(updated_str)
    if not norm:
        return 999
    try:
        dt = datetime.fromisoformat(norm)
        now = datetime.now(dt.tzinfo)
        return (now - dt).days
    except Exception:
        return 999


def today_str():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
