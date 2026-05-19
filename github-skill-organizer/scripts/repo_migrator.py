"""
---
title: Repository Migrator
name: github-skill-organizer
description: Batch migrates github_repository field across all files in a skill package. Supports dry-run, frontmatter/docstring/_meta formats, and automatic version bump.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/repo_migrator.py"
  github_path: "github-skill-organizer/scripts/repo_migrator.py"
---
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime


class RepoMigrator:
    """
    Batch migrates github_repository field in all skill files.
    Supports .md (YAML frontmatter), .py (docstring YAML), .json (_meta field).
    """

    def __init__(self, skill_dir: str, old_repo: str, new_repo: str, dry_run: bool = True):
        self.skill_dir = Path(skill_dir).resolve()
        self.old_repo = old_repo.strip().strip("/")
        self.new_repo = new_repo.strip().strip("/")
        self.dry_run = dry_run
        self.modified_files = []
        self.skipped_files = []
        self.errors = []

    def migrate(self) -> dict:
        """
        Scan all files in skill directory and migrate github_repository.
        Returns: {"modified": [...], "skipped": [...], "errors": [...]}
        """
        if not self.skill_dir.exists():
            return {"error": f"Skill directory not found: {self.skill_dir}"}

        for file_path in self._scan_files():
            try:
                result = self._migrate_file(file_path)
                if result["modified"]:
                    self.modified_files.append({
                        "file": str(file_path.relative_to(self.skill_dir)),
                        "old_value": result["old_value"],
                        "new_value": result["new_value"],
                    })
                else:
                    self.skipped_files.append(str(file_path.relative_to(self.skill_dir)))
            except Exception as e:
                self.errors.append({
                    "file": str(file_path.relative_to(self.skill_dir)),
                    "error": str(e),
                })

        # Auto-bump version if any files modified
        version_bumped = False
        if self.modified_files and not self.dry_run:
            version_bumped = self._bump_version()

        return {
            "dry_run": self.dry_run,
            "skill_dir": str(self.skill_dir),
            "old_repo": self.old_repo,
            "new_repo": self.new_repo,
            "modified_count": len(self.modified_files),
            "modified_files": self.modified_files,
            "skipped_count": len(self.skipped_files),
            "skipped_files": self.skipped_files,
            "error_count": len(self.errors),
            "errors": self.errors,
            "version_bumped": version_bumped,
        }

    def _scan_files(self):
        """Yield all relevant files in skill directory."""
        for pattern in ["**/*.md", "**/*.py", "**/*.json"]:
            for file_path in self.skill_dir.glob(pattern):
                if file_path.is_file() and not file_path.name.startswith("."):
                    yield file_path

    def _migrate_file(self, file_path: Path) -> dict:
        """
        Migrate a single file. Returns: {"modified": bool, "old_value": str|null, "new_value": str|null}
        """
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        original_content = content

        # Detect file type and extract frontmatter region
        if file_path.suffix == ".md":
            new_content = self._migrate_md(content)
        elif file_path.suffix == ".py":
            new_content = self._migrate_py(content)
        elif file_path.suffix == ".json":
            new_content = self._migrate_json(content)
        else:
            return {"modified": False, "old_value": None, "new_value": None}

        if new_content == original_content:
            return {"modified": False, "old_value": None, "new_value": None}

        # Extract old value for reporting
        old_value = self._extract_old_repo(original_content, file_path.suffix)

        if not self.dry_run:
            file_path.write_text(new_content, encoding="utf-8")

        return {"modified": True, "old_value": old_value, "new_value": self.new_repo}

    def _migrate_md(self, content: str) -> str:
        """Migrate YAML frontmatter in .md files."""
        if not content.startswith("---"):
            return content

        end = content.find("---", 3)
        if end == -1:
            return content

        frontmatter = content[3:end]
        new_frontmatter = self._replace_repo_in_yaml(frontmatter)
        return content[:3] + new_frontmatter + content[end:]

    def _migrate_py(self, content: str) -> str:
        """Migrate docstring YAML block in .py files."""
        match = re.search(r'"""\s*---\s*(.*?)\s*---\s*"""', content, re.DOTALL)
        if not match:
            return content

        frontmatter = match.group(1)
        new_frontmatter = self._replace_repo_in_yaml(frontmatter)
        return content[:match.start(1)] + new_frontmatter + content[match.end(1):]

    def _migrate_json(self, content: str) -> str:
        """Migrate _meta.github_repository in .json files."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return content

        if "_meta" in data and "github_repository" in data["_meta"]:
            if data["_meta"]["github_repository"] == self.old_repo:
                data["_meta"]["github_repository"] = self.new_repo
                return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

        return content

    def _replace_repo_in_yaml(self, yaml_text: str) -> str:
        """Replace github_repository value in YAML text."""
        # Match github_repository line with various quote styles
        pattern = r'^(github_repository:\s*)(["']?)(' + re.escape(self.old_repo) + r')()(\s*)$'
        replacement = r'\1\2' + self.new_repo + r'\2\4'
        return re.sub(pattern, replacement, yaml_text, flags=re.MULTILINE)

    def _extract_old_repo(self, content: str, suffix: str) -> str:
        """Extract the old github_repository value from content."""
        if suffix == ".json":
            try:
                data = json.loads(content)
                if "_meta" in data:
                    return data["_meta"].get("github_repository", "")
            except Exception:
                pass
        else:
            match = re.search(r'github_repository:\s*["']?([^"'\n]+)["']?', content)
            if match:
                return match.group(1)
        return ""

    def _bump_version(self) -> bool:
        """Auto-bump patch version in SKILL.md or the first .md file found."""
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            md_files = list(self.skill_dir.glob("*.md"))
            if md_files:
                skill_md = md_files[0]
            else:
                return False

        try:
            content = skill_md.read_text(encoding="utf-8")
            # Match version: "x.y.z" or version: x.y.z
            match = re.search(r'(version:\s*["']?)(\d+)\.(\d+)\.(\d+)(["']?)', content)
            if match:
                major, minor, patch = int(match.group(2)), int(match.group(3)), int(match.group(4))
                new_version = f"{major}.{minor}.{patch + 1}"
                new_content = content[:match.start(2)] + new_version + content[match.end(5):]
                if not self.dry_run:
                    skill_md.write_text(new_content, encoding="utf-8")
                self.modified_files.append({
                    "file": str(skill_md.relative_to(self.skill_dir)),
                    "old_value": f"{major}.{minor}.{patch}",
                    "new_value": new_version,
                    "note": "auto-bump patch version",
                })
                return True
        except Exception as e:
            self.errors.append({
                "file": str(skill_md.relative_to(self.skill_dir)),
                "error": f"Version bump failed: {e}",
            })
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Batch migrate github_repository in a skill package"
    )
    parser.add_argument("--skill-dir", required=True, help="Path to skill directory")
    parser.add_argument("--old-repo", required=True, help="Old repository, e.g. nervlin4444/ai.skills.incubation")
    parser.add_argument("--new-repo", required=True, help="New repository, e.g. nervlin4444/ai.skills.devops")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview changes without writing (default: true)")
    parser.add_argument("--apply", action="store_true",
                        help="Apply changes (disables dry-run)")

    args = parser.parse_args()

    dry_run = not args.apply

    migrator = RepoMigrator(
        skill_dir=args.skill_dir,
        old_repo=args.old_repo,
        new_repo=args.new_repo,
        dry_run=dry_run,
    )

    result = migrator.migrate()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Exit code: 0 if no errors, 1 if errors occurred
    if result.get("error_count", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
