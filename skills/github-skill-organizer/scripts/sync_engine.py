"""
---
title: Sync Engine
name: github-skill-organizer
description: Handles bi-directional sync between local skills and GitHub. Includes upload gate, download sync, SHA-based comparison, and reverse download to arbitrary local directories. v1.0.4 adds deletion confirmation gate. v1.0.5 fixes compare_skill subdir prefix filtering and action determination — NO automatic file/directory removal without user consent.
version: 1.0.5
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  - local_path: "{baseDir}/scripts/sync_engine.py"
    github_path: "github-skill-organizer/scripts/sync_engine.py"
---
"""

import sys
import os
import json
import subprocess
import re
import hashlib
import base64
import ssl
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    from skill_organizer_config import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config


class SyncEngine:
    # EXCLUSION PATTERNS: never upload these files/directories
    UPLOAD_EXCLUDES = {
        '.backups', '.backup', '.env', '.env.local', '.git', '.github',
        'logs', 'pending_approval', '__pycache__', 'node_modules',
        '.DS_Store', 'Thumbs.db', '.vscode', '.idea',
    }
    UPLOAD_EXCLUDE_SUFFIXES = ('.pyc', '.pyo', '.so', '.zip.moved', '.bak')
    UPLOAD_EXCLUDE_PREFIXES = ('.', 'temp_', 'tmp_')

    def __init__(self):
        self.cfg = load_config()
        self.dep_scripts = self.cfg.get_dependency_import_path()
        self.github_api = None
        self._init_github_api()
        self.token = self.cfg.get_github_token()
        self.api_base = "https://api.github.com"
        self.pending_cleanup_dir = Path(self.cfg.user_skills_folder).parent / "logs" / "pending_cleanup"
        self.pending_cleanup_dir.mkdir(parents=True, exist_ok=True)

    def _init_github_api(self):
        if self.dep_scripts and Path(self.dep_scripts).exists():
            sys.path.insert(0, self.dep_scripts)
            try:
                for mod_name in ["github_repo_sync", "github_api", "github_client"]:
                    try:
                        mod = __import__(mod_name)
                        self.github_api = mod
                        print(f"[SYNC] Using imported module: {mod_name}")
                        return
                    except ImportError:
                        continue
            except Exception as e:
                print(f"[SYNC] Import failed: {e}")

        print("[SYNC] Running in CLI fallback mode")
        self.github_api = None

    def _run_dep_cli(self, args):
        dep_path = Path(self.cfg.dependency_skill_path)
        cli_script = dep_path / "scripts" / "github_repo_sync.py"
        if not cli_script.exists():
            for alt in ["sync_engine.py", "github_api.py", "upload.py"]:
                alt_path = dep_path / "scripts" / alt
                if alt_path.exists():
                    cli_script = alt_path
                    break

        if not cli_script.exists():
            raise RuntimeError(f"No CLI script found in {dep_path}/scripts/")

        cmd = [sys.executable, str(cli_script)] + args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(dep_path))
        return result

    def _github_api_call(self, endpoint, use_unverified=False):
        """Direct GitHub API call with SSL fallback for comparison operations."""
        if not self.token:
            return {"error": "No GITHUB_TOKEN available"}
        url = f"{self.api_base}{endpoint}"
        req = Request(url)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("Accept", "application/vnd.github+json")

        ctx = None
        if use_unverified:
            ctx = ssl._create_unverified_context()
            print(f"[WARN] SSL verification disabled for: {url}")

        try:
            if ctx:
                with urlopen(req, timeout=30, context=ctx) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            else:
                with urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            return {"error": True, "status": e.code, "message": str(e)}
        except URLError as e:
            err_str = str(e.reason) if hasattr(e, "reason") else str(e)
            if "CERTIFICATE_VERIFY_FAILED" in err_str and not use_unverified:
                return self._github_api_call(endpoint, use_unverified=True)
            return {"error": True, "status": 0, "message": err_str}
        except Exception as e:
            return {"error": True, "status": 0, "message": str(e)}

    # ===== DELETION CONFIRMATION GATE =====
    # CRITICAL: No file or directory shall be deleted without user consent.
    # All cleanup operations record to pending_cleanup/ and wait for approval.

    def _record_pending_cleanup(self, path: Path, reason: str, auto_approved: bool = False) -> str:
        """
        Record a path for cleanup instead of deleting immediately.
        Returns the path to the recorded manifest file.

        If auto_approved is True (for pure temp dirs like mkdtemp), 
        still records but marks as 'system_temp' for audit trail.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        manifest = self.pending_cleanup_dir / f"cleanup_{ts}_{path.name}.json"

        record = {
            "path": str(path.absolute()),
            "reason": reason,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending_confirmation" if not auto_approved else "system_temp_recorded",
            "size_bytes": self._get_path_size(path) if path.exists() else 0,
        }

        with open(manifest, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        print(f"[CLEANUP_RECORDED] {path} -> {manifest}")
        print(f"[CLEANUP_RECORDED] Reason: {reason}")
        if not auto_approved:
            print(f"[CLEANUP_PENDING] User must run cleanup_pending() or manually delete. DO NOT auto-delete.")

        return str(manifest)

    def _get_path_size(self, path: Path) -> int:
        """Get total size of a file or directory in bytes."""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return 0

    def cleanup_pending(self, confirm: bool = False, dry_run: bool = True) -> dict:
        """
        Execute or preview pending cleanup operations.

        Args:
            confirm: MUST be True to actually delete. Default False = dry-run only.
            dry_run: If True, only list what would be deleted.

        Returns:
            {"deleted": [...], "skipped": [...], "dry_run": bool}
        """
        manifests = sorted(self.pending_cleanup_dir.glob("cleanup_*.json"))
        deleted = []
        skipped = []

        for manifest in manifests:
            with open(manifest, "r", encoding="utf-8") as f:
                record = json.load(f)

            path = Path(record["path"])

            if dry_run or not confirm:
                skipped.append({
                    "path": str(path),
                    "reason": record["reason"],
                    "manifest": str(manifest),
                    "action": "skipped (dry_run or confirm=False)",
                })
                continue

            # CONFIRMED deletion
            if path.exists():
                try:
                    if path.is_file():
                        os.remove(path)
                    elif path.is_dir():
                        shutil.rmtree(path)
                    deleted.append({
                        "path": str(path),
                        "reason": record["reason"],
                        "manifest": str(manifest),
                    })
                    # Archive manifest instead of deleting it (audit trail)
                    archive_dir = self.pending_cleanup_dir / "executed"
                    archive_dir.mkdir(exist_ok=True)
                    manifest.rename(archive_dir / manifest.name)
                except Exception as e:
                    skipped.append({
                        "path": str(path),
                        "reason": f"ERROR: {e}",
                        "manifest": str(manifest),
                    })
            else:
                skipped.append({
                    "path": str(path),
                    "reason": "Path already missing",
                    "manifest": str(manifest),
                })

        return {
            "deleted": deleted,
            "skipped": skipped,
            "dry_run": dry_run or not confirm,
            "total_pending": len(manifests),
        }

    # ===== FRONTMATTER VALIDATION =====

    def _validate_github_repository(self, frontmatter, source_file):
        """
        Strict validation: github_repository must be "owner/repo" format.
        Returns: {"valid": bool, "owner": str|null, "repo": str|null, "error": str|null}
        """
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
                "error": "Invalid github_repository format in " + str(source_file) + ". Must be owner/repo.",
            }

        owner, repo = parts[0], parts[1]
        if not owner or not repo:
            return {
                "valid": False,
                "owner": None,
                "repo": None,
                "error": "Empty owner or repo in github_repository in " + str(source_file),
            }

        return {"valid": True, "owner": owner, "repo": repo, "error": None}

    # ===== REPO NAME SAFETY =====

    def _extract_repo_name(self, github_repository):
        """
        SAFETY: Extract ONLY the repo name from "owner/repo" format.
        NEVER pass the full "owner/repo" string to --repo-name.
        """
        if not github_repository:
            raise ValueError("github_repository is empty")

        parts = github_repository.strip().strip("/").split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid github_repository format: {github_repository}. Must be owner/repo.")

        repo_name = parts[-1]
        owner = parts[0]

        if not re.match(r'^[a-zA-Z0-9_.-]+$', repo_name):
            raise ValueError(f"Invalid repo name characters in: {repo_name}")

        print(f"[SAFETY] Extracted repo name: {repo_name} (owner: {owner})")
        return repo_name

    # ===== LOCAL FILE HASH =====

    def _local_file_sha(self, file_path):
        """Compute Git-compatible SHA1 hash for a local file."""
        try:
            content = Path(file_path).read_bytes()
            header = f"blob {len(content)}\0".encode()
            sha = hashlib.sha1(header + content).hexdigest()
            return sha
        except Exception:
            return None

    # ===== EXCLUSION HELPERS =====

    def _should_exclude(self, path: Path) -> bool:
        """Check if a file or directory should be excluded from upload."""
        name = path.name
        # Directory exclusion
        if path.is_dir():
            if name in self.UPLOAD_EXCLUDES:
                return True
            if any(name.startswith(p) for p in self.UPLOAD_EXCLUDE_PREFIXES):
                return True
            return False
        # File exclusion
        if name in self.UPLOAD_EXCLUDES:
            return True
        if any(name.endswith(s) for s in self.UPLOAD_EXCLUDE_SUFFIXES):
            return True
        if any(name.startswith(p) for p in self.UPLOAD_EXCLUDE_PREFIXES):
            return True
        return False

    def _create_clean_temp_dir(self, source_dir: Path) -> Path:
        """
        Create a temporary directory containing only files that should be uploaded.
        Excludes .backups, logs, pending_approval, __pycache__, .env, etc.
        Returns the path to the temporary directory.

        CRITICAL: The returned temp dir is recorded for cleanup, NOT auto-deleted.
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="sync_clean_"))
        source_dir = Path(source_dir)

        for item in source_dir.rglob("*"):
            if not item.exists():
                continue
            # Check exclusion at every level of the path
            if any(self._should_exclude(part) for part in item.relative_to(source_dir).parents):
                continue
            if self._should_exclude(item):
                continue

            rel_path = item.relative_to(source_dir)
            dest = temp_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if item.is_file():
                shutil.copy2(item, dest)

        # Log what was excluded
        excluded = []
        for item in source_dir.rglob("*"):
            if item.is_dir() and self._should_exclude(item):
                excluded.append(str(item.relative_to(source_dir)))
        if excluded:
            print(f"[EXCLUDE] Skipped directories: {', '.join(excluded[:5])}" + ("..." if len(excluded) > 5 else ""))

        return temp_dir

    # ===== COMPARISON: Local vs GitHub =====

    def compare_skill(self, skill_name, local_dir=None):
        """
        Compare local skill files with GitHub repository using SHA hashes.

        FIX v1.0.5:
        - GitHub tree API returns paths with skill subdir prefix (e.g. "skill-name/SKILL.md")
        - Local scan returns relative paths without prefix (e.g. "SKILL.md")
        - Must filter github_files to only the skill subdir and strip the prefix
        - Must also handle local_only correctly in action determination

        Returns: {"status": "ok"|"error", "owner": str, "repo": str,
                  "comparisons": [...], "action": str}
        action values: "identical", "local_ahead", "github_ahead", "diverged"
        """
        if local_dir is None:
            local_dir = Path(self.cfg.user_skills_folder) / skill_name
        else:
            local_dir = Path(local_dir)

        if not local_dir.exists():
            return {"status": "error", "reason": f"Local directory not found: {local_dir}"}

        local_skill_md = local_dir / "SKILL.md"
        if not local_skill_md.exists():
            return {"status": "error", "reason": "No local SKILL.md found"}

        fm = self._read_frontmatter_from_file(local_skill_md)
        validation = self._validate_github_repository(fm, local_skill_md)
        if not validation["valid"]:
            return {"status": "error", "reason": validation["error"]}

        owner = validation["owner"]
        repo = validation["repo"]

        tree_data = self._github_api_call(f"/repos/{owner}/{repo}/git/trees/main?recursive=1")
        if isinstance(tree_data, dict) and tree_data.get("error"):
            return {"status": "error", "reason": f"GitHub API error: {tree_data.get('message', 'unknown')}"}

        # =====================================================================
        # FIX v1.0.5: Filter github_files to ONLY the skill subdir and strip prefix
        # =====================================================================
        prefix = skill_name + "/"
        github_files = {}
        for item in tree_data.get("tree", []):
            if item["type"] != "blob":
                continue
            path = item["path"]
            # Only include files under this skill's subdirectory
            if path.startswith(prefix):
                rel_path = path[len(prefix):]
                github_files[rel_path] = item["sha"]
        # =====================================================================

        comparisons = []
        local_only = []
        github_only = []
        modified = []

        for local_file in local_dir.rglob("*"):
            if not local_file.is_file():
                continue
            if local_file.name.startswith("."):
                continue

            rel_path = str(local_file.relative_to(local_dir))
            local_sha = self._local_file_sha(local_file)
            github_sha = github_files.get(rel_path)

            if github_sha is None:
                local_only.append(rel_path)
                comparisons.append({
                    "file": rel_path,
                    "status": "local_only",
                    "local_sha": local_sha,
                    "github_sha": None,
                })
            elif local_sha == github_sha:
                comparisons.append({
                    "file": rel_path,
                    "status": "identical",
                    "sha": local_sha,
                })
            else:
                modified.append(rel_path)
                comparisons.append({
                    "file": rel_path,
                    "status": "modified",
                    "local_sha": local_sha,
                    "github_sha": github_sha,
                })

        local_rel_paths = {str(f.relative_to(local_dir)) for f in local_dir.rglob("*") if f.is_file()}
        for gh_path in github_files:
            if gh_path not in local_rel_paths:
                github_only.append(gh_path)
                comparisons.append({
                    "file": gh_path,
                    "status": "github_only",
                    "github_sha": github_files[gh_path],
                })

        # =====================================================================
        # FIX v1.0.5: Correct action determination including local_only cases
        # =====================================================================
        if not modified and not local_only and not github_only:
            action = "identical"
        elif (modified or local_only) and not github_only:
            action = "local_ahead"
        elif github_only and not modified and not local_only:
            action = "github_ahead"
        else:
            action = "diverged"
        # =====================================================================

        return {
            "status": "ok",
            "owner": owner,
            "repo": repo,
            "local_dir": str(local_dir),
            "action": action,
            "identical_count": len([c for c in comparisons if c["status"] == "identical"]),
            "modified_count": len(modified),
            "local_only_count": len(local_only),
            "github_only_count": len(github_only),
            "modified_files": modified,
            "local_only_files": local_only,
            "github_only_files": github_only,
            "comparisons": comparisons,
        }

    # ===== REVERSE DOWNLOAD: GitHub -> Local =====

    def download_from_github(self, owner, repo, target_dir, files_to_download=None):
        """
        Download files from GitHub repository to local directory.
        Overwrites existing files without backup.
        Returns: {"downloaded": [...], "failed": [...]}
        """
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        downloaded = []
        failed = []

        contents = self._github_api_call(f"/repos/{owner}/{repo}/contents?ref=main")
        if isinstance(contents, dict) and contents.get("error"):
            return {"downloaded": [], "failed": [{"error": contents.get("message", "unknown")}]}

        if not isinstance(contents, list):
            return {"downloaded": [], "failed": [{"error": "Invalid repository contents"}]}

        for item in contents:
            if item["type"] != "file":
                continue

            file_path = item["path"]

            if files_to_download and file_path not in files_to_download:
                continue

            download_url = item.get("download_url")
            if not download_url:
                failed.append({"file": file_path, "reason": "No download_url"})
                continue

            try:
                req = Request(download_url)
                req.add_header("Authorization", f"Bearer {self.token}")
                with urlopen(req, timeout=30) as resp:
                    content = resp.read()

                local_file = target_path / file_path
                local_file.parent.mkdir(parents=True, exist_ok=True)
                local_file.write_bytes(content)
                downloaded.append(file_path)

            except Exception as e:
                failed.append({"file": file_path, "reason": str(e)})

        return {"downloaded": downloaded, "failed": failed}

    def sync_skill(self, skill_name, local_dir=None, dry_run=True):
        """
        Full sync: compare local with GitHub, then download if GitHub is ahead.
        Returns: {"status": str, "details": dict}
        """
        comparison = self.compare_skill(skill_name, local_dir)
        if comparison["status"] != "ok":
            return comparison

        action = comparison["action"]

        if action == "identical":
            return {"status": "ok", "action": "identical", "message": "Local and GitHub are identical"}

        if action == "local_ahead":
            return {"status": "ok", "action": "local_ahead", "message": "Local is ahead of GitHub. Use upload to sync."}

        if action in ("github_ahead", "diverged"):
            if dry_run:
                return {
                    "status": "ok",
                    "action": action,
                    "dry_run": True,
                    "message": f"GitHub is ahead. Would download {len(comparison['github_only_files'])} new files and overwrite {len(comparison['modified_files'])} modified files.",
                    "github_only_files": comparison["github_only_files"],
                    "modified_files": comparison["modified_files"],
                }

            owner = comparison["owner"]
            repo = comparison["repo"]
            target = Path(comparison["local_dir"])

            result = self.download_from_github(owner, repo, target)

            return {
                "status": "ok",
                "action": "downloaded",
                "downloaded": result["downloaded"],
                "failed": result["failed"],
            }

        return {"status": "error", "reason": f"Unknown action: {action}"}

    def download_all_skills(self):
        """Pull latest skills from GitHub to local skills folder."""
        results = {}
        try:
            config_path = Path(__file__).parent.parent / "config" / "sync.config.json"
            if config_path.exists():
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                skill_name = config.get("skill_name", "github-skill-organizer")
            else:
                skill_name = "github-skill-organizer"

            owner = self.cfg.get_github_owner()
            if not owner:
                return {"error": "Cannot determine GitHub owner"}

            skill_dir = Path(self.cfg.user_skills_folder) / skill_name
            if skill_dir.exists():
                result = self.sync_skill(skill_name, str(skill_dir), dry_run=False)
                results[skill_name] = result
        except Exception as e:
            results["error"] = str(e)

        return results

    # ===== UPLOAD (existing) =====

    def upload_skill(self, skill_name, files, classification):
        """Upload changed files to GitHub. Delegates all API calls to dependency skill."""
        if classification["approval_required"]:
            self._move_to_pending(skill_name, files, classification)
            return {"status": "pending_approval", "reason": classification["reason"]}

        # FIX v1.0.5: Only validate from SKILL.md, not every file
        fm = None
        for f in files:
            if Path(f).name == "SKILL.md":
                fm = self._read_frontmatter_from_file(f)
                break
        if fm is None:
            fm = {}  # Default empty frontmatter
        validation = self._validate_github_repository(fm, "SKILL.md")
        if not validation["valid"]:
            self._log_rejected(skill_name, files, validation)
            return {"status": "rejected", "reason": validation["error"]}

        gate_result = self._run_gate_checks(files)
        if not gate_result["passed"]:
            self._log_rejected(skill_name, files, gate_result)
            return {"status": "rejected", "reason": gate_result["reason"]}

        bump_type = classification["bump_type"]
        new_version = classification["new_version"]
        agent_name = os.getenv("AGENT_NAME", "unknown-agent")
        model_name = os.getenv("MODEL_NAME", "unknown-model")
        summary = classification["reason"]

        template = self.cfg.json_config.get("commit_message_template",
            "[{bump_type}] {skill_name} v{new_version} by {agent_name}({model}) - {summary}")

        commit_msg = template.format(
            bump_type=bump_type.upper(),
            skill_name=skill_name,
            new_version=new_version,
            agent_name=agent_name,
            model=model_name,
            summary=summary,
        )

        # FIX: Use the already-parsed fm from SKILL.md above (lines 626-631), not files[0]
        try:
            repo_name = self._extract_repo_name(fm.get("github_repository", ""))
        except ValueError as e:
            return {"status": "rejected", "reason": str(e)}

        # FIX: When github_api module is available, use CLI (which uses the module internally)
        # _upload_via_api is a placeholder, _upload_via_cli does the actual work
        if self.github_api:
            result = self._upload_via_cli(repo_name, files, commit_msg, skill_name)
        else:
            # Fallback: try direct API methods if available, otherwise fail
            result = {"method": "api", "status": "error", "reason": "No github_api module available"}

        return {
            "status": "uploaded",
            "commit_message": commit_msg,
            "new_version": new_version,
            "repo_name_used": repo_name,
            "details": result,
        }

    def _read_frontmatter_from_file(self, file_path):
        """Extract frontmatter from an installed file."""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    return self._parse_simple_yaml(content[3:end])
            if Path(file_path).suffix == ".py":
                match = re.search(r'"""\s*---\s*(.*?)\s*---\s*"""', content, re.DOTALL)
                if match:
                    return self._parse_simple_yaml(match.group(1))
        except Exception:
            pass
        return {}

    def _parse_simple_yaml(self, yaml_text):
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
        return result

    def _run_gate_checks(self, files):
        checks = self.cfg.json_config.get("upload_gate", {})
        if not checks.get("check_frontmatter", True):
            return {"passed": True}

        # FIX v1.0.5: Only check frontmatter in SKILL.md
        skill_md_found = False
        for f in files:
            p = Path(f)
            if p.name == "SKILL.md":
                skill_md_found = True
                if p.suffix in [".md", ".py", ".json"]:
                    try:
                        content = p.read_text(encoding="utf-8", errors="ignore")
                        if "---" not in content:
                            return {"passed": False, "reason": f"Missing frontmatter in {p.name}"}
                    except Exception:
                        pass
                break

        if checks.get("check_hardcoded_paths", True):
            patterns = checks.get("hardcoded_path_patterns", [])
            for f in files:
                if Path(f).suffix in [".py", ".md"]:
                    try:
                        content = Path(f).read_text(encoding="utf-8", errors="ignore")
                        for pat in patterns:
                            if pat in content:
                                return {"passed": False, "reason": f"Hardcoded path detected: {pat} in {f}"}
                    except Exception:
                        pass

        return {"passed": True}

    def _move_to_pending(self, skill_name, files, classification):
        pending_dir = Path(self.cfg.user_skills_folder).parent / "pending_approval"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        batch_dir = pending_dir / f"{skill_name}_{ts}"
        batch_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "skill_name": skill_name,
            "classification": classification,
            "files": [str(f) for f in files],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(batch_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        for f in files:
            src = Path(f)
            dst = batch_dir / src.name
            dst.write_bytes(src.read_bytes())

        print(f"[PENDING] Moved {len(files)} files to {batch_dir}")

    def _log_rejected(self, skill_name, files, gate_result):
        rejected_dir = Path(self.cfg.user_skills_folder).parent / "logs" / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        log_file = rejected_dir / f"{skill_name}_{ts}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump({
                "skill_name": skill_name,
                "files": [str(f) for f in files],
                "reason": gate_result.get("error") or gate_result.get("reason"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2, ensure_ascii=False)

    def _upload_via_api(self, repo_name, files, commit_msg, skill_name=None):
        return {"method": "api", "status": "placeholder", "repo_name": repo_name}

    def _upload_via_cli(self, repo_name, files, commit_msg, skill_name=None):
        """
        Call github_repo_sync.py via CLI with CORRECT parameters.
        CRITICAL v1.0.4: Creates clean temp dir excluding dev artifacts.
        NO automatic deletion — temp dir recorded for user-confirmed cleanup.
        """
        try:
            dep_path = Path(self.cfg.dependency_skill_path)
            cli_script = dep_path / "scripts" / "github_repo_sync.py"
            if not cli_script.exists():
                return {"method": "cli", "status": "error", "reason": "github_repo_sync.py not found"}

            # FIX: files is a list of strings (paths). Must wrap in Path() before accessing .parent
            if files:
                local_dir = Path(files[0]).parent.parent
            else:
                local_dir = self.cfg.user_skills_folder / (skill_name or repo_name)
            skill_dir_name = Path(str(local_dir)).name  # e.g., "github-skill-organizer"

            # CRITICAL FIX v1.0.3: Create clean temp dir excluding development artifacts
            print(f"[UPLOAD] Creating clean temp dir from {local_dir}...")
            clean_dir = self._create_clean_temp_dir(local_dir)
            print(f"[UPLOAD] Clean temp dir: {clean_dir}")

            cmd = [
                sys.executable, str(cli_script),
                "--repo-name", repo_name,
                "--local-dir", str(clean_dir),
                "--repo-base-path", skill_dir_name,
                "--force",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(dep_path))

            # CRITICAL v1.0.4: NO automatic deletion. Record for user-confirmed cleanup.
            self._record_pending_cleanup(
                clean_dir,
                f"Upload temp dir for {skill_name or repo_name}. Safe to delete after confirming upload success.",
                auto_approved=False,
            )
            print(f"[UPLOAD] Temp dir preserved for audit. Run cleanup_pending(confirm=True) to delete after verifying upload.")

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
            return {"method": "cli", "status": "error", "reason": str(e)}


if __name__ == "__main__":
    engine = SyncEngine()
    print(json.dumps(engine.cfg.to_dict(), indent=2, ensure_ascii=False))
