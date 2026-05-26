#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""---
title: Skill Profile Book
name: agent-skill-acquiring
description: Display skill profile as markdown table. Page=skills shows alias, summary, and function.
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
  local_path: "{baseDir}/scripts/skill_profile_book.py"
  github_path: "agent-skill-acquiring/scripts/skill_profile_book.py"
---"""

"""
skill_profile_book.py
Display skill profile as markdown table.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from core_profile_io import load_profile, list_skills


def book(page: str = "skills") -> str:
    if page != "skills":
        return f"[ERROR] Unknown page: {page}. Supported: skills"
    profile = load_profile()
    if not profile:
        return "[EMPTY] No skills in profile. Run extract first."
    names = list_skills(profile)
    lines = [
        "| Alias | Skill Name | Skill Summary | Function Summary |",
        "|-------|------------|---------------|------------------|"
    ]
    for name in names:
        meta = profile.get(name, {})
        alias = meta.get("alias", "")
        skill_summary = meta.get("skill_summary", "")
        function_summary = meta.get("function_summary", "")
        lines.append(f"| {alias} | {name} | {skill_summary} | {function_summary} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Display skill profile book")
    parser.add_argument("--page", default="skills", help="Page to display")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    args = parser.parse_args()
    if args.format == "json":
        profile = load_profile()
        names = list_skills(profile)
        data = []
        for name in names:
            meta = profile.get(name, {})
            data.append({
                "alias": meta.get("alias", ""),
                "name": name,
                "skill_summary": meta.get("skill_summary", ""),
                "function_summary": meta.get("function_summary", "")
            })
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(book(args.page))


if __name__ == "__main__":
    main()
