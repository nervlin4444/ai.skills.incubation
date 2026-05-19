"""
---
title: Version Manager
name: github-skill-organizer
description: Auto-detects changes, bumps version across all skill files, and records entries to CHANGELOG.md. Accepts agent-provided change descriptions.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/version_manager.py"
  github_path: "github-skill-organizer/scripts/version_manager.py"
---
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    from skill_organizer_config import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config


class VersionManager:
    """
    Manages version bumping and CHANGELOG recording for skill packages.
    - Scans all .md/.py/.json files in skill directory
    - Bumps version field in frontmatter/docstring/_meta
    - Records entry to scripts/CHANGELOG.md
    - Accepts agent-provided change description via --message
    """

    def __init__(self, skill_dir: str, dry_run: bool = True):
        self.skill_dir = Path(skill_dir).resolve()
        self.dry_run = dry_run
        self.scripts_dir = self.skill_dir / "scripts"
        self.changelog_path = self.scripts_dir / "CHANGELOG.md"
        self.modified_files = []
        self.errors = []

    def bump(self, bump_type: str, message: str) -> dict:
        """
        Main entry: bump version and record changelog.
        bump_type: "patch" | "minor" | "major"
        message: Change description provided by agent
        Returns: {"status": str, "old_version": str, "new_version": str, "modified_files": [...], "changelog_updated": bool}
        """
        if not self.skill_dir.exists():
            return {"status": "error", "reason": f"Skill directory not found: {self.skill_dir}"}

        # Step 1: Read current version from SKILL.md
        current_version = self._read_current_version()
        if not current_version:
            return {"status": "error", "reason": "Could not read current version from SKILL.md"}

        # Step 2: Compute new version
        new_version = self._compute_new_version(current_version, bump_type)
        if not new_version:
            return {"status": "error", "reason": f"Invalid version format: {current_version}"}

        # Step 3: Scan and bump all files
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

        # Step 4: Record CHANGELOG
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
        """Read version from SKILL.md frontmatter."""
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            # Fallback: first .md file
            md_files = list(self.skill_dir.glob("*.md"))
            if md_files:
                skill_md = md_files[0]
            else:
                return ""

        try:
            content = skill_md.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r'version:\s*["']?([\d.]+)["']?', content)
            if match:
                return match.group(1)
        except Exception:
            pass
        return ""

    def _compute_new_version(self, version_str: str, bump_type: str) -> str:
        """Compute new semver based on bump type."""
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
        """Yield all files that may contain version frontmatter."""
        for pattern in ["**/*.md", "**/*.py", "**/*.json"]:
            for file_path in self.skill_dir.glob(pattern):
                if file_path.is_file() and not file_path.name.startswith("."):
                    yield file_path

    def _bump_file(self, file_path: Path, old_version: str, new_version: str) -> dict:
        """Bump version in a single file. Supports .md, .py, .json."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        original = content

        suffix = file_path.suffix

        if suffix == ".json":
            new_content = self._bump_json(content, old_version, new_version)
        else:
            # .md and .py both use regex on text
            new_content = self._bump_text(content, old_version, new_version)

        if new_content == original:
            return {"modified": False}

        if not self.dry_run:
            file_path.write_text(new_content, encoding="utf-8")

        return {"modified": True}

    def _bump_text(self, content: str, old_version: str, new_version: str) -> str:
        """Replace version in text files (.md, .py)."""
        # Match version: "x.y.z" or version: x.y.z or version: "vX.Y.Z"
        pattern = rf'(version:\s*["']?)({re.escape(old_version)})(["']?)'
        replacement = rf'\1{new_version}\3'
        return re.sub(pattern, replacement, content)

    def _bump_json(self, content: str, old_version: str, new_version: str) -> str:
        """Replace version in JSON _meta field."""
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

        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    def _record_changelog(self, bump_type: str, new_version: str, message: str) -> bool:
        """Append entry to scripts/CHANGELOG.md."""
        try:
            self.scripts_dir.mkdir(parents=True, exist_ok=True)

            # Read existing or create new
            if self.changelog_path.exists():
                content = self.changelog_path.read_text(encoding="utf-8")
            else:
                content = "# Changelog\n\nAll notable changes to this skill will be documented in this file.\n\n"

            # Build entry
            today = datetime.utcnow().strftime("%Y-%m-%d")
            entry = f"## [{new_version}] - {today}\n\n"
            entry += f"### {bump_type.upper()}\n\n"
            entry += f"- {message}\n"
            if self.modified_files:
                entry += "- Modified files:\n"
                for mf in self.modified_files:
                    entry += f"  - `{mf['file']}`\n"
            entry += "\n"

            # Prepend to content (newest first)
            # Find position after header
            header_end = content.find("\n\n", content.find("# Changelog"))
            if header_end == -1:
                new_content = content + "\n" + entry
            else:
                new_content = content[:header_end + 2] + entry + content[header_end + 2:]

            if not self.dry_run:
                self.changelog_path.write_text(new_content, encoding="utf-8")

            return True
        except Exception as e:
            self.errors.append({
                "file": str(self.changelog_path),
                "error": f"CHANGELOG record failed: {e}",
            })
            return False


def main():
    parser = argparse.ArgumentParser(description="Version Manager for Skill Packages")
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
        print(f"\n✅ Version bumped to {result['new_version']}")
        print(f"📝 CHANGELOG updated: {result['changelog_path']}")
    elif result.get("status") == "ok" and result.get("dry_run"):
        print(f"\n🔍 DRY-RUN: Would bump to {result['new_version']}")
        print(f"   Files to modify: {result['modified_count']}")


if __name__ == "__main__":
    main()
