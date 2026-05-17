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

| Command | Description |
|---|---|
| `python scripts/scheduler_daemon.py --start` | Start background daemon |
| `python scripts/scheduler_daemon.py --stop` | Stop daemon |
| `python scripts/scheduler_daemon.py --status` | Check daemon status |
| `python scripts/scheduler_daemon.py --sync-now` | Run one sync cycle immediately |
| `python scripts/scheduler_daemon.py --scan-only` | Scan without upload/download |

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

## Directory Structure

    github-skill-organizer/
    ├── SKILL.md              # LLM execution directive
    ├── README.md             # Human overview
    ├── .env.example          # Environment template (no GITHUB_TOKEN)
    ├── scripts/
    │   ├── USAGE.md          # This file
    │   ├── scheduler_daemon.py   # Main daemon
    │   ├── sync_engine.py    # GitHub sync logic
    │   ├── local_scanner.py  # Local file scanner
    │   ├── change_classifier.py  # Version bump logic
    │   ├── skill_installer.py    # Skill registration
    │   └── github_dependency_checker.py  # Dependency check
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

## Safety Rules
- The daemon NEVER modifies files outside `USER_SKILLS_FOLDER` and `DOWNLOAD_FOLDER`
- All uploads are logged with commit messages for audit
- Breaking changes are ALWAYS held for manual approval
- GITHUB_TOKEN is never stored in this skill directory
