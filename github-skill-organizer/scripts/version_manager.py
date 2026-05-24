#!/usr/bin/env python3
'''
---
title: Version Manager
name: github-skill-organizer
description: Auto-detects changes, bumps version across all skill files, and records entries to CHANGELOG.md. Uses core_frontmatter for extraction and core_exclude_engine for file filtering. v1.2.0 refactored to use core modules.
version: "1.2.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-24T21:50:00+08:00"
fixes: []
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: "../.env"
file_mapping:
  local_path: "scripts/version_manager.py"
  github_path: "github-skill-organizer/scripts/version_manager.py"
---
'''

import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

try:
    from skill_organizer_config import load_config
    from core_frontmatter import FrontmatterExtractor
    from core_exclude_engine import ExcludeEngine
    from core_path_utils import normalize_path
    from core_logger import log
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config
    from core_frontmatter import FrontmatterExtractor
    from core_exclude_engine import ExcludeEngine
    from core_path_utils import normalize_path
    from core_logger import log


class VersionManager:
    def __init__(self, skill_dir: str, dry_run: bool = True):
        self.skill_dir = normalize_path(skill_dir)
        self.dry_run = dry_run
        self.changelog_path = self.skill_dir / "CHANGELOG.md"
        self.exclude = ExcludeEngine()
        self.modified_files = []
        self.errors = []

    def bump(self, bump_type: str, message: str) -> dict:
        if not self.skill_dir.exists():
            return {"status": "error", "reason": f"Skill directory not found: {self.skill_dir}"}

        current_version = self._read_current_version()
        if not current_version:
            return {"status": "error", "reason": "Could not read current version from SKILL.md"}

        new_version = self._compute_new_version(current_version, bump_type)
        if not new_version:
            return {"status": "error", "reason": f"Invalid version format: {current_version}"}

        for file_path in self._scan_files():
            try:
                result = self._bump_file(file_path, current_version, new_version)
                if result["modified"]:
                    self.modified_files.append({
                        "file": str(file_path.relative_to(self.skill_dir)),
                        "old_version": current_version,
                        "new_version": new_version,
                    })
            except Exception as e:
                self.errors.append({
                    "file": str(file_path.relative_to(self.skill_dir)),
                    "error": str(e),
                })

        changelog_updated = False
        if self.modified_files:
            changelog_updated = self._record_changelog(bump_type, new_version, message)

        return {
            "status": "ok",
            "dry_run": self.dry_run,
            "bump_type": bump_type,
            "old_version": current_version,
            "new_version": new_version,
            "message": message,
            "modified_count": len(self.modified_files),
            "modified_files": self.modified_files,
            "changelog_updated": changelog_updated,
            "changelog_path": str(self.changelog_path),
            "errors": self.errors,
        }

    def _read_current_version(self) -> str:
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            md_files = [f for f in self.skill_dir.glob("*.md") if f.is_file()]
            if md_files:
                skill_md = md_files[0]
            else:
                return ""

        fm = FrontmatterExtractor.extract(skill_md)
        if fm and "version" in fm:
            return str(fm["version"]).lstrip("v")
        return ""

    def _compute_new_version(self, version_str: str, bump_type: str) -> str:
        parts = version_str.strip().split(".")
        while len(parts) < 3:
            parts.append("0")
        try:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            return ""

        if bump_type == "patch":
            patch += 1
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        else:
            return ""

        return f"{major}.{minor}.{patch}"

    def _scan_files(self):
        for pattern in ["**/*.md", "**/*.py", "**/*.json"]:
            for file_path in self.skill_dir.glob(pattern):
                if not file_path.is_file():
                    continue
                if self.exclude.is_excluded(file_path, "version_manager", base_path=self.skill_dir):
                    continue
                yield file_path

    def _bump_file(self, file_path: Path, old_version: str, new_version: str) -> dict:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        original = content

        suffix = file_path.suffix

        if suffix == ".json":
            new_content = self._bump_json(content, old_version, new_version)
        else:
            new_content = self._bump_text(content, old_version, new_version)

        if new_content == original:
            return {"modified": False}

        if not self.dry_run:
            file_path.write_text(new_content, encoding="utf-8")
            log("VERSION_MGR", f"Bumped {file_path.name}: {old_version} -> {new_version}")

        return {"modified": True}

    def _bump_text(self, content: str, old_version: str, new_version: str) -> str:
        lines = content.splitlines()
        new_lines = []
        modified = False
        for line in lines:
            if "version:" in line and old_version in line:
                new_line = line.replace(old_version, new_version, 1)
                new_lines.append(new_line)
                modified = True
            else:
                new_lines.append(line)
        if modified:
            sep = chr(10)
            return sep.join(new_lines) + sep
        return content

    def _bump_json(self, content: str, old_version: str, new_version: str) -> str:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return content

        modified = False
        if "_meta" in data and "version" in data["_meta"]:
            if data["_meta"]["version"] == old_version:
                data["_meta"]["version"] = new_version
                modified = True

        if not modified:
            return content

        return json.dumps(data, indent=2, ensure_ascii=False) + chr(10)

    def _record_changelog(self, bump_type: str, new_version: str, message: str) -> bool:
        try:
            self.changelog_path.parent.mkdir(parents=True, exist_ok=True)

            if self.changelog_path.exists():
                content = self.changelog_path.read_text(encoding="utf-8")
            else:
                sep = chr(10)
                header = "# Changelog" + sep + sep
                header += "All notable changes to this skill will be documented in this file." + sep + sep
                content = header

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sep = chr(10)
            entry = f"## [{new_version}] - {today}" + sep + sep
            entry += f"### {bump_type.upper()}" + sep + sep
            entry += f"- {message}" + sep
            if self.modified_files:
                entry += "- Modified files:" + sep
                for mf in self.modified_files:
                    fname = mf["file"]
                    entry += f"  - `{fname}`" + sep
            entry += sep

            marker = "# Changelog"
            header_end = content.find(sep + sep, content.find(marker))
            if header_end == -1:
                new_content = content + sep + entry
            else:
                new_content = content[:header_end + 2] + entry + content[header_end + 2:]

            if not self.dry_run:
                self.changelog_path.write_text(new_content, encoding="utf-8")
                log("VERSION_MGR", f"CHANGELOG updated: {self.changelog_path}")

            return True
        except Exception as e:
            self.errors.append({
                "file": str(self.changelog_path),
                "error": f"CHANGELOG record failed: {e}",
            })
            return False


def main():
    parser = argparse.ArgumentParser(description="Version Manager for Skill Packages v1.2.0")
    parser.add_argument("--skill-dir", required=True, help="Path to skill directory")
    parser.add_argument("--bump-type", required=True, choices=["patch", "minor", "major"],
                        help="Version bump type")
    parser.add_argument("--message", required=True, help="Change description (provided by agent)")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")

    args = parser.parse_args()

    manager = VersionManager(skill_dir=args.skill_dir, dry_run=not args.apply)
    result = manager.bump(bump_type=args.bump_type, message=args.message)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get("status") == "ok" and not result.get("dry_run"):
        print()
        print(f"Version bumped to {result['new_version']}")
        print(f"CHANGELOG updated: {result['changelog_path']}")
    elif result.get("status") == "ok" and result.get("dry_run"):
        print()
        print(f"DRY-RUN: Would bump to {result['new_version']}")
        print(f"Files to modify: {result['modified_count']}")


if __name__ == "__main__":
    main()
