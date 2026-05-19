---
title: GitHub Skill Organizer - CLI Usage Guide
name: github-skill-organizer
description: Command-line usage reference. Authentication borrowed from github-restful-api-connector.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/USAGE.md"
  github_path: "github-skill-organizer/scripts/USAGE.md"
---

# GitHub Skill Organizer - CLI Usage Guide

## Prerequisites
1. Dependency Skill: `github-restful-api-connector` must be installed in your `USER_SKILLS_FOLDER`, with its `.env` configured with `GITHUB_TOKEN` and `GITHUB_OWNER`.
2. Python 3.8+

## Installation

### Step 1: Place Skill
Place this skill directory into your local skills folder:
    ~/skills/github-skill-organizer/

### Step 2: Configure Environment
Copy `.env.example` to `.env` and fill in:

    DOWNLOAD_FOLDER=~/Downloads/skills-inbox
    USER_SKILLS_FOLDER=~/skills
    DEPENDENCY_SKILL=github-restful-api-connector
    DEPENDENCY_SKILL_PATH=~/skills/github-restful-api-connector

Note: `GITHUB_TOKEN` and `GITHUB_OWNER` are **NOT** in this `.env`. They are read from the dependency skill `.env`.

### Step 3: Start Daemon
    cd ~/skills/github-skill-organizer
    python scripts/scheduler_daemon.py --start

The daemon will run in background, checking every 60 seconds.

### Step 4: Verify
Check logs:
    tail -f logs/organizer.log

## Commands

### Daemon Commands

| Command | Description |
|---|---|
| `python scripts/scheduler_daemon.py --start` | Start background daemon |
| `python scripts/scheduler_daemon.py --stop` | Stop daemon |
| `python scripts/scheduler_daemon.py --status` | Check daemon status |
| `python scripts/scheduler_daemon.py --sync-now` | Run one sync cycle immediately |
| `python scripts/scheduler_daemon.py --scan-only` | Scan without upload/download |

### Repository Inventory (repo_inventory.py)

List all GitHub repositories and identify which are skills.

#### List All Repositories (Human Readable)

    python3 scripts/repo_inventory.py

Output:
    === GitHub Repository Inventory ===
    Owner: nervlin4444
    Total Repositories: 23
    Skills Identified: 5
    Non-Skill Repos: 18
    Errors: 0

    --- Skills ---
      [github-skill-organizer] github-skill-organizer (v1.0.0) - https://github.com/nervlin4444/github-skill-organizer
      [github-restful-api-connector] github-restful-api-connector (v1.2.0) - https://github.com/nervlin4444/github-restful-api-connector

#### List All Repositories (JSON for Agent)

    python3 scripts/repo_inventory.py --json

Returns structured JSON with:
- `skills`: Array of skill objects (skill_name, repo_name, version, description, html_url)
- `non_skills`: Array of non-skill repositories
- `errors`: Any API errors

#### Limit Scan (Testing)

    python3 scripts/repo_inventory.py --max-repos 5

### Skill Comparison and Sync (skill_sync.py)

Compare local skill with GitHub and sync if needed.

#### Compare (Minimum Cost - SHA Only)

    python3 scripts/skill_sync.py compare --skill-name github-skill-organizer

Compares local files with GitHub using SHA1 hashes. No file content is downloaded.

Output actions:
- `identical`: Local and GitHub are exactly the same
- `local_ahead`: Local has changes not on GitHub (needs upload)
- `github_ahead`: GitHub has changes not locally (needs download)
- `diverged`: Both have different changes

#### Compare with Custom Directory

    python3 scripts/skill_sync.py compare --skill-name github-skill-organizer --local-dir /mnt/nas/skills-backup/github-skill-organizer

#### Sync (Dry-Run by Default)

    python3 scripts/skill_sync.py sync --skill-name github-skill-organizer

If GitHub is ahead, shows what would be downloaded. No files modified.

#### Sync (Apply Download)

    python3 scripts/skill_sync.py sync --skill-name github-skill-organizer --apply

If GitHub is ahead, downloads and overwrites local files. **No backup is created.**

#### Force Download

    python3 scripts/skill_sync.py download --owner nervlin4444 --repo github-skill-organizer --target-dir /path/to/destination

Downloads all files from GitHub repository to any target directory.

### Repository Migration (repo_migrator.py)

