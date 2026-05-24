#!/usr/bin/env python3
'''
---
title: Skill Installer
name: github-skill-organizer
description: Installs new skill files from DOWNLOAD_FOLDER into USER_SKILLS_FOLDER. v1.2.0 adds _get_file_path() compatibility helper for both path and file_path keys.
version: 1.2.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-24T22:15:00+08:00
fixes: []
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: scripts/skill_installer.py
  github_path: github-skill-organizer/scripts/skill_installer.py
---
'''

import sys
import shutil
import json
import re
from pathlib import Path
from datetime import datetime, timezone

try:
    from skill_organizer_config import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config


class SkillInstaller:
    def __init__(self):
        self.cfg = load_config()
        self.archive_dir = self._get_archive_dir()

    def _get_archive_dir(self):
        download_path = Path(self.cfg.download_folder)
        archive = download_path.parent / "skills_moved"
        archive.mkdir(parents=True, exist_ok=True)
        return archive

    def _get_file_path(self, file_info: dict) -> str:
        """Compatibility: accepts both 'path' (legacy) and 'file_path' (new file_scouter)."""
        return file_info.get("path") or file_info.get("file_path") or ""

    def _validate_github_repository(self, frontmatter, source_file):
        repo_field = frontmatter.get("github_repository", "") if frontmatter else ""
        if not repo_field:
            return {
                "valid": False,
                "owner": None,
                "repo": None,
                "error": "Missing github_repository in frontmatter: " + str(source_file),
            }

        repo_field = repo_field.strip().strip("/")
        parts = repo_field.split("/")
        if len(parts) != 2:
            return {
                "valid": False,
                "owner": None,
                "repo": None,
                "error": "Invalid github_repository format. Must be owner/repo.",
            }

        owner, repo = parts[0], parts[1]
        if not owner or not repo:
            return {
                "valid": False,
                "owner": None,
                "repo": None,
                "error": "Empty owner or repo in github_repository.",
            }
        return {"valid": True, "owner": owner, "repo": repo, "error": None}

    def install_file(self, file_info):
        frontmatter = file_info.get("frontmatter", {})
        if not frontmatter or "name" not in frontmatter:
            return {"status": "unclassified", "reason": "Missing name in frontmatter"}

        source_path_str = self._get_file_path(file_info)
        if not source_path_str:
            return {"status": "error", "reason": "Missing path/file_path in file_info"}

        validation = self._validate_github_repository(frontmatter, source_path_str)
        if not validation["valid"]:
            self._log_rejected_install(file_info, validation["error"])
            return {"status": "rejected", "reason": validation["error"]}

        skill_name = frontmatter["name"]
        skill_dir = Path(self.cfg.user_skills_folder) / skill_name

        file_mapping = frontmatter.get("file_mapping", {})
        if isinstance(file_mapping, dict) and "github_path" in file_mapping:
            github_path = file_mapping["github_path"]
            github_repo = frontmatter.get("github_repository", "")
            repo_name = github_repo.split("/")[-1] if "/" in github_repo else None
            rel_path = self._derive_local_path_from_github_path(github_path, skill_name, repo_name)
        elif isinstance(file_mapping, list) and len(file_mapping) > 0:
            github_path = None
            for mapping in file_mapping:
                if isinstance(mapping, dict) and "github_path" in mapping:
                    github_path = mapping["github_path"]
                    break
            if github_path:
                github_repo = frontmatter.get("github_repository", "")
                repo_name = github_repo.split("/")[-1] if "/" in github_repo else None
                rel_path = self._derive_local_path_from_github_path(github_path, skill_name, repo_name)
            else:
                rel_path = Path(source_path_str).name
        else:
            rel_path = Path(source_path_str).name

        rel_path = self._clean_downloaded_filename(str(rel_path))
        target_path = skill_dir / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        backup = None
        if target_path.exists():
            backup_dir = skill_dir / ".backups"
            backup_dir.mkdir(exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            backup_name = f"{target_path.name}.{ts}.bak"
            backup = backup_dir / backup_name
            shutil.copy2(target_path, backup)

        try:
            shutil.copy2(source_path_str, target_path)
        except Exception as e:
            return {"status": "error", "reason": str(e)}

        archived_to = None
        try:
            source_path = Path(source_path_str)
            if source_path.exists():
                archive_subdir = self.archive_dir / skill_name
                archive_subdir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                archive_name = f"{source_path.stem}.{ts}{source_path.suffix}"
                archived_to = archive_subdir / archive_name
                shutil.move(str(source_path), str(archived_to))
                print(f"[ARCHIVE] Moved {source_path.name} -> {archived_to}")
        except Exception as e:
            print(f"[WARN] Failed to archive {source_path_str}: {e}")

        return {
            "status": "installed",
            "skill_name": skill_name,
            "target_path": str(target_path),
            "backup": str(backup) if backup else None,
            "archived_to": str(archived_to) if archived_to else None,
            "derived_from": "frontmatter" if file_mapping else "fallback",
        }

    def _derive_local_path_from_github_path(self, github_path, skill_name, repo_name=None):
        path = github_path.lstrip("/")
        parts = path.split("/")
        if repo_name and len(parts) >= 1 and parts[0] == repo_name:
            parts = parts[1:]
        if parts and parts[0] == skill_name:
            parts = parts[1:]
        return "/".join(parts) if parts else Path(github_path).name

    def _clean_downloaded_filename(self, filename):
        cleaned = re.sub(r"\s*\(\d+\)\s*(?=\.[^.]+$)", "", filename)
        cleaned = re.sub(r"\s*\(\d+\)$", "", cleaned)
        return cleaned

    def _log_rejected_install(self, file_info, reason):
        rejected_dir = Path(self.cfg.user_skills_folder).parent / "logs" / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = rejected_dir / f"install_rejected_{ts}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "original_name": file_info.get("original_name", file_info.get("file_name", "unknown")),
                "path": self._get_file_path(file_info),
                "frontmatter": file_info.get("frontmatter", {}),
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2, ensure_ascii=False)

    def install_batch(self, file_infos):
        results = []
        for fi in file_infos:
            result = self.install_file(fi)
            results.append(result)
        return results


def main():
    installer = SkillInstaller()
    test_cases = [
        {
            "file_path": "/tmp/downloads/SKILL (1).md",
            "original_name": "SKILL (1).md",
            "frontmatter": {
                "name": "test-skill",
                "github_repository": "nervlin4444/ai.skills.incubation",
                "file_mapping": {
                    "github_path": "test-skill/SKILL.md",
                    "local_path": "{baseDir}/SKILL.md"
                }
            }
        },
        {
            "path": "/tmp/downloads/bad.md",
            "original_name": "bad.md",
            "frontmatter": {
                "name": "bad-skill",
                "github_repository": "invalid-format",
                "file_mapping": {}
            }
        },
    ]
    for tc in test_cases:
        name = tc.get("original_name", tc.get("file_name", "unknown"))
        print(f"Input: {name}")
        print(json.dumps(installer.install_file(tc), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
