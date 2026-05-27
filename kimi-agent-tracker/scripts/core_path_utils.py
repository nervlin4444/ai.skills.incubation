"""
---
title: "Core Path Utilities"
name: "kimi-agent-tracker"
description: "Shared path resolution utilities for cross-platform skill directory management. Resolves baseDir, expands home, ensures directories exist."
version: "v5.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-26T18:15:30.038+00:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{{baseDir}}/scripts/core_path_utils.py"
  github_path: "kimi-agent-tracker/scripts/core_path_utils.py"
---
"""

import os
import sys
from pathlib import Path


def get_skill_dir() -> Path:
    # Resolve skill root from this file location: scripts/ -> parent -> skill root
    return Path(__file__).resolve().parent.parent


def resolve_path(path_tpl: str, skill_dir: Path = None) -> Path:
    # Resolve path template with baseDir placeholder and home expansion
    if skill_dir is None:
        skill_dir = get_skill_dir()
    resolved = path_tpl.replace("{baseDir}", str(skill_dir))
    if resolved.startswith("~/"):
        resolved = os.path.expanduser(resolved)
    return Path(resolved)


def ensure_dir(path_tpl: str, skill_dir: Path = None) -> Path:
    # Ensure directory exists, create if missing
    p = resolve_path(path_tpl, skill_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_config_dir(skill_dir: Path = None) -> Path:
    return ensure_dir("{baseDir}/config", skill_dir)


def get_data_dir(skill_dir: Path = None) -> Path:
    return ensure_dir("{baseDir}/data", skill_dir)


def get_logs_dir(skill_dir: Path = None) -> Path:
    return ensure_dir("{baseDir}/logs", skill_dir)


def get_download_dir(skill_dir: Path = None) -> Path:
    # Download directory is OUTSIDE skill dir to avoid frontmatter upload conflicts
    # Controlled by tracker_config, default to ~/Downloads
    dl_path = Path.home() / "Downloads"
    dl_path.mkdir(parents=True, exist_ok=True)
    return dl_path


def get_conversations_json_path(skill_dir: Path = None) -> Path:
    return get_config_dir(skill_dir) / "conversations.json"


def get_tracker_config_path(skill_dir: Path = None) -> Path:
    return get_config_dir(skill_dir) / "tracker_config.json"


def get_download_state_path(skill_dir: Path = None) -> Path:
    return get_data_dir(skill_dir) / "download_state.json"


if __name__ == "__main__":
    sd = get_skill_dir()
    print(f"skill_dir: {sd}")
    print(f"config_dir: {get_config_dir(sd)}")
    print(f"data_dir: {get_data_dir(sd)}")
    print(f"logs_dir: {get_logs_dir(sd)}")
    print(f"download_dir: {get_download_dir(sd)}")
