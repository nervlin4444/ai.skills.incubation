"""
---
title: Skill Uploader
name: github-skill-organizer
description: Handles skill upload to GitHub with auto-classification, parameter normalization, and base_path boundary exclusion. v1.0.1 fixes gate check to use unified FrontmatterExtractor.extract() for .json _meta support.
version: 1.0.1
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T00:30:00+08:00
fixes: [32]
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: scripts/skill_uploader.py
  github_path: github-skill-organizer/scripts/skill_uploader.py
---
"""

import sys
import os
import json
import subprocess
import re
import hashlib
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Core imports with fallback
try:
    from skill_organizer_config import load_config
    from core_exclude_engine import ExcludeEngine
    from core_frontmatter import FrontmatterExtractor
    from core_path_utils import normalize_path, ensure_dir
    from core_logger import log, log_error
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config
    from core_exclude_engine import ExcludeEngine
    from core_frontmatter import FrontmatterExtractor
    from core_path_utils import normalize_path, ensure_dir
    from core_logger import log, log_error


class SkillUploader:
    """
    Skill upload handler.
    Agent-friendly: auto-normalizes parameters, auto-completes classification, provides structured error codes.
    """

    def __init__(self):
        self.cfg = load_config()
        self.exclude = ExcludeEngine()
        self.token = self.cfg.get_github_token()
        self.api_base = "https://api.github.com"
        self.pending_cleanup_dir = normalize_path(
            Path(self.cfg.user_skills_folder).parent / "logs" / "pending_cleanup"
        )
        ensure_dir(self.pending_cleanup_dir)

    def upload_skill(
        self,
        skill_name: str,
        files: list = None,
        classification: dict = None,
        auto_classify: bool = True,
        dry_run: bool = False,
    ) -> dict:
        """
        Upload skill to GitHub.

        Agent-friendly parameters:
        - skill_name: str (required) - e.g. "github-skill-organizer"
        - files: None (auto-scan all) or list of str/Path
        - classification: None (auto-classify) or compare_skill return dict
        - auto_classify: bool (default True) - auto-complete incomplete classification
        - dry_run: bool (default False) - preview only, no actual upload

        Returns dict with status, error_code, hint, fix_action for agent self-repair.
        """
        # Validate skill_name
        if not skill_name or not str(skill_name).strip():
            return log_error(
                "UPLOADER", "PARAM_MISSING_SKILL_NAME",
                "skill_name is empty",
                "Provide skill directory name, e.g. skill_name='github-skill-organizer'",
                "Check local_dir path and confirm directory name"
            )

        skill_name = str(skill_name).strip()
        skill_dir = normalize_path(Path(self.cfg.user_skills_folder) / skill_name)

        if not skill_dir.exists():
            return log_error(
                "UPLOADER", "PARAM_INVALID_FILES",
                f"Skill directory not found: {skill_dir}",
                "Confirm skill_name is correct, or provide local_dir override",
                f"Check if {self.cfg.user_skills_folder}/{skill_name} exists"
            )

        # Normalize files
        files = self._normalize_files(files, skill_dir)
        if not files:
            return log_error(
                "UPLOADER", "PARAM_INVALID_FILES",
                "File list empty or all paths invalid",
                "Pass None to auto-scan all files under skill directory",
                "Confirm files parameter or change to files=None"
            )

        # Auto-complete classification
        if auto_classify:
            classification = self._ensure_classification(classification, skill_name, files)
        if not classification or "bump_type" not in classification:
            return log_error(
                "UPLOADER", "CLASSIFICATION_INCOMPLETE",
                "classification missing required fields",
                "Pass compare_skill() return value directly, system auto-calls change_classifier",
                "No need to manually call classify_change(), auto-complete is built-in"
            )

        # Check approval
        if classification.get("approval_required", False):
            return {
                "status": "pending_approval",
                "reason": classification.get("reason", "Approval required"),
                "hint": "Please review and manually set approval_required=False before retry",
                "fix_action": "Review changes, confirm correct, then re-call upload_skill()",
            }

        # Filter excluded files
        filtered_files = []
        excluded_count = 0
        for f in files:
            if self.exclude.is_excluded(f, "skill_uploader", base_path=skill_dir):
                excluded_count += 1
                log("UPLOADER", f"Excluded: {f.name}")
                continue
            filtered_files.append(f)

        if excluded_count > 0:
            log("UPLOADER", f"Excluded {excluded_count} files per config.json rules")

        if not filtered_files:
            return log_error(
                "UPLOADER", "EXCLUDE_ALL_FILES",
                "All files blocked by exclusion rules",
                "Check config.json global_excludes for false positives (e.g. .workbuddy)",
                "Verify global_excludes.prefixes does not contain '.', or adjust script_profiles boundary"
            )

        # Validate frontmatter (skip CHANGELOG)
        for f in filtered_files:
            if self.exclude.should_skip_frontmatter(f.name, "skill_uploader"):
                continue
            fm = FrontmatterExtractor.extract(f)
            if not fm or "name" not in fm:
                return log_error(
                    "UPLOADER", "FRONTMATTER_MISSING",
                    f"{f.name}: missing frontmatter (identity card)",
                    "Use skill_files_designer to regenerate files with frontmatter",
                    "Add unified frontmatter to file, or move it out of skill directory"
                )

        # Gate checks
        gate_result = self._run_gate_checks(filtered_files)
        if not gate_result["passed"]:
            return {
                "status": "rejected",
                "error_code": "GATE_CHECK_FAILED",
                "reason": gate_result["reason"],
                "hint": "Check file content for hardcoded paths or missing frontmatter",
                "fix_action": gate_result.get("fix_action", "Fix files and retry"),
            }

        if dry_run:
            return {
                "status": "dry_run",
                "skill_name": skill_name,
                "files_count": len(filtered_files),
                "files": [str(f) for f in filtered_files],
                "classification": classification,
                "hint": "This is preview mode. Set dry_run=False to execute real upload",
            }

        # Execute upload
        bump_type = classification.get("bump_type", "patch")
        new_version = classification.get("new_version", "")
        agent_name = os.getenv("AGENT_NAME", "unknown-agent")
        model_name = os.getenv("MODEL_NAME", "unknown-model")
        summary = classification.get("reason", "")

        template = self.cfg.json_config.get(
            "commit_message_template",
            "[{bump_type}] {skill_name} v{new_version} by {agent_name}({model}) - {summary}"
        )
        commit_msg = template.format(
            bump_type=bump_type.upper(), skill_name=skill_name,
            new_version=new_version, agent_name=agent_name,
            model=model_name, summary=summary,
        )

        # Read repo from SKILL.md
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return log_error(
                "UPLOADER", "PARAM_INVALID_FILES",
                f"SKILL.md not found: {skill_md}",
                "Each skill must contain SKILL.md as entry file",
                "Use skill_folder_designer to initialize skill directory structure"
            )

        fm = FrontmatterExtractor.extract(skill_md)
        repo_field = fm.get("github_repository", "") if fm else ""
        if not repo_field:
            return log_error(
                "UPLOADER", "FRONTMATTER_MISSING",
                "SKILL.md missing github_repository",
                "Add github_repository: nervlin4444/ai.skills.incubation in SKILL.md frontmatter",
                "Use skill_files_designer to fix frontmatter"
            )

        try:
            repo_name = self._extract_repo_name(repo_field)
        except ValueError as e:
            return log_error(
                "UPLOADER", "PARAM_INVALID_FILES",
                str(e),
                "github_repository must be owner/repo format",
                "Fix github_repository field in SKILL.md"
            )

        result = self._upload_via_cli(repo_name, filtered_files, commit_msg, skill_name, skill_dir)
        return {
            "status": "uploaded" if result.get("returncode") == 0 else "error",
            "commit_message": commit_msg,
            "new_version": new_version,
            "repo_name_used": repo_name,
            "details": result,
            "files_uploaded": [str(f.name) for f in filtered_files],
        }

    def _normalize_files(self, files, skill_dir: Path) -> list:
        """Normalize any input to list[Path]. Supports None, str, Path, or mixed list."""
        if files is None:
            # Auto-scan skill directory
            return [f for f in skill_dir.rglob("*") if f.is_file()]

        result = []
        for item in files:
            if isinstance(item, str):
                item = item.strip()
                # Check if relative first, before normalize_path resolves to CWD
                p = Path(item)
                if not p.is_absolute():
                    p = skill_dir / p
                p = normalize_path(p)
            elif isinstance(item, Path):
                p = item
                if not p.is_absolute():
                    p = skill_dir / p
                p = normalize_path(p)
            else:
                continue
            if p.exists():
                result.append(p)
        return result

    def _ensure_classification(self, classification, skill_name, files) -> dict:
        """Auto-complete classification if incomplete."""
        if classification is None:
            log("UPLOADER", "classification is None, auto-invoking classify_change...")
            try:
                from change_classifier import classify_change
                # Need comparison first - use skill_syncer
                from skill_syncer import SkillSyncer
                syncer = SkillSyncer()
                comparison = syncer.compare_skill(skill_name)
                return classify_change(comparison)
            except Exception as e:
                log("UPLOADER", f"Auto-classify failed: {e}", "WARN")
                return {}

        if "bump_type" not in classification or "approval_required" not in classification:
            log("UPLOADER", "classification incomplete, auto-completing...")
            try:
                from change_classifier import classify_change
                return classify_change(classification)
            except Exception as e:
                log("UPLOADER", f"Auto-complete failed: {e}", "WARN")
                return classification

        return classification

    def _extract_repo_name(self, github_repository):
        if not github_repository:
            raise ValueError("github_repository is empty")
        parts = github_repository.strip().strip("/").split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid format: {github_repository}. Must be owner/repo.")
        repo_name = parts[-1]
        if not re.match(r'^[a-zA-Z0-9_.-]+$', repo_name):
            raise ValueError(f"Invalid repo name characters: {repo_name}")
        return repo_name

    def _run_gate_checks(self, files):
        """
        Run upload gate checks.
        FIX v1.0.1: Use FrontmatterExtractor.extract() unified interface
        instead of primitive '---' string matching. Respects .json _meta field.
        """
        checks = self.cfg.json_config.get("upload_gate", {})
        if not checks.get("check_frontmatter", True):
            return {"passed": True}
        for f in files:
            if self.exclude.should_skip_frontmatter(f.name, "skill_uploader"):
                continue
            # FIX: Use unified extractor instead of primitive '---' check
            fm = FrontmatterExtractor.extract(f)
            if not fm or "name" not in fm:
                return {
                    "passed": False,
                    "reason": f"Missing frontmatter in {f.name}",
                    "fix_action": "Use skill_files_designer to add frontmatter"
                }
        if checks.get("check_hardcoded_paths", True):
            patterns = checks.get("hardcoded_path_patterns", [])
            for f in files:
                if f.suffix in [".py", ".md"]:
                    try:
                        content = f.read_text(encoding="utf-8", errors="ignore")
                        for pat in patterns:
                            if pat in content:
                                return {
                                    "passed": False,
                                    "reason": f"Hardcoded path: {pat} in {f.name}",
                                    "fix_action": "Replace hardcoded path with config-driven approach"
                                }
                    except Exception:
                        pass
        return {"passed": True}

    def _upload_via_cli(self, repo_name, files, commit_msg, skill_name, skill_dir):
        try:
            dep_path = normalize_path(self.cfg.dependency_skill_path)
            cli_script = dep_path / "scripts" / "github_repo_sync.py"
            if not cli_script.exists():
                return log_error(
                    "UPLOADER", "CLI_NOT_FOUND",
                    f"github_repo_sync.py not found at {cli_script}",
                    "Confirm github-restful-api-connector skill installed at DEPENDENCY_SKILL_PATH",
                    "Install dependency skill and verify DEPENDENCY_SKILL_PATH in .env"
                )

            clean_dir = self._create_clean_temp_dir(skill_dir)
            log("UPLOADER", f"Clean temp dir: {clean_dir}")

            cmd = [
                sys.executable, str(cli_script),
                "--repo-name", repo_name,
                "--local-dir", str(clean_dir),
                "--repo-base-path", skill_name,
                "--force"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(dep_path))

            self._record_pending_cleanup(
                clean_dir,
                f"Upload temp for {skill_name}. Safe to delete after confirming upload success."
            )

            return {
                "method": "cli",
                "status": "success" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout[:500] if result.stdout else "",
                "stderr": result.stderr[:500] if result.stderr else "",
                "clean_dir_used": str(clean_dir),
                "cleanup_status": "pending_user_confirmation",
            }
        except Exception as e:
            return log_error(
                "UPLOADER", "UPLOAD_EXCEPTION",
                str(e),
                "Unexpected error during upload",
                "Check dependency skill installation and network connection"
            )

    def _create_clean_temp_dir(self, source_dir: Path) -> Path:
        """Create temp dir with exclusion rules applied. Uses base_path boundary."""
        temp_dir = Path(tempfile.mkdtemp(prefix="sync_clean_"))
        source_dir = normalize_path(source_dir)

        for item in source_dir.rglob("*"):
            if not item.exists():
                continue
            if self.exclude.is_excluded(item, "skill_uploader", base_path=source_dir):
                continue
            rel_path = item.relative_to(source_dir)
            dest = temp_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if item.is_file():
                shutil.copy2(item, dest)

        # Log excluded directories
        excluded = []
        for item in source_dir.rglob("*"):
            if item.is_dir() and self.exclude.is_excluded(item, "skill_uploader", base_path=source_dir):
                excluded.append(str(item.relative_to(source_dir)))
        if excluded:
            log("UPLOADER", f"Skipped: {', '.join(excluded[:5])}" + ("..." if len(excluded) > 5 else ""))

        return temp_dir

    def _record_pending_cleanup(self, path: Path, reason: str):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        manifest = self.pending_cleanup_dir / f"cleanup_{ts}_{path.name}.json"
        record = {
            "path": str(path.absolute()),
            "reason": reason,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending_confirmation",
        }
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        log("UPLOADER", f"Cleanup recorded: {manifest}")


if __name__ == "__main__":
    uploader = SkillUploader()
    print(json.dumps({"status": "ready", "uploader": "initialized"}, indent=2, ensure_ascii=False))
