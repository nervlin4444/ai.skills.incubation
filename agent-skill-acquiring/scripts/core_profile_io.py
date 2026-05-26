#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""---
title: Skill Profile IO Core
name: agent-skill-acquiring
description: Unified read/write for skill_profile.json with UTF-8 no-BOM guarantee and cross-platform path resolution.
version: v2.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T12:10:00+08:00
fixes: []
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/scripts/core_profile_io.py"
  github_path: "agent-skill-acquiring/scripts/core_profile_io.py"
---"""

"""
core_profile_io.py
Unified read/write for skill_profile.json.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

ENCODING = "utf-8"


def _get_platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    elif sys.platform == "darwin":
        return "macos"
    return "linux"


def _expand_path(path_str: str) -> Path:
    if sys.platform.startswith("win"):
        import re
        def _repl(m):
            return os.environ.get(m.group(1), m.group(0))
        path_str = re.sub(r'%([^%]+)%', _repl, path_str)
    return Path(os.path.expandvars(os.path.expanduser(path_str)))


def _get_default_data_dir() -> Path:
    platform = _get_platform()
    script_dir = Path(__file__).resolve().parent
    config_path = script_dir.parent / "config" / "acquiring.config.json"
    if not config_path.exists():
        config_path = script_dir / "acquiring.config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding=ENCODING) as f:
                cfg = json.load(f)
            defaults = cfg.get("workstation_defaults", {}).get(platform, {})
            data_folder = defaults.get("data_folder")
            if data_folder:
                return _expand_path(data_folder)
        except Exception:
            pass
    if platform == "windows":
        base = Path(os.environ.get("APPDATA", "~")).expanduser()
        return base / ".workbuddy" / "skills" / "agent-skill-acquiring" / "data"
    elif platform == "macos":
        return Path("~/.workbuddy/skills/agent-skill-acquiring/data").expanduser()
    else:
        return Path("~/.local/share/openclaw/skills/agent-skill-acquiring/data").expanduser()


def get_profile_path() -> Path:
    data_dir = _get_default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "skill_profile.json"


def load_profile() -> Dict[str, Any]:
    path = get_profile_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding=ENCODING) as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {}


def save_profile(data: Dict[str, Any]) -> None:
    path = get_profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding=ENCODING) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def get_skill_entry(profile: Dict[str, Any], skill_name: str) -> Optional[Dict[str, Any]]:
    return profile.get(skill_name)


def list_skills(profile: Dict[str, Any], source: Optional[str] = None) -> List[str]:
    if source is None:
        return sorted(profile.keys())
    return sorted([k for k, v in profile.items() if v.get("source") == source])


def update_skill(profile: Dict[str, Any], skill_name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    existing = profile.get(skill_name, {})
    existing.update(metadata)
    profile[skill_name] = existing
    return profile


def remove_skill(profile: Dict[str, Any], skill_name: str) -> Dict[str, Any]:
    profile.pop(skill_name, None)
    return profile
