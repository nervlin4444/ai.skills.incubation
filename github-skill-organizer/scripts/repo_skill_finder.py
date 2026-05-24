"""
---
title: Repo Skill Finder
name: github-skill-organizer
description: Scans GitHub repositories to discover skill packages. Supports flat and monorepo layouts. Replaces repo_inventory.py.
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
  local_path: scripts/repo_skill_finder.py
  github_path: github-skill-organizer/scripts/repo_skill_finder.py
---
"""

import sys
from pathlib import Path

try:
    from skill_organizer_config import load_config
    from core_github_api import GitHubAPIClient
    from core_logger import log
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config
    from core_github_api import GitHubAPIClient
    from core_logger import log


class RepoSkillFinder:
    """
    Remote skill discovery.
    Scans GitHub repos to find which contain skill packages.
    """

    def __init__(self):
        self.cfg = load_config()
        self.token = self.cfg.get_github_token()
        self.client = GitHubAPIClient(self.token) if self.token else None

    def find_all_skills(self, owner=None):
        """
        Scan all repos for skills.
        Returns list of skill records with layout type (flat/monorepo).
        """
        if not self.client:
            log("FINDER", "No GitHub token available", "ERROR")
            return []

        if owner is None:
            owner = self.cfg.get_github_owner()

        repos = self.client.call(f"/users/{owner}/repos?per_page=100")
        if isinstance(repos, dict) and repos.get("error"):
            log("FINDER", f"API error: {repos.get('message', 'unknown')}", "ERROR")
            return []

        skills = []
        for repo in repos:
            repo_name = repo.get("name", "")
            if not repo_name:
                continue

            # Check flat layout: SKILL.md at root
            root_skill = self.client.call(f"/repos/{owner}/{repo_name}/contents/SKILL.md")
            if not (isinstance(root_skill, dict) and root_skill.get("error")):
                skills.append({
                    "repo": repo_name,
                    "skill_name": repo_name,
                    "layout": "flat",
                    "path": "SKILL.md",
                })
                continue

            # Check monorepo: list root contents for subdirectories with SKILL.md
            contents = self.client.call(f"/repos/{owner}/{repo_name}/contents")
            if not isinstance(contents, list):
                continue

            for item in contents:
                if item.get("type") != "dir":
                    continue
                subdir = item.get("name", "")
                sub_skill = self.client.call(f"/repos/{owner}/{repo_name}/contents/{subdir}/SKILL.md")
                if not (isinstance(sub_skill, dict) and sub_skill.get("error")):
                    skills.append({
                        "repo": repo_name,
                        "skill_name": subdir,
                        "layout": "monorepo",
                        "path": f"{subdir}/SKILL.md",
                    })

        log("FINDER", f"Found {len(skills)} skills across {len(repos)} repos")
        return skills

    def find_skill(self, skill_name, owner=None):
        """Find specific skill by name."""
        if owner is None:
            owner = self.cfg.get_github_owner()
        all_skills = self.find_all_skills(owner)
        for skill in all_skills:
            if skill["skill_name"] == skill_name:
                return skill
        return None


if __name__ == "__main__":
    import json
    finder = RepoSkillFinder()
    skills = finder.find_all_skills()
    print(json.dumps({"skills_found": len(skills), "skills": skills}, indent=2, ensure_ascii=False))
