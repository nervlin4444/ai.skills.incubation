#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""---
title: Skill Profile Search
name: agent-skill-acquiring
description: Multi-keyword skill search with user-first ranking and adoption logging.
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
  local_path: "{baseDir}/scripts/skill_profile_search.py"
  github_path: "agent-skill-acquiring/scripts/skill_profile_search.py"
---"""

"""
skill_profile_search.py
Search skills by keywords. Return top 5 matches.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from core_profile_io import load_profile, list_skills
from core_logger import log_adoption


def _match_score(skill: Dict[str, Any], keywords: List[str]) -> int:
    score = 0
    fields = [
        skill.get("name", ""),
        skill.get("description", ""),
        skill.get("alias", ""),
        " ".join(skill.get("keywords", []))
    ]
    text = " ".join(str(f) for f in fields if f).lower()
    for kw in keywords:
        kw_lower = kw.lower()
        if re.search(r'\b' + re.escape(kw_lower) + r'\b', text):
            score += 2
        elif kw_lower in text:
            score += 1
    return score


def search(keywords: List[str], max_results: int = 5) -> List[Tuple[str, Dict[str, Any], int]]:
    if not keywords:
        return []
    profile = load_profile()
    if not profile:
        return []
    results = []
    for name, meta in profile.items():
        score = _match_score(meta, keywords)
        if score > 0:
            results.append((name, meta, score))

    def _sort_key(item):
        name, meta, score = item
        source = meta.get("source", "external")
        source_order = 0 if source == "user" else 1
        return (source_order, -score, name)

    results.sort(key=_sort_key)
    return results[:max_results]


def format_results(results: List[Tuple[str, Dict[str, Any], int]]) -> str:
    if not results:
        return "[SKILL-NOT-FOUND] No matching skills found."
    lines = [
        "| Rank | Skill Name | Alias | Summary | Score | Source |",
        "|------|------------|-------|---------|-------|--------|"
    ]
    for idx, (name, meta, score) in enumerate(results, 1):
        alias = meta.get("alias", "")
        summary = meta.get("skill_summary", "")
        source = meta.get("source", "unknown")
        lines.append(f"| {idx} | {name} | {alias} | {summary} | {score} | {source} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Search skills by keywords")
    parser.add_argument("keywords", nargs="+", help="Search keywords")
    parser.add_argument("--max-results", type=int, default=5, help="Maximum results")
    parser.add_argument("--log", action="store_true", help="Log adoption for rank 1")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    args = parser.parse_args()
    results = search(args.keywords, args.max_results)
    if args.log and results:
        top_name, top_meta, top_score = results[0]
        log_adoption(top_name, args.keywords, 1, adopted=True)
    if args.format == "json":
        output = []
        for name, meta, score in results:
            entry = dict(meta)
            entry["_name"] = name
            entry["_score"] = score
            output.append(entry)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(format_results(results))


if __name__ == "__main__":
    main()
