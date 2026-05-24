"""
---
title: Core Logger
name: github-skill-organizer
description: Unified logging format with [TAG] prefix for all scripts. Ensures consistent agent-parsable output.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-24T15:58:00+08:00
fixes: []
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: scripts/core_logger.py
  github_path: github-skill-organizer/scripts/core_logger.py
---
"""

import sys
from datetime import datetime, timezone


def log(tag: str, message: str, level: str = "INFO"):
    """
    Unified log output: 2026-05-24 14:00:00 [INFO] [TAG] message
    All scripts MUST use this function instead of print() for operational logs.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [{level}] [{tag}] {message}"
    print(line, file=sys.stdout if level != "ERROR" else sys.stderr)
    return line


def log_error(tag: str, error_code: str, reason: str, hint: str, fix_action: str):
    """
    Structured error log for agent self-repair.
    Returns dict for programmatic consumption.
    """
    log(tag, f"ERROR[{error_code}]: {reason}", "ERROR")
    log(tag, f"HINT: {hint}", "ERROR")
    log(tag, f"FIX: {fix_action}", "ERROR")
    return {
        "status": "error",
        "error_code": error_code,
        "reason": reason,
        "hint": hint,
        "fix_action": fix_action,
    }
