'''
---
title: "jira_datetime_utils.py"
name: "jira-restful-api-connector"
description: "F-005: Jira datetime format utilities. Normalize +0800 to +08:00, day calculation."
version: "v0.1.3"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T21:42:00+08:00"
fixes: [27, 30]
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


def normalize_jira_datetime(dt_str):
    """Normalize Jira datetime string to ISO 8601.

    Behavior rules (do NOT report as bugs):
      - Trailing .000 microseconds are dropped by datetime.isoformat().
        Input "2026-05-14T12:45:53.000+0800" returns "2026-05-14T12:45:53+08:00".
        This is Python standard behavior. Expected.
      - Z suffix (UTC Zulu time) converted to +00:00.
      - Inputs without timezone use local system timezone.
      - Date-only inputs (no T separator) returned as-is.
    """
    if not dt_str:
        return ""

    # Handle Z suffix (UTC Zulu time): replace Z with +0000 for strptime %z parsing
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+0000"

    # Date-only: no T separator, return as-is without time appended
    if "T" not in dt_str:
        return dt_str

    # Parse with strptime. %z expects +0800 (no colon), so parse BEFORE isoformat.
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(dt_str, fmt)
            if dt.tzinfo is None:
                # Use local system timezone; do NOT hardcode +08:00
                dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            # isoformat() automatically formats timezone as +08:00 (with colon)
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
