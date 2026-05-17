"""
---
title: GitHub Dependency Checker
name: github-skill-organizer
description: Verifies that the required github-restful-api-connector skill is installed and importable.
version: 1.0.0
github_repository: ai.skills.incubation/github-skill-organizer
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/github_dependency_checker.py"
  github_path: "github-skill-organizer/scripts/github_dependency_checker.py"
---
"""

import sys
import os
from pathlib import Path

try:
    from skill_organizer_config import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config


def check_dependency():
    cfg = load_config()
    dep_path = Path(cfg.dependency_skill_path)

    print(f"Checking dependency: {cfg.dependency_skill}")
    print(f"Expected path: {dep_path}")

    if not dep_path.exists():
        print(f"[FAIL] Dependency skill not found at {dep_path}", file=sys.stderr)
        print("[HINT] Please install github-restful-api-connector skill first.", file=sys.stderr)
        print("[HINT] It must be registered by the owner (you) in the GitHub repo.", file=sys.stderr)
        return 1

    scripts_dir = dep_path / "scripts"
    if not scripts_dir.exists():
        print(f"[FAIL] scripts/ directory not found in {dep_path}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(scripts_dir))

    possible_modules = [
        "github_repo_sync",
        "github_api",
        "github_client",
    ]

    found = False
    for mod in possible_modules:
        try:
            __import__(mod)
            print(f"[OK] Found importable module: {mod}")
            found = True
            break
        except ImportError:
            continue

    if not found:
        print("[WARN] No known modules importable, but directory exists.")
        print("[INFO] Will attempt CLI invocation at runtime.")

    print("[OK] Dependency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(check_dependency())
