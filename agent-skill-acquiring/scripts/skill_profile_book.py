#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""---
title: Skill Profile Book
name: agent-skill-acquiring
description: Display skill profile as markdown table. Page=skills shows alias, summary, and function. v2.0.1 added dual-sort (user by usage ranking, external by alias) and pending-alias display.
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
  local_path: "{baseDir}/scripts/skill_profile_book.py"
  github_path: "agent-skill-acquiring/scripts/skill_profile_book.py"
---"""

"""
skill_profile_book.py
Display skill profile as markdown table.
v2.0.1: 3-column layout, dual-sort, pending-alias handling.
ABSOLUTE RULE: Output raw markdown table. NEVER wrap in ``` code blocks.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from core_profile_io import load_profile, list_skills, get_usage_stats


def _format_alias(meta: Dict[str, Any], skill_name: str) -> str:
    alias = meta.get("alias", "")
    if alias and alias != "[PENDING-ALIAS]":
        return alias
    func = meta.get("function_summary", "")
    if func:
        return f"[{skill_name} {func}]"
    return f"[{skill_name}]"


def book(page: str = "skills") -> str:
    if page != "skills":
        return f"[ERROR] Unknown page: {page}. Supported: skills"
    profile = load_profile()
    if not profile:
        return "[EMPTY] No skills in profile. Run extract first."
    usage_stats = get_usage_stats()
    names = list_skills(profile)
    user_items = []
    external_items = []
    for name in names:
        meta = profile.get(name, {})
        source = meta.get("source", "external")
        display_alias = _format_alias(meta, name)
        item = (name, meta, display_alias)
        if source == "user":
            user_items.append(item)
        else:
            external_items.append(item)
    user_items.sort(key=lambda x: (-usage_stats.get(x[0], 0), x[2]))
    external_items.sort(key=lambda x: x[2])
    all_items = user_items + external_items
    lines = [
        "| Alias | Skill Summary | Function Summary |",
        "|-------|---------------|------------------|"
    ]
    for name, meta, display_alias in all_items:
        skill_summary = meta.get("skill_summary", "")
        function_summary = meta.get("function_summary", "")
        lines.append(f"| {display_alias} | {skill_summary} | {function_summary} |")
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
                "alias": _format_alias(meta, name),
                "skill_summary": meta.get("skill_summary", ""),
                "function_summary": meta.get("function_summary", "")
            })
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(book(args.page))


if __name__ == "__main__":
    main()
