"""
---
title: Skill Syncer
name: github-skill-organizer
description: Handles compare and download operations between local skills and GitHub. v1.2.1 adds download authorization: when local file mtime is newer than GitHub last commit date, requires user approval before overwrite.
version: "1.2.1"
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: "2026-05-26T01:15:00+08:00"
fixes: []
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: scripts/skill_syncer.py
  github_path: github-skill-organizer/scripts/skill_syncer.py
---
"""

import sys
import json
import hashlib
import base64
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    from skill_organizer_config import load_config
    from core_frontmatter import FrontmatterExtractor
    from core_path_utils import normalize_path
    from core_logger import log, log_error
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config
    from core_frontmatter import FrontmatterExtractor
    from core_path_utils import normalize_path
    from core_logger import log, log_error


class SkillSyncer:
    """
    Skill comparison and download handler.
    Separated from upload logic for clarity.
    v1.2.1: Added download authorization based on file date comparison.
    """

    def __init__(self):
        self.cfg = load_config()
        self.token = self.cfg.get_github_token()
        self.api_base = "https://api.github.com"

    def compare_skill(self, skill_name, local_dir=None):
        """
        Compare local skill directory with GitHub repository.
        Returns comparison dict with action, modified_files, local_only_files, etc.
        """
        if local_dir is None:
            local_dir = normalize_path(Path(self.cfg.user_skills_folder) / skill_name)
        else:
            local_dir = normalize_path(local_dir)

        if not local_dir.exists():
            return {"status": "error", "reason": f"Local directory not found: {local_dir}"}

        local_skill_md = local_dir / "SKILL.md"
        if not local_skill_md.exists():
            return {"status": "error", "reason": "No local SKILL.md found"}

        fm = FrontmatterExtractor.extract(local_skill_md)
        validation = self._validate_repo(fm, local_skill_md)
        if not validation["valid"]:
            return {"status": "error", "reason": validation["error"]}

        owner = validation["owner"]
        repo = validation["repo"]

        tree_data = self._github_api_call(f"/repos/{owner}/{repo}/git/trees/main?recursive=1")
        if isinstance(tree_data, dict) and tree_data.get("error"):
            return {"status": "error", "reason": f"GitHub API error: {tree_data.get('message', 'unknown')}"}

        prefix = skill_name + "/"
        github_files = {}
        for item in tree_data.get("tree", []):
            if item["type"] != "blob":
                continue
            path = item["path"]
            if path.startswith(prefix):
                rel_path = path[len(prefix):]
                github_files[rel_path] = item["sha"]

        comparisons = []
        local_only = []
        modified = []
        github_only = []

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
                comparisons.append({"file": rel_path, "status": "local_only", "local_sha": local_sha, "github_sha": None})
            elif local_sha == github_sha:
                comparisons.append({"file": rel_path, "status": "identical", "sha": local_sha})
            else:
                modified.append(rel_path)
                comparisons.append({"file": rel_path, "status": "modified", "local_sha": local_sha, "github_sha": github_sha})

        local_rel_paths = {str(f.relative_to(local_dir)) for f in local_dir.rglob("*") if f.is_file()}
        for gh_path in github_files:
            if gh_path not in local_rel_paths:
                github_only.append(gh_path)
                comparisons.append({"file": gh_path, "status": "github_only", "github_sha": github_files[gh_path]})

        if not modified and not local_only and not github_only:
            action = "identical"
        elif (modified or local_only) and not github_only:
            action = "local_ahead"
        elif github_only and not modified and not local_only:
            action = "github_ahead"
        else:
            action = "diverged"

        return {
            "status": "ok",
            "action": action,
            "owner": owner,
            "repo": repo,
            "local_dir": str(local_dir),
            "modified_files": modified,
            "local_only_files": local_only,
            "github_only_files": github_only,
            "modified_count": len(modified),
            "local_only_count": len(local_only),
            "github_only_count": len(github_only),
            "comparisons": comparisons,
        }

    def download_from_github(self, owner, repo, target_dir, files_to_download=None, force=False):
        """
        Download files from GitHub repository to local directory.

        v1.2.1 CHANGE: Added authorization check. If local file mtime is newer
        than GitHub last commit date, requires user approval (force=True) to overwrite.

        Args:
            owner: GitHub repository owner
            repo: GitHub repository name
            target_dir: Local directory to download to
            files_to_download: Optional list of specific files to download
            force: If True, skip authorization check and overwrite local files

        Returns:
            dict with status, downloaded list, failed list, or pending_approval info
        """
        target_path = normalize_path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        downloaded = []
        failed = []
        needs_approval = []
        skipped = []

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

            local_file = target_path / file_path

            # v1.2.1: Authorization check - compare local mtime with GitHub commit date
            if local_file.exists() and not force:
                local_mtime = local_file.stat().st_mtime
                github_date = self._get_github_file_date(owner, repo, file_path)

                if github_date:
                    local_dt = datetime.fromtimestamp(local_mtime, tz=timezone.utc)
                    if local_dt > github_date:
                        needs_approval.append({
                            "file": file_path,
                            "local_mtime": local_dt.isoformat(),
                            "github_date": github_date.isoformat(),
                            "reason": "Local file is newer than GitHub version. User approval required to overwrite."
                        })
                        skipped.append(file_path)
                        continue  # Skip download, wait for user approval

            # Proceed with download
            try:
                req = Request(download_url)
                req.add_header("Authorization", f"Bearer {self.token}")
                with urlopen(req, timeout=30) as resp:
                    content = resp.read()
                local_file.parent.mkdir(parents=True, exist_ok=True)
                local_file.write_bytes(content)
                downloaded.append(file_path)
            except Exception as e:
                failed.append({"file": file_path, "reason": str(e)})

        # If any files need approval, return pending_approval status
        if needs_approval and not force:
            return {
                "status": "pending_approval",
                "reason": f"{len(needs_approval)} local file(s) are newer than GitHub versions",
                "needs_approval": needs_approval,
                "downloaded": downloaded,
                "skipped": skipped,
                "failed": failed,
                "hint": "Review the files above. If you want to overwrite local files with GitHub versions, call download_from_github(..., force=True)",
                "fix_action": "Call download_from_github(..., force=True) after user confirms overwrite",
            }

        return {"downloaded": downloaded, "failed": failed}

    def _get_github_file_date(self, owner, repo, file_path):
        """
        Get the last commit date for a specific file on GitHub.
        Returns datetime in UTC, or None if unable to fetch.
        """
        try:
            commits_data = self._github_api_call(
                f"/repos/{owner}/{repo}/commits?path={file_path}&per_page=1"
            )
            if isinstance(commits_data, list) and len(commits_data) > 0:
                commit_date_str = commits_data[0].get("commit", {}).get("committer", {}).get("date")
                if commit_date_str:
                    # Parse ISO 8601 format: 2026-05-24T20:14:00Z
                    return datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
        except Exception as e:
            log("SYNCER", f"Failed to get GitHub date for {file_path}: {e}", "WARN")
        return None

    def sync_changelog(self, skill_name, local_dir=None):
        """Sync CHANGELOG.md frontmatter between local and GitHub."""
        if local_dir is None:
            local_dir = normalize_path(Path(self.cfg.user_skills_folder) / skill_name)
        else:
            local_dir = normalize_path(local_dir)

        local_changelog = local_dir / "CHANGELOG.md"
        if not local_changelog.exists():
            return {"status": "error", "reason": "Local CHANGELOG.md not found"}

        comparison = self.compare_skill(skill_name, local_dir)
        if comparison["status"] != "ok":
            return comparison

        owner = comparison["owner"]
        repo = comparison["repo"]
        prefix = skill_name + "/"

        changelog_api = self._github_api_call(f"/repos/{owner}/{repo}/contents/{prefix}CHANGELOG.md?ref=main")
        if isinstance(changelog_api, dict) and changelog_api.get("error"):
            return {"status": "error", "reason": "Cannot fetch remote CHANGELOG.md"}

        remote_content = base64.b64decode(changelog_api.get("content", "")).decode("utf-8")
        local_content = local_changelog.read_text(encoding="utf-8", errors="ignore")

        local_has_fm = local_content.startswith("---")
        remote_has_fm = remote_content.startswith("---")

        if not local_has_fm and remote_has_fm:
            local_changelog.write_text(remote_content, encoding="utf-8")
            return {"status": "synced", "action": "downloaded", "message": "CHANGELOG.md synced from GitHub"}
        elif local_has_fm and not remote_has_fm:
            return {"status": "pending_upload", "action": "local_ahead", "message": "Local has frontmatter, remote does not"}
        elif local_content == remote_content:
            return {"status": "identical", "action": "identical", "message": "CHANGELOG.md identical"}
        else:
            return {"status": "diverged", "action": "diverged", "message": "CHANGELOG.md differs, manual review required"}

    def download_all_skills(self):
        """Download all configured skills from GitHub.
        Returns dict where ALL values are dicts (never strings), safe for daemon iteration.
        """
        results = {}
        try:
            config_path = Path(__file__).parent.parent / "config" / "sync.config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                skill_name = config.get("skill_name", "github-skill-organizer")
            else:
                skill_name = "github-skill-organizer"
            owner = self.cfg.get_github_owner()
            if not owner:
                results[skill_name] = {"status": "error", "reason": "Cannot determine GitHub owner"}
                return results
            skill_dir = normalize_path(Path(self.cfg.user_skills_folder) / skill_name)
            if not skill_dir.exists():
                results[skill_name] = {"status": "not_found", "reason": f"Skill directory not found: {skill_dir}"}
                return results
            comparison = self.compare_skill(skill_name, str(skill_dir))
            if comparison["status"] == "ok" and comparison["action"] in ("github_ahead", "diverged"):
                result = self.download_from_github(owner, comparison["repo"], skill_dir)
                results[skill_name] = {
                    "status": result.get("status", "downloaded"),
                    "downloaded": result.get("downloaded", []),
                    "failed": result.get("failed", []),
                    "needs_approval": result.get("needs_approval", []),
                }
            elif comparison["status"] == "ok":
                results[skill_name] = {"status": comparison["action"]}
            else:
                results[skill_name] = {"status": "error", "reason": comparison.get("reason", "compare failed")}
        except Exception as e:
            results["_exception"] = {"status": "error", "reason": str(e)}
        return results

    def _validate_repo(self, frontmatter, source_file):
        repo_field = frontmatter.get("github_repository", "") if frontmatter else ""
        if not repo_field:
            return {"valid": False, "error": f"Missing github_repository in frontmatter: {source_file}"}
        parts = repo_field.strip().strip("/").split("/")
        if len(parts) != 2:
            return {"valid": False, "error": f"Invalid format in {source_file}. Must be owner/repo."}
        return {"valid": True, "owner": parts[0], "repo": parts[1]}

    def _local_file_sha(self, file_path):
        try:
            content = Path(file_path).read_bytes()
            header = f"blob {len(content)}\0".encode()
            return hashlib.sha1(header + content).hexdigest()
        except Exception:
            return None

    def _github_api_call(self, endpoint):
        if not self.token:
            return {"error": "No GITHUB_TOKEN"}
        endpoint = endpoint.lstrip("/")
        url = f"{self.api_base}/{endpoint}"
        req = Request(url)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("Accept", "application/vnd.github+json")
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            return {"error": True, "status": e.code, "message": str(e)}
        except URLError as e:
            return {"error": True, "status": 0, "message": str(e.reason) if hasattr(e, "reason") else str(e)}
        except Exception as e:
            return {"error": True, "status": 0, "message": str(e)}


if __name__ == "__main__":
    syncer = SkillSyncer()
    print(json.dumps({"status": "ready", "syncer": "initialized"}, indent=2, ensure_ascii=False))
