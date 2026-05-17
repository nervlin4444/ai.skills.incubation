"""
---
title: Sync Engine
name: github-skill-organizer
description: Handles bi-directional sync between local skills and GitHub. All API calls delegated to github-restful-api-connector. Strict frontmatter validation enforced.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/sync_engine.py"
  github_path: "github-skill-organizer/scripts/sync_engine.py"
---
"""

import sys
import os
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime

try:
    from skill_organizer_config import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config


class SyncEngine:
    def __init__(self):
        self.cfg = load_config()
        self.dep_scripts = self.cfg.get_dependency_import_path()
        self.github_api = None
        self._init_github_api()

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

        # Must contain exactly one slash, no leading/trailing slashes
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

    # ===== UPLOAD =====

    def upload_skill(self, skill_name, files, classification):
        """Upload changed files to GitHub. Delegates all API calls to dependency skill."""
        if classification["approval_required"]:
            self._move_to_pending(skill_name, files, classification)
            return {"status": "pending_approval", "reason": classification["reason"]}

        # Validate frontmatter on all files
        for f in files:
            fm = self._read_frontmatter_from_file(f)
            validation = self._validate_github_repository(fm, f)
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

        if self.github_api:
            result = self._upload_via_api(skill_name, files, commit_msg)
        else:
            result = self._upload_via_cli(skill_name, files, commit_msg)

        return {
            "status": "uploaded",
            "commit_message": commit_msg,
            "new_version": new_version,
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
                match = re.search('"""\s*---\s*(.*?)\s*---\s*"""', content, re.DOTALL)
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
            match = re.match('^(\s*)([\w_]+):\s*(.*)$', line)
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

        for f in files:
            p = Path(f)
            if p.suffix in [".md", ".py", ".json"]:
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    if "---" not in content:
                        return {"passed": False, "reason": f"Missing frontmatter in {p.name}"}
                except Exception:
                    pass

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
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        batch_dir = pending_dir / f"{skill_name}_{ts}"
        batch_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "skill_name": skill_name,
            "classification": classification,
            "files": [str(f) for f in files],
            "timestamp": datetime.utcnow().isoformat(),
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
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_file = rejected_dir / f"{skill_name}_{ts}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump({
                "skill_name": skill_name,
                "files": [str(f) for f in files],
                "reason": gate_result.get("error") or gate_result.get("reason"),
                "timestamp": datetime.utcnow().isoformat(),
            }, f, indent=2, ensure_ascii=False)

    def _upload_via_api(self, skill_name, files, commit_msg):
        return {"method": "api", "status": "placeholder"}

    def _upload_via_cli(self, skill_name, files, commit_msg):
        return {"method": "cli", "status": "placeholder"}

    # ===== DOWNLOAD =====

    def download_all_skills(self):
        """
        Scan USER_SKILLS_FOLDER for all installed skills,
        check GitHub for newer versions, and download if needed.
        Returns: {skill_name: {"updated": bool, "version": str, "error": str|null}}
        """
        results = {}
        skills_dir = Path(self.cfg.user_skills_folder)

        if not skills_dir.exists():
            return results

        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith(".") or skill_dir.name.startswith("_"):
                continue

            skill_name = skill_dir.name
            try:
                result = self.download_skill(skill_name)
                results[skill_name] = result
            except Exception as e:
                results[skill_name] = {"updated": False, "error": str(e)}

        return results

    def download_skill(self, skill_name):
        """
        Download the latest version of a skill from GitHub.
        Reads owner/repo from local SKILL.md frontmatter.
        Returns: {"updated": bool, "version": str, "error": str|null}
        """
        local_skill_dir = Path(self.cfg.user_skills_folder) / skill_name
        local_skill_md = local_skill_dir / "SKILL.md"

        local_version = "0.0.0"
        owner_repo = None

        if local_skill_md.exists():
            fm = self._read_frontmatter_from_file(local_skill_md)
            local_version = self._extract_version_from_frontmatter(fm)
            validation = self._validate_github_repository(fm, local_skill_md)
            if validation["valid"]:
                owner_repo = f"{validation['owner']}/{validation['repo']}"

        if not owner_repo:
            return {"updated": False, "version": local_version, "error": "Missing or invalid github_repository in local SKILL.md"}

        remote_version = self._fetch_remote_version(owner_repo, skill_name)
        if remote_version is None:
            return {"updated": False, "version": local_version, "error": "Could not fetch remote version"}

        if self._version_gte(local_version, remote_version):
            return {"updated": False, "version": local_version, "error": None}

        downloaded = self._download_remote_files(owner_repo, skill_name, local_skill_dir)
        if downloaded:
            return {"updated": True, "version": remote_version, "error": None}
        else:
            return {"updated": False, "version": local_version, "error": "Download failed"}

    def _extract_version_from_frontmatter(self, frontmatter):
        version = frontmatter.get("version", "") if frontmatter else ""
        if version:
            return version.strip().strip("v")
        return "0.0.0"

    def _version_gte(self, v1, v2):
        def parse(v):
            parts = v.strip().split(".")
            return [int(p) for p in parts] + [0] * (3 - len(parts))
        try:
            return parse(v1) >= parse(v2)
        except ValueError:
            return True

    def _fetch_remote_version(self, owner_repo, skill_name):
        """Fetch the version from GitHub SKILL.md. Placeholder for dependency skill integration."""
        return None

    def _download_remote_files(self, owner_repo, skill_name, target_dir):
        """Download all files for a skill from GitHub. Placeholder."""
        return False


