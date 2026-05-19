"""
---
title: Skill Sync CLI
name: github-skill-organizer
description: Standalone CLI for comparing local skills with GitHub and performing reverse downloads. Wraps sync_engine.py for easy agent invocation.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/skill_sync.py"
  github_path: "github-skill-organizer/scripts/skill_sync.py"
---
"""

import sys
import json
import argparse
from pathlib import Path

try:
    from sync_engine import SyncEngine
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from sync_engine import SyncEngine


def main():
    parser = argparse.ArgumentParser(description="Skill Sync: Compare local with GitHub and sync")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # compare command
    compare_parser = subparsers.add_parser("compare", help="Compare local skill with GitHub")
    compare_parser.add_argument("--skill-name", required=True, help="Skill name (directory name)")
    compare_parser.add_argument("--local-dir", help="Override local directory (default: USER_SKILLS_FOLDER/skill-name)")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync: download from GitHub if ahead")
    sync_parser.add_argument("--skill-name", required=True, help="Skill name (directory name)")
    sync_parser.add_argument("--local-dir", help="Override local directory")
    sync_parser.add_argument("--apply", action="store_true", help="Apply download (default is dry-run)")

    # download command
    download_parser = subparsers.add_parser("download", help="Force download from GitHub to local")
    download_parser.add_argument("--owner", required=True, help="GitHub owner")
    download_parser.add_argument("--repo", required=True, help="GitHub repo name")
    download_parser.add_argument("--target-dir", required=True, help="Local target directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    engine = SyncEngine()

    if args.command == "compare":
        result = engine.compare_skill(args.skill_name, args.local_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "sync":
        result = engine.sync_skill(args.skill_name, args.local_dir, dry_run=not args.apply)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "download":
        result = engine.download_from_github(args.owner, args.repo, args.target_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
