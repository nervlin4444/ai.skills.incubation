"""
---
title: Core Path Utilities
name: github-skill-organizer
description: Path expansion and normalization utilities. Replaces repeated expanduser/expandvars logic across all scripts.
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
  local_path: scripts/core_path_utils.py
  github_path: github-skill-organizer/scripts/core_path_utils.py
---
"""

import os
from pathlib import Path


def normalize_path(path_str) -> Path:
    """
    Normalize any path input: expanduser + expandvars + resolve.
    Supports str, Path, or None (returns None).
    """
    if path_str is None:
        return None
    if isinstance(path_str, Path):
        return path_str.expanduser().resolve()
    return Path(os.path.expanduser(os.path.expandvars(str(path_str).strip()))).resolve()


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, create if not."""
    path.mkdir(parents=True, exist_ok=True)
    return path
