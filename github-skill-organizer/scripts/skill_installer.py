"""
---
title: Skill Installer
name: github-skill-organizer
description: Installs new skill files from DOWNLOAD_FOLDER into USER_SKILLS_FOLDER. All scanned files are MOVED out of download folder regardless of install status: identical -> .identical/, skipped -> .skipped/, rejected -> .rejected/, unclassified -> .unclassified/. Only newer AND different files are actually installed.
version: 1.0.4
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  - local_path: "{baseDir}/scripts/skill_installer.py"
    github_path: "github-skill-organizer/scripts/skill_installer.py"
---
"""

import sys
import shutil
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone

try:
    from skill_organizer_config import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config


class SkillInstaller:
    """
    Installs skill files from DOWNLOAD_FOLDER to USER_SKILLS_FOLDER.
    CRITICAL RULE: Every file scanned by local_scanner.py MUST be moved
    out of DOWNLOAD_FOLDER, regardless of install outcome.

    Archive destinations:
    - installed -> skills_moved/{skill_name}/
    - identical -> skills_moved/.identical/
    - skipped -> skills_moved/.skipped/
    - rejected -> skills_moved/.rejected/
    - unclassified -> skills_moved/.unclassified/
    """

    def __init__(self):
        self.cfg = load_config()
        self.archive_dir = self._get_archive_dir()

    def _get_archive_dir(self):
        download_path = Path(self.cfg.download_folder)
        archive = download_path.parent / "skills_moved"
        archive.mkdir(parents=True, exist_ok=True)
        return archive

    def _validate_github_repository(self, frontmatter, source_file):
        repo_field = frontmatter.get("github_repository", "") if frontmatter else ""
        if not repo_field:
            return {
                "valid": False, "owner": None, "repo": None,
                "error": "Missing github_repository in frontmatter: " + str(source_file),
            }
        repo_field = repo_field.strip().strip("/")
        parts = repo_field.split("/")
        if len(parts) != 2:
            return {
                "valid": False, "owner": None, "repo": None,
                "error": "Invalid github_repository format in " + str(source_file) + ". Must be owner/repo.",
            }
        owner, repo = parts[0], parts[1]
        if not owner or not repo:
            return {
                "valid": False, "owner": None, "repo": None,
                "error": "Empty owner or repo in github_repository in " + str(source_file),
            }
        return {"valid": True, "owner": owner, "repo": repo, "error": None}

    def _file_hash(self, file_path: Path) -> str:
        try:
            return hashlib.sha256(file_path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def _archive_file(self, source_path: Path, subdir_name: str, reason: str = "") -> str:
        """
        Move a file from download folder to skills_moved/{subdir_name}/.
        Returns the archived path.
        """
        try:
            archive_subdir = self.archive_dir / subdir_name
            archive_subdir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            archive_name = f"{source_path.stem}.{ts}{source_path.suffix}"
            archived_to = archive_subdir / archive_name
            shutil.move(str(source_path), str(archived_to))
            if reason:
                print(f"[ARCHIVE] {source_path.name} -> {archived_to} ({reason})")
            else:
                print(f"[ARCHIVE] {source_path.name} -> {archived_to}")
            return str(archived_to)
        except Exception as e:
            print(f"[WARN] Failed to archive {source_path}: {e}")
            return ""

    def install_file(self, file_info):
        """
        file_info: dict from local_scanner
        Returns: {"status": "installed"|"identical"|"skipped"|"rejected"|"unclassified"|"error", ...}

        ALL outcomes move the source file out of download folder.
        """
        source_path = Path(file_info["path"])
        frontmatter = file_info.get("frontmatter", {})

        # === OUTCOME: Unclassified (no frontmatter or no name) ===
        if not frontmatter or "name" not in frontmatter:
            archived_to = self._archive_file(source_path, ".unclassified", "no frontmatter/name")
            return {
                "status": "unclassified",
                "reason": "Missing name in frontmatter",
                "archived_to": archived_to,
            }

        # === OUTCOME: Rejected (invalid github_repository) ===
        validation = self._validate_github_repository(frontmatter, file_info.get("path", "unknown"))
        if not validation["valid"]:
            self._log_rejected_install(file_info, validation["error"])
            archived_to = self._archive_file(source_path, ".rejected", validation["error"])
            return {
                "status": "rejected",
                "reason": validation["error"],
                "archived_to": archived_to,
            }

        skill_name = frontmatter["name"]
        skill_dir = Path(self.cfg.user_skills_folder) / skill_name

        # Determine target path
        file_mapping = frontmatter.get("file_mapping", {})
        if isinstance(file_mapping, dict) and "github_path" in file_mapping:
            github_path = file_mapping["github_path"]
            rel_path = self._derive_local_path_from_github_path(github_path, skill_name)
        elif isinstance(file_mapping, list) and len(file_mapping) > 0:
            github_path = None
            for mapping in file_mapping:
                if isinstance(mapping, dict) and "github_path" in mapping:
                    github_path = mapping["github_path"]
                    break
            if github_path:
                rel_path = self._derive_local_path_from_github_path(github_path, skill_name)
            else:
                rel_path = Path(file_info["path"]).name
        else:
            rel_path = Path(file_info["path"]).name

        rel_path = self._clean_downloaded_filename(str(rel_path))
        target_path = skill_dir / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # === OUTCOME: Identical (content same, target exists) ===
        if target_path.exists():
            source_hash = self._file_hash(source_path)
            target_hash = self._file_hash(target_path)
            if source_hash and target_hash and source_hash == target_hash:
                archived_to = self._archive_file(source_path, ".identical", f"same as {target_path.name}")
                return {
                    "status": "identical",
                    "skill_name": skill_name,
                    "target_path": str(target_path),
                    "reason": "Content identical, no update needed",
                    "archived_to": archived_to,
                }

        # === OUTCOME: Skipped (target is newer or same age) ===
        if target_path.exists():
            source_mtime = source_path.stat().st_mtime
            target_mtime = target_path.stat().st_mtime
            if target_mtime >= source_mtime:
                archived_to = self._archive_file(source_path, ".skipped", f"target newer: {target_path.name}")
                return {
                    "status": "skipped",
                    "skill_name": skill_name,
                    "target_path": str(target_path),
                    "reason": f"Target file is newer or same age (target: {target_mtime}, source: {source_mtime})",
                    "archived_to": archived_to,
                }

        # === OUTCOME: Installed (source is newer AND content differs) ===
        backup = None
        if target_path.exists():
            # FIX: use .backups (plural) to match sync_engine.py skip logic
            backup_dir = skill_dir / ".backups"
            backup_dir.mkdir(exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            backup_name = f"{target_path.name}.{ts}.bak"
            backup = backup_dir / backup_name
            shutil.copy2(target_path, backup)

        try:
            shutil.copy2(file_info["path"], target_path)
        except Exception as e:
            return {"status": "error", "reason": str(e)}

        # Archive source file after successful install
        archived_to = self._archive_file(source_path, skill_name, "installed")

        return {
            "status": "installed",
            "skill_name": skill_name,
            "target_path": str(target_path),
            "backup": str(backup) if backup else None,
            "archived_to": archived_to,
            "derived_from": "frontmatter" if file_mapping else "fallback",
        }

    def _derive_local_path_from_github_path(self, github_path, skill_name):
        path = github_path.lstrip("/")
        parts = path.split("/")
        if parts and parts[0] == skill_name:
            parts = parts[1:]
        return "/".join(parts) if parts else Path(github_path).name

    def _clean_downloaded_filename(self, filename):
        cleaned = re.sub(r'\s*\(\d+\)\s*(?=\.[^.]+$)', "", filename)
        cleaned = re.sub(r'\s*\(\d+\)$', "", cleaned)
        return cleaned

    def _log_rejected_install(self, file_info, reason):
        rejected_dir = Path(self.cfg.user_skills_folder).parent / "logs" / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = rejected_dir / f"install_rejected_{ts}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump({
                "original_name": file_info.get("original_name", "unknown"),
                "path": file_info.get("path", "unknown"),
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


if __name__ == "__main__":
    installer = SkillInstaller()
    print(json.dumps({
        "status": "ready",
        "archive_dir": str(installer.archive_dir),
        "user_skills_folder": str(installer.cfg.user_skills_folder),
        "download_folder": str(installer.cfg.download_folder),
    }, indent=2, ensure_ascii=False))
