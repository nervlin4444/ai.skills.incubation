"""
---
title: Repo Skill Migrator
name: github-skill-organizer
description: Batch migrates github_repository fields across all files in a skill package. Replaces repo_migrator.py.
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
  local_path: scripts/repo_skill_migrator.py
  github_path: github-skill-organizer/scripts/repo_skill_migrator.py
---
"""

import sys
from pathlib import Path

try:
    from skill_organizer_config import load_config
    from core_path_utils import normalize_path
    from core_logger import log
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config
    from core_path_utils import normalize_path
    from core_logger import log


class RepoSkillMigrator:
    """
    Repository field batch migrator.
    Updates github_repository in all skill files.
    """

    def __init__(self):
        self.cfg = load_config()

    def migrate_skill(self, skill_name, new_repo, local_dir=None, dry_run=True):
        """
        Migrate all files in a skill to new github_repository.

        Args:
            skill_name: Skill directory name
            new_repo: New repo string, e.g. "nervlin4444/ai.skills.incubation"
            local_dir: Override local directory path
            dry_run: True = preview only, False = execute changes
        """
        if local_dir is None:
            local_dir = normalize_path(Path(self.cfg.user_skills_folder) / skill_name)
        else:
            local_dir = normalize_path(local_dir)

        if not local_dir.exists():
            return {"status": "error", "reason": f"Directory not found: {local_dir}"}

        files = [f for f in local_dir.rglob("*") if f.is_file()]
        changes = []

        for file_path in files:
            if file_path.name.startswith("."):
                continue

            suffix = file_path.suffix
            if suffix not in [".md", ".py", ".json", ".html"]:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            old_repo = None
            new_content = content

            if suffix == ".md" and content.startswith("---"):
                old_repo = self._extract_repo_value(content, "github_repository:")
                if old_repo:
                    new_content = content.replace(old_repo["full_line"], f"github_repository: {new_repo}")

            elif suffix == ".py":
                old_repo = self._extract_repo_value(content, "github_repository:")
                if old_repo:
                    new_content = content.replace(old_repo["full_line"], f"github_repository: {new_repo}")

            elif suffix == ".json":
                old_repo = self._extract_repo_value(content, '"github_repository"')
                if old_repo:
                    new_content = content.replace(old_repo["full_line"], f'"github_repository": "{new_repo}"')

            if old_repo and old_repo.get("value") != new_repo:
                changes.append({
                    "file": str(file_path.relative_to(local_dir)),
                    "old": old_repo.get("value"),
                    "new": new_repo,
                })
                if not dry_run:
                    file_path.write_text(new_content, encoding="utf-8")
                    log("MIGRATOR", f"Updated: {file_path.name} ({old_repo.get('value')} -> {new_repo})")

        if dry_run:
            return {
                "status": "dry_run",
                "skill_name": skill_name,
                "changes": changes,
                "total_files": len(files),
                "files_to_update": len(changes),
                "hint": "確認無誤後設置 dry_run=False 執行真實修改",
            }
        else:
            return {
                "status": "migrated",
                "skill_name": skill_name,
                "changes": changes,
                "total_files": len(files),
                "files_updated": len(changes),
            }

    def _extract_repo_value(self, content: str, key: str) -> dict | None:
        """
        Extract repository value from content.
        Returns {"value": str, "full_line": str} or None.
        """
        for line in content.splitlines():
            if key in line:
                parts = line.split(key, 1)
                if len(parts) == 2:
                    value = parts[1].strip()
                    value = value.strip('"').strip("'")
                    return {"value": value, "full_line": line}
        return None

    def migrate_all_skills(self, new_repo, dry_run=True):
        """Migrate all skills to new repo."""
        skills_dir = normalize_path(self.cfg.user_skills_folder)
        if not skills_dir.exists():
            return {"error": "Skills folder not found"}

        results = []
        for item in skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                result = self.migrate_skill(item.name, new_repo, dry_run=dry_run)
                results.append(result)

        return {
            "status": "dry_run" if dry_run else "migrated",
            "results": results,
        }


if __name__ == "__main__":
    import json
    migrator = RepoSkillMigrator()
    print(json.dumps({"status": "ready", "migrator": "initialized"}, indent=2, ensure_ascii=False))
