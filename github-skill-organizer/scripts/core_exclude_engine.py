"""
---
title: Core Exclude Engine
name: github-skill-organizer
description: Unified exclusion rule engine driven by config.json. Provides is_excluded() with base_path boundary to prevent .workbuddy false positives.
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
  local_path: scripts/core_exclude_engine.py
  github_path: github-skill-organizer/scripts/core_exclude_engine.py
---
"""

import json
from pathlib import Path


class ExcludeEngine:
    """
    Unified exclusion engine.
    Reads config.json and provides script-specific exclusion logic.
    KEY FIX: base_path boundary prevents parent-directory cascade exclusion.
    """

    def __init__(self, config_path: Path = None):
        if config_path is None:
            # Default: sibling of skill_organizer_config.py -> ../config/config.json
            script_dir = Path(__file__).parent.absolute()
            config_path = script_dir.parent / "config" / "sync.config.json"
        self.config_path = Path(config_path)
        self._config = self._load()

    def _load(self) -> dict:
        if not self.config_path.exists():
            # Fallback: use hardcoded safe defaults if config missing
            return {
                "global_excludes": {
                    "directories": [".backups", ".git", "__pycache__", "node_modules", ".vscode", ".idea"],
                    "files": ["LICENSE", "LICENSE.md"],
                    "suffixes": [".pyc", ".pyo", ".so", ".bak"],
                    "prefixes": ["temp_", "tmp_"]
                },
                "script_profiles": {}
            }
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_rules(self, profile: str = "default") -> dict:
        """Get merged rules for a script profile."""
        global_rules = self._config.get("global_excludes", {})
        profiles = self._config.get("script_profiles", {})
        profile_cfg = profiles.get(profile, {})

        if not profile_cfg.get("inherit_global", True):
            return profile_cfg

        merged = {
            "directories": list(set(
                global_rules.get("directories", []) + profile_cfg.get("extra_directories", [])
            )),
            "files": list(set(
                global_rules.get("files", []) + profile_cfg.get("extra_files", [])
            )),
            "suffixes": global_rules.get("suffixes", []),
            "prefixes": global_rules.get("prefixes", []),
            "check_parents": profile_cfg.get("check_parents", False),
            "base_path_boundary": profile_cfg.get("base_path_boundary", False),
            "skip_frontmatter_validation": profile_cfg.get("skip_frontmatter_validation", []),
        }
        return merged

    def is_excluded(self, path: Path, profile: str = "default", base_path: Path = None) -> bool:
        """
        Check if a path should be excluded.

        Args:
            path: File or directory to check
            profile: Script profile name (e.g. "skill_uploader", "file_scouter")
            base_path: Boundary path. If set, parent checks stop at this boundary.
                      This FIXES the .workbuddy cascade exclusion bug.
        """
        rules = self.get_rules(profile)
        name = path.name

        # Check the path itself
        if path.is_dir():
            if name in rules["directories"]:
                return True
            if any(name.startswith(p) for p in rules["prefixes"]):
                return True
        else:
            if name in rules["files"]:
                return True
            if any(name.endswith(s) for s in rules["suffixes"]):
                return True
            if any(name.startswith(p) for p in rules["prefixes"]):
                return True

        # Check parents (with boundary protection)
        if rules.get("check_parents", False):
            for parent in path.parents:
                # Boundary check: stop at base_path or its ancestors
                if base_path and (parent == base_path or parent in base_path.parents):
                    break
                if self._should_exclude_simple(parent, rules):
                    return True

        return False

    def _should_exclude_simple(self, path: Path, rules: dict) -> bool:
        """Simple exclusion check for a single path (used in parent iteration)."""
        name = path.name
        if path.is_dir():
            if name in rules["directories"]:
                return True
            if any(name.startswith(p) for p in rules["prefixes"]):
                return True
        else:
            if name in rules["files"]:
                return True
            if any(name.endswith(s) for s in rules["suffixes"]):
                return True
            if any(name.startswith(p) for p in rules["prefixes"]):
                return True
        return False

    def should_skip_frontmatter(self, filename: str, profile: str = "default") -> bool:
        """Check if a file should skip frontmatter validation (e.g. CHANGELOG.md)."""
        rules = self.get_rules(profile)
        return filename in rules.get("skip_frontmatter_validation", [])
