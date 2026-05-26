#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""---
title: Skill Usage Logger Core
name: agent-skill-acquiring
description: Unified usage logging for skill search hits and adoption records.
version: v2.0.1
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T16:10:00+08:00
fixes: [37, 39]
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/scripts/core_logger.py"
  github_path: "agent-skill-acquiring/scripts/core_logger.py"
---"""

"""
core_logger.py
Usage logging for skill search adoption.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

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
    if platform == "windows":
        base = Path(os.environ.get("APPDATA", "~")).expanduser()
        return base / ".workbuddy" / "skills" / "agent-skill-acquiring" / "data"
    elif platform == "macos":
        return Path("~/.workbuddy/skills/agent-skill-acquiring/data").expanduser()
    else:
        return Path("~/.local/share/openclaw/skills/agent-skill-acquiring/data").expanduser()


def _get_log_path() -> Path:
    data_dir = _get_default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "usage_log.json"


def log_adoption(skill_name: str, keywords: List[str], rank: int, adopted: bool = True, notes: str = "") -> None:
    path = _get_log_path()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "skill_name": skill_name,
        "keywords": keywords,
        "rank": rank,
        "adopted": adopted,
        "notes": notes
    }
    logs = []
    if path.exists():
        try:
            with open(path, "r", encoding=ENCODING) as f:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = []
        except Exception:
            logs = []
    logs.append(entry)
    with open(path, "w", encoding=ENCODING) as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