When you need to change the `github_repository` field across all files in a skill package.

#### Preview Mode (Default - Dry Run)

    python3 scripts/repo_migrator.py
        --skill-dir ~/skills/github-skill-organizer
        --old-repo "nervlin4444/ai.skills.incubation"
        --new-repo "nervlin4444/ai.skills.devops"

#### Apply Mode (Writes Changes)

    python3 scripts/repo_migrator.py
        --skill-dir ~/skills/github-skill-organizer
        --old-repo "nervlin4444/ai.skills.incubation"
        --new-repo "nervlin4444/ai.skills.devops"
        --apply

## How It Works

### Download Folder Processing
Any file placed in `DOWNLOAD_FOLDER` with valid frontmatter is automatically:
1. Parsed for skill name and target repository
2. **Validated**: `github_repository` must be exactly `owner/repo` format
3. If invalid: rejected and logged to `logs/rejected/`
4. If valid: merged into the correct local skill directory (path derived from `file_mapping.github_path`)
5. Version-checked against existing files
6. Classified for upload (auto or pending approval)

### Upload to GitHub
When local skill files change:
1. Patch changes (typos, paths): Auto-upload with version +0.0.1
2. Minor/Major changes: Moved to `pending_approval/` for your review

### Cross-Workstation Sync
Other workstations running this daemon will pull the latest versions from GitHub automatically.

### Skill Comparison (SHA-Based)
The `skill_sync.py compare` command:
1. Reads local `SKILL.md` to get `github_repository`
2. Fetches GitHub repository tree with file SHAs via API
3. Computes local file SHAs (Git blob format)
4. Compares without downloading any file content
5. Reports: identical, local_ahead, github_ahead, or diverged

### Reverse Download
When GitHub is ahead of local:
1. `skill_sync.py sync --apply` downloads files from GitHub
2. Overwrites local files directly (no backup)
3. Works with any target directory, not just `USER_SKILLS_FOLDER`

## Directory Structure

    github-skill-organizer/
    ├── SKILL.md              # LLM execution directive
    ├── README.md             # Human overview
    ├── .env.example          # Environment template (no GITHUB_TOKEN)
    ├── scripts/
    │   ├── USAGE.md          # This file
    │   ├── scheduler_daemon.py   # Main daemon
    │   ├── sync_engine.py    # GitHub sync logic (upload/download/compare)
    │   ├── skill_sync.py     # CLI for compare and sync
    │   ├── local_scanner.py  # Local file scanner
    │   ├── change_classifier.py  # Version bump logic
    │   ├── skill_installer.py    # Skill registration
    │   ├── github_dependency_checker.py  # Dependency check
    │   ├── repo_inventory.py   # GitHub repository inventory
    │   └── repo_migrator.py  # Repository migration utility
    ├── config/
    │   └── sync.config.json  # Path mappings
    ├── logs/                 # Runtime logs
    ├── state/                # Daemon state (JSON)
    └── pending_approval/     # Changes awaiting owner review

## Troubleshooting

| Issue | Solution |
|---|---|
| Daemon will not start | Check `.env` and dependency skill path |
| Files rejected with "Invalid github_repository" | Ensure frontmatter has `github_repository: "owner/repo"` |
| Upload rejected | Check `logs/rejected/` for specific errors |
| Web fetcher disabled | This is expected; enable only when ready |
| repo_migrator says "0 files modified" | Check that `--old-repo` exactly matches current value (including quotes) |
| `skill_sync.py compare` says "No local SKILL.md found" | Ensure the skill directory contains a SKILL.md file with valid frontmatter |
| `repo_inventory.py` returns 0 skills | Check that repositories contain SKILL.md with valid frontmatter including `name` field |
| Agent cannot find repositories | Run `repo_inventory.py --json` first to get the list, then guide agent with specific repo names |

## Safety Rules
- The daemon NEVER modifies files outside `USER_SKILLS_FOLDER` and `DOWNLOAD_FOLDER`
- All uploads are logged with commit messages for audit
- Breaking changes are ALWAYS held for manual approval
- GITHUB_TOKEN is never stored in this skill directory
- Repository migration ALWAYS requires dry-run preview before `--apply`
- Skill comparison uses SHA hashes only - no file content is transferred during comparison
- Reverse download (`sync --apply`) overwrites files without backup - use with caution