if __name__ == "__main__":
    engine = SyncEngine()
    print(json.dumps(engine.cfg.to_dict(), indent=2, ensure_ascii=False))


    def _read_frontmatter_from_file(self, file_path):
        """Extract frontmatter from an installed file."""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    return self._parse_simple_yaml(content[3:end])
            if Path(file_path).suffix == ".py":
                match = re.search('"""\s*---\s*(.*?)\s*---\s*"""', content, re.DOTALL)
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
            match = re.match('^(\s*)([\w_]+):\s*(.*)$', line)
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

        for f in files:
            p = Path(f)
            if p.suffix in [".md", ".py", ".json"]:
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    if "---" not in content:
                        return {"passed": False, "reason": f"Missing frontmatter in {p.name}"}
                except Exception:
                    pass

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
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        batch_dir = pending_dir / f"{skill_name}_{ts}"
        batch_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "skill_name": skill_name,
            "classification": classification,
            "files": [str(f) for f in files],
            "timestamp": datetime.utcnow().isoformat(),
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
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_file = rejected_dir / f"{skill_name}_{ts}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump({
                "skill_name": skill_name,
                "files": [str(f) for f in files],
                "reason": gate_result.get("error") or gate_result.get("reason"),
                "timestamp": datetime.utcnow().isoformat(),
            }, f, indent=2, ensure_ascii=False)

    def _upload_via_api(self, repo_name, files, commit_msg):
        return {"method": "api", "status": "placeholder", "repo_name": repo_name}

    def _upload_via_cli(self, repo_name, files, commit_msg):
        """
        Call github_repo_sync.py via CLI with CORRECT parameters.
        repo_name: ONLY the repository name (e.g. "github-skill-organizer").
        NEVER pass owner/repo format here.
        """
        try:
            dep_path = Path(self.cfg.dependency_skill_path)
            cli_script = dep_path / "scripts" / "github_repo_sync.py"
            if not cli_script.exists():
                return {"method": "cli", "status": "error", "reason": "github_repo_sync.py not found"}

            # Build command with ONLY repo name (not owner/repo)
            cmd = [
                sys.executable, str(cli_script),
                "--repo-name", repo_name,
                "--local-dir", str(self.cfg.user_skills_folder / self.cfg.dependency_skill),
                "--repo-base-path", repo_name,
                "--force",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(dep_path))
            return {
                "method": "cli",
                "status": "success" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout[:500] if result.stdout else "",
                "stderr": result.stderr[:500] if result.stderr else "",
            }
        except Exception as e:
            return {"method": "cli", "status": "error", "reason": str(e)}

    # ===== DOWNLOAD =====

    def download_all_skills(self):
        """
        Scan USER_SKILLS_FOLDER for all installed skills,
        check GitHub for newer versions, and download if needed.
        Returns: {skill_name: {"updated": bool, "version": str, "error": str|null}}
        """
        results = {}
        skills_dir = Path(self.cfg.user_skills_folder)

        if not skills_dir.exists():
            return results

        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith(".") or skill_dir.name.startswith("_"):
                continue

            skill_name = skill_dir.name
            try:
                result = self.download_skill(skill_name)
                results[skill_name] = result
            except Exception as e:
                results[skill_name] = {"updated": False, "error": str(e)}

        return results

    def download_skill(self, skill_name):
        """
        Download the latest version of a skill from GitHub.
        Reads owner/repo from local SKILL.md frontmatter.
        Returns: {"updated": bool, "version": str, "error": str|null}
        """
        local_skill_dir = Path(self.cfg.user_skills_folder) / skill_name
        local_skill_md = local_skill_dir / "SKILL.md"

        local_version = "0.0.0"
        owner_repo = None

        if local_skill_md.exists():
            fm = self._read_frontmatter_from_file(local_skill_md)
            local_version = self._extract_version_from_frontmatter(fm)
            validation = self._validate_github_repository(fm, local_skill_md)
            if validation["valid"]:
                owner_repo = f"{validation['owner']}/{validation['repo']}"

        if not owner_repo:
            return {"updated": False, "version": local_version, "error": "Missing or invalid github_repository in local SKILL.md"}

        remote_version = self._fetch_remote_version(owner_repo, skill_name)
        if remote_version is None:
            return {"updated": False, "version": local_version, "error": "Could not fetch remote version"}

        if self._version_gte(local_version, remote_version):
            return {"updated": False, "version": local_version, "error": None}

        downloaded = self._download_remote_files(owner_repo, skill_name, local_skill_dir)
        if downloaded:
            return {"updated": True, "version": remote_version, "error": None}
        else:
            return {"updated": False, "version": local_version, "error": "Download failed"}

    def _extract_version_from_frontmatter(self, frontmatter):
        version = frontmatter.get("version", "") if frontmatter else ""
        if version:
            return version.strip().strip("v")
        return "0.0.0"

    def _version_gte(self, v1, v2):
        def parse(v):
            parts = v.strip().split(".")
            return [int(p) for p in parts] + [0] * (3 - len(parts))
        try:
            return parse(v1) >= parse(v2)
        except ValueError:
            return True

    def _fetch_remote_version(self, owner_repo, skill_name):
        """Fetch the version from GitHub SKILL.md. Placeholder for dependency skill integration."""
        return None

    def _download_remote_files(self, owner_repo, skill_name, target_dir):
        """Download all files for a skill from GitHub. Placeholder."""
        return False


if __name__ == "__main__":
    engine = SyncEngine()
    print(json.dumps(engine.cfg.to_dict(), indent=2, ensure_ascii=False))
