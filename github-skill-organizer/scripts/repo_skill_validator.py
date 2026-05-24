"""
---
title: Repo Skill Validator
name: github-skill-organizer
description: Validates that claimed GitHub repositories actually exist. Replaces repo_validator.py.
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
  local_path: scripts/repo_skill_validator.py
  github_path: github-skill-organizer/scripts/repo_skill_validator.py
---
"""

import sys
from pathlib import Path

try:
    from skill_organizer_config import load_config
    from core_frontmatter import FrontmatterExtractor
    from core_github_api import GitHubAPIClient
    from core_path_utils import normalize_path
    from core_logger import log
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config
    from core_frontmatter import FrontmatterExtractor
    from core_github_api import GitHubAPIClient
    from core_path_utils import normalize_path
    from core_logger import log


class RepoSkillValidator:
    """
    Repository existence validator.
    Checks if the repo claimed in SKILL.md actually exists on GitHub.
    """

    def __init__(self):
        self.cfg = load_config()
        self.token = self.cfg.get_github_token()
        self.client = GitHubAPIClient(self.token) if self.token else None

    def validate_skill(self, skill_name, local_dir=None):
        """
        Validate a skill's claimed GitHub repository.
        Returns validation result with is_valid and details.
        """
        if local_dir is None:
            local_dir = normalize_path(Path(self.cfg.user_skills_folder) / skill_name)
        else:
            local_dir = normalize_path(local_dir)

        if not local_dir.exists():
            return {"is_valid": False, "reason": f"Local directory not found: {local_dir}"}

        skill_md = local_dir / "SKILL.md"
        if not skill_md.exists():
            return {"is_valid": False, "reason": "SKILL.md not found"}

        fm = FrontmatterExtractor.extract(skill_md)
        if not fm:
            return {"is_valid": False, "reason": "Cannot parse SKILL.md frontmatter"}

        repo_field = fm.get("github_repository", "")
        if not repo_field:
            return {"is_valid": False, "reason": "Missing github_repository in frontmatter"}

        parts = repo_field.strip().strip("/").split("/")
        if len(parts) != 2:
            return {"is_valid": False, "reason": f"Invalid repo format: {repo_field}"}

        owner, repo = parts
        if not self.client:
            return {"is_valid": False, "reason": "No GitHub token available"}

        # Check repo exists
        repo_data = self.client.call(f"/repos/{owner}/{repo}")
        if isinstance(repo_data, dict) and repo_data.get("error"):
            return {
                "is_valid": False,
                "reason": f"Repository not found or inaccessible: {repo_field}",
                "api_error": repo_data.get("message", "unknown"),
            }

        # Check skill_name subdirectory exists (monorepo check)
        skill_path = f"/repos/{owner}/{repo}/contents/{skill_name}/SKILL.md"
        skill_check = self.client.call(skill_path)
        if isinstance(skill_check, dict) and skill_check.get("error"):
            # Try flat layout
            flat_check = self.client.call(f"/repos/{owner}/{repo}/contents/SKILL.md")
            if isinstance(flat_check, dict) and flat_check.get("error"):
                return {
                    "is_valid": False,
                    "reason": f"SKILL.md not found in repo {repo_field} (tried both flat and {skill_name}/)",
                }
            layout = "flat"
        else:
            layout = "monorepo"

        return {
            "is_valid": True,
            "repo": repo_field,
            "owner": owner,
            "repo_name": repo,
            "layout": layout,
            "skill_name": skill_name,
            "local_dir": str(local_dir),
        }

    def validate_all_skills(self):
        """Validate all skills in the skills folder."""
        skills_dir = normalize_path(self.cfg.user_skills_folder)
        if not skills_dir.exists():
            return {"error": "Skills folder not found"}

        results = []
        for item in skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                result = self.validate_skill(item.name)
                results.append(result)

        valid = [r for r in results if r.get("is_valid")]
        invalid = [r for r in results if not r.get("is_valid")]

        return {
            "total": len(results),
            "valid": len(valid),
            "invalid": len(invalid),
            "results": results,
        }


if __name__ == "__main__":
    import json
    validator = RepoSkillValidator()
    report = validator.validate_all_skills()
    print(json.dumps(report, indent=2, ensure_ascii=False))
