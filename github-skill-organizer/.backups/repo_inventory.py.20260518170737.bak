"""
---
title: Repository Inventory Scanner v2
name: github-skill-organizer
description: Scans GitHub repositories and identifies skill packages. Supports flat repos (SKILL.md in root) and monorepo layout (SKILL.md in subdirectories). Outputs structured inventory for agent consumption.
version: 2.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/repo_inventory.py"
  github_path: "github-skill-organizer/scripts/repo_inventory.py"
---
"""

import sys
import os
import json
import re
import base64
import ssl
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    from skill_organizer_config import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config


class RepoInventory:
    """
    Scans GitHub repositories and identifies skill packages.
    Supports two layouts:
      A. Flat: SKILL.md in repository root (single skill per repo)
      B. Monorepo: SKILL.md in subdirectories (multiple skills per repo)
    """

    def __init__(self):
        self.cfg = load_config()
        self.token = self.cfg.get_github_token()
        self.owner = self.cfg.get_github_owner()
        self.api_base = "https://api.github.com"

    def _api_call(self, endpoint, use_unverified=False):
        """Make authenticated GitHub API call with SSL fallback."""
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
                return self._api_call(endpoint, use_unverified=True)
            return {"error": True, "status": 0, "message": err_str}
        except Exception as e:
            return {"error": True, "status": 0, "message": str(e)}

    def list_repositories(self, repo_type="owner", per_page=100):
        """List all repositories for the authenticated user."""
        all_repos = []
        page = 1
        while True:
            endpoint = f"/user/repos?type={repo_type}&per_page={per_page}&page={page}"
            data = self._api_call(endpoint)
            if isinstance(data, dict) and data.get("error"):
                return data
            if not data:
                break
            all_repos.extend(data)
            if len(data) < per_page:
                break
            page += 1
        return all_repos

    def read_repo_content(self, owner, repo, path=""):
        """Read repository contents at given path. Returns list of items or error dict."""
        endpoint = f"/repos/{owner}/{repo}/contents/{path}?ref=main" if path else f"/repos/{owner}/{repo}/contents?ref=main"
        return self._api_call(endpoint)

    def read_file_content(self, owner, repo, path):
        """Read a specific file from repository. Returns decoded content or None."""
        endpoint = f"/repos/{owner}/{repo}/contents/{path}?ref=main"
        data = self._api_call(endpoint)

        if isinstance(data, dict) and data.get("error"):
            return None

        content_b64 = data.get("content", "")
        if not content_b64:
            return None

        try:
            return base64.b64decode(content_b64.replace("\n", "")).decode("utf-8", errors="ignore")
        except Exception:
            return None

    def extract_frontmatter(self, content):
        """Extract YAML frontmatter from markdown content. Returns dict or None."""
        if not content or not content.startswith("---"):
            return None

        end = content.find("---", 3)
        if end == -1:
            return None

        fm_text = content[3:end].strip()
        return self._parse_simple_yaml(fm_text)

    def _parse_simple_yaml(self, yaml_text):
        """Parse simple YAML subset."""
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
        return result if result else None

    def scan_repo_for_skills(self, owner, repo):
        """
        Scan a single repository for skills.
        First checks root for SKILL.md (flat layout).
        If not found, scans subdirectories (monorepo layout).
        Returns list of skill dicts.
        """
        skills = []

        # Strategy A: Flat layout - SKILL.md in root
        root_content = self.read_file_content(owner, repo, "SKILL.md")
        if root_content:
            fm = self.extract_frontmatter(root_content)
            if fm and "name" in fm:
                skills.append({
                    "skill_name": fm["name"],
                    "repo_name": repo,
                    "path_in_repo": "SKILL.md",
                    "layout": "flat",
                    "version": fm.get("version", ""),
                    "description": fm.get("description", ""),
                    "github_repository": fm.get("github_repository", f"{owner}/{repo}"),
                })
                return skills  # Flat repo found, no need to scan deeper

        # Strategy B: Monorepo layout - scan subdirectories
        contents = self.read_repo_content(owner, repo)
        if isinstance(contents, dict) and contents.get("error"):
            return [{"error": contents.get("message", "API error"), "repo": repo}]

        if not isinstance(contents, list):
            return []

        for item in contents:
            if item["type"] != "dir":
                continue

            subdir_name = item["name"]
            skill_md_path = f"{subdir_name}/SKILL.md"
            skill_content = self.read_file_content(owner, repo, skill_md_path)

            if not skill_content:
                continue

            fm = self.extract_frontmatter(skill_content)
            if not fm or "name" not in fm:
                continue

            skills.append({
                "skill_name": fm["name"],
                "repo_name": repo,
                "path_in_repo": skill_md_path,
                "layout": "monorepo",
                "version": fm.get("version", ""),
                "description": fm.get("description", ""),
                "github_repository": fm.get("github_repository", f"{owner}/{repo}"),
            })

        return skills

    def scan_all(self, max_repos=None):
        """
        Full scan: list repos, identify skills (flat or monorepo), return structured report.
        """
        if not self.owner:
            return {"error": "GITHUB_OWNER not available from dependency skill .env"}

        repos = self.list_repositories()
        if isinstance(repos, dict) and repos.get("error"):
            return repos

        all_skills = []
        repo_details = []
        errors = []

        for idx, repo in enumerate(repos):
            if max_repos and idx >= max_repos:
                break

            repo_name = repo.get("name", "unknown")
            repo_info = {
                "repo_name": repo_name,
                "full_name": repo.get("full_name", ""),
                "private": repo.get("private", True),
                "html_url": repo.get("html_url", ""),
                "updated_at": repo.get("updated_at", ""),
            }

            skills = self.scan_repo_for_skills(self.owner, repo_name)

            # Check if any skill returned an error
            if skills and "error" in skills[0]:
                errors.append({
                    "repo": repo_name,
                    "error": skills[0]["error"],
                })
                repo_info["skills_found"] = 0
                repo_info["skill_layout"] = "error"
            elif skills:
                repo_info["skills_found"] = len(skills)
                repo_info["skill_layout"] = skills[0].get("layout", "unknown")
                for s in skills:
                    all_skills.append({
                        **repo_info,
                        "skill_name": s["skill_name"],
                        "path_in_repo": s["path_in_repo"],
                        "version": s["version"],
                        "description": s["description"],
                        "github_repository": s["github_repository"],
                    })
            else:
                repo_info["skills_found"] = 0
                repo_info["skill_layout"] = "none"

            repo_details.append(repo_info)

        return {
            "owner": self.owner,
            "total_repos": len(repos),
            "skill_count": len(all_skills),
            "skills": all_skills,
            "repo_details": repo_details,
            "errors": errors,
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Repository Inventory for Skills (v2 - Monorepo Support)")
    parser.add_argument("--max-repos", type=int, help="Limit scan to N repos (for testing)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    inv = RepoInventory()
    result = inv.scan_all(max_repos=args.max_repos)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n=== GitHub Repository Inventory (v2) ===")
        print(f"Owner: {result.get('owner', 'unknown')}")
        print(f"Total Repositories: {result.get('total_repos', 0)}")
        print(f"Skills Identified: {result.get('skill_count', 0)}")
        print(f"Errors: {len(result.get('errors', []))}")

        print("\n--- Skills Found ---")
        for s in result.get("skills", []):
            layout = s.get("path_in_repo", "SKILL.md")
            print(f"  [{s['skill_name']}] {s['repo_name']} (v{s.get('version', '?')}) - {layout}")
            print(f"    URL: {s.get('html_url', '')}")

        if result.get("errors"):
            print("\n--- Errors ---")
            for e in result["errors"]:
                print(f"  {e['repo']}: {e['error']}")

        # Monorepo summary
        monorepos = [r for r in result.get("repo_details", []) if r.get("skill_layout") == "monorepo"]
        if monorepos:
            print(f"\n--- Monorepo Layout Detected ({len(monorepos)} repos) ---")
            for r in monorepos:
                print(f"  {r['repo_name']}: {r['skills_found']} skill(s)")


if __name__ == "__main__":
    main()
