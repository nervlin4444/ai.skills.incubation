"""
---
title: Core Frontmatter Extractor
name: github-skill-organizer
description: Unified frontmatter extraction for .md (YAML), .py (docstring YAML), .json (_meta). Replaces duplicated logic in 6 scripts.
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
  local_path: scripts/core_frontmatter.py
  github_path: github-skill-organizer/scripts/core_frontmatter.py
---
"""

import re
import json
from pathlib import Path


class FrontmatterExtractor:
    """
    Unified frontmatter extractor.
    Supports .md (YAML frontmatter), .py (docstring YAML block), .json (_meta field).
    """

    @staticmethod
    def extract(file_path: Path) -> dict | None:
        """Extract frontmatter from any skill file. Returns None if not found or unparseable."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        suffix = file_path.suffix

        if suffix == ".md" and content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                return FrontmatterExtractor.parse_yaml(content[3:end])

        if suffix == ".py":
            match = re.search(r'"""\s*---\s*(.*?)\s*---\s*"""', content, re.DOTALL)
            if match:
                return FrontmatterExtractor.parse_yaml(match.group(1))
            # Also try single quotes
            match = re.search(r"'''\s*---\s*(.*?)\s*---\s*'''", content, re.DOTALL)
            if match:
                return FrontmatterExtractor.parse_yaml(match.group(1))

        if suffix == ".json":
            try:
                data = json.loads(content)
                if "_meta" in data:
                    return data["_meta"]
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def is_invalid(file_path: Path) -> dict | None:
        """
        Check if file has frontmatter traces but is unparseable.
        Returns {"_invalid": True, "reason": "..."} or None.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        if file_path.suffix == ".md" and "---" in content[:500]:
            if not content.startswith("---"):
                return {"_invalid": True, "reason": "md_frontmatter_unparseable", "path": str(file_path)}

        if file_path.suffix == ".py":
            dq = chr(34) * 3
            sq = chr(39) * 3
            has_docstring = dq in content[:500] or sq in content[:500]
            if has_docstring and "---" in content[:500]:
                # Try extraction
                fm = FrontmatterExtractor.extract(file_path)
                if fm is None:
                    return {"_invalid": True, "reason": "py_docstring_frontmatter_unparseable", "path": str(file_path)}

        return None

    @staticmethod
    def parse_yaml(yaml_text: str) -> dict:
        """
        Parse a simple subset of YAML: key: value and basic nesting.
        Replaces _parse_simple_yaml duplicated in 5 scripts.
        """
        result = {}
        current_key = None
        current_dict = None

        for line in yaml_text.splitlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r'^(\s*)([\w_]+):\s*(.*)$', line)
            if match:
                indent, key, value = match.groups()
                indent_level = len(indent)
                if indent_level == 0:
                    current_key = key
                    if not value:
                        result[key] = {}
                        current_dict = result[key]
                    else:
                        result[key] = value.strip().strip('"').strip("'")
                        current_dict = None
                elif current_dict is not None and indent_level > 0:
                    current_dict[key] = value.strip().strip('"').strip("'")

        return result if result else None
