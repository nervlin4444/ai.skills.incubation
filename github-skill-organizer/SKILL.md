---
title: GitHub Skill Organizer - LLM Execution Directive
name: github-skill-organizer
description: Background daemon for bi-directional skill sync. Authentication borrowed from github-restful-api-connector. Strict frontmatter validation enforced. THIS FILE IS FOR LLM AGENTS ONLY.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/SKILL.md"
  github_path: "github-skill-organizer/SKILL.md"
---

# [LLM ONLY] EXECUTION DIRECTIVE

## 1. ROLE DEFINITION
You are the execution agent for github-skill-organizer. Your sole purpose is to maintain a background synchronization daemon that bridges local skill directories and GitHub repositories.

## 2. AUTHENTICATION POLICY
This skill does NOT hold GITHUB_TOKEN or GITHUB_OWNER. All authentication is borrowed from the dependency skill github-restful-api-connector.
- GITHUB_TOKEN: read from dependency skill .env (never stored locally)
- GITHUB_OWNER: read from dependency skill .env (only for logging/error messages)
- All GitHub API calls are delegated to github-restful-api-connector

## 3. PRE-EXECUTION CHECKLIST
Before performing ANY sync operation, verify ALL of the following:

- [ ] Dependency skill github-restful-api-connector is installed at DEPENDENCY_SKILL_PATH in .env. If missing, HALT and instruct user to install it first.
- [ ] .env file exists in the skill root directory with valid DOWNLOAD_FOLDER, USER_SKILLS_FOLDER, DEPENDENCY_SKILL_PATH.
- [ ] The scheduler daemon is not already running (check PID file at /tmp/github-skill-organizer.pid).

## 4. CORE WORKFLOW
When user invokes this skill, execute EXACTLY this sequence:

### Step 1: Dependency Verification
Run github_dependency_checker.py. If return code != 0, output the error message and STOP.

### Step 2: Configuration Load
Run skill_organizer_config.py to load .env and config/sync.config.json. Validate all required paths exist.

### Step 3: Daemon Start
Execute scheduler_daemon.py in background mode. This process will:
- Scan DOWNLOAD_FOLDER every 60 seconds for new files (mtime > last_run_timestamp)
- Read frontmatter from each new file
- Validate github_repository format (must be "owner/repo")
- Reject files with invalid/missing github_repository (log to logs/rejected/)
- Classify files into target skill directories based on name and file_mapping fields
- Trigger upload/download via sync_engine.py (delegated to dependency skill)
- Log all actions to logs/organizer.log

### Step 4: Immediate Sync (Optional)
If user provides --sync-now flag, run one immediate sync cycle before starting daemon.

## 5. CHANGE CLASSIFICATION RULES (HARD-CODED)
The change_classifier.py uses DETERMINISTIC rules. NO LLM judgment is permitted for version bumping:

| Trigger Condition | Version Bump | Approval Required | Action |
|---|---|---|---|
| File count <= 3, only typo/path fixes, no new dependencies, no SKILL.md changes | Patch (+0.0.1) | NO | Auto-upload via sync_engine |
| File count > 3, or new dependencies added, or SKILL.md modified, or config changed | Minor (+0.1.0) | YES | Move to pending_approval/, generate report |
| Breaking changes, skill merge, or major architecture shift | Major (+1.0.0) | YES (Owner) | Move to pending_approval/, generate report |

## 6. FRONTMATTER VALIDATION (STRICT)
Every skill file MUST have a valid github_repository in frontmatter. Format: "owner/repo" (exactly one slash).

Invalid formats that MUST be rejected:
- "github-skill-organizer" (missing owner)
- "ai.skill.automation" (missing repo)
- "" or null (missing entirely)

On rejection: log to logs/rejected/, skip file, continue processing other files.

## 7. UPLOAD GATE CHECK (Pre-Commit)
Before ANY upload to GitHub, sync_engine.py MUST verify:
1. All files have valid frontmatter (title, name, description, version, github_repository, target_branch, auth_config, file_mapping)
2. github_repository is exactly "owner/repo" format
3. Version string follows semver (x.y.z)
4. No hardcoded absolute paths in scripts (regex scan for /home/, C:\\, /Users/)
5. Commit message template: [{bump_type}] {skill_name} v{new_version} by {agent_name}({model}) - {summary}

If ANY check fails, ABORT upload and log to logs/rejected/.

## 8. CRITICAL: github_repo_sync.py INVOCATION RULE
When calling github-restful-api-connector/scripts/github_repo_sync.py to upload files, you MUST follow these EXACT rules:

### 8.1 Parameter Rules
| Parameter | Required | Value Rule | Common Mistake |
|---|---|---|---|
| --repo-name | YES | ONLY the repository name, e.g. "github-skill-organizer" | NEVER pass "owner/repo" like "nervlin4444/github-skill-organizer" |
| --local-dir | YES | Absolute path to the skill directory on local machine | |
| --repo-base-path | YES | The subdirectory path inside the repo, usually same as skill name | |
| --force | Optional | Add this flag to overwrite existing files | |

### 8.2 Owner Resolution
The owner (GITHUB_OWNER) is ALWAYS read from github-restful-api-connector/.env by the script itself.
You MUST NOT pass owner in --repo-name.

### 8.3 Example Correct Invocation
    python3 /path/to/github-restful-api-connector/scripts/github_repo_sync.py
        --repo-name github-skill-organizer
        --local-dir /home/user/skills/github-skill-organizer
        --repo-base-path github-skill-organizer
        --force

### 8.4 Example WRONG Invocation (NEVER DO THIS)
    # WRONG: passing owner/repo in --repo-name
    python3 ... --repo-name nervlin4444/github-skill-organizer

    # WRONG: passing full path with owner
    python3 ... --repo-name ai.skills.incubation/github-skill-organizer

### 8.5 Why This Matters
github_repo_sync.py creates the repository if it does not exist.
If you pass "nervlin4444/github-skill-organizer" as --repo-name, the script will create a repo literally named "nervlin4444-github-skill-organizer".
This is a PERMANENT mistake that pollutes the GitHub account with wrong repositories.

### 8.6 sync_engine.py Safety
sync_engine.py MUST extract repo name from frontmatter github_repository before calling github_repo_sync.py:

    # CORRECT: extract only repo name
    owner_repo = frontmatter["github_repository"]  # "nervlin4444/ai.skills.incubation"
    parts = owner_repo.split("/")
    repo_name = parts[-1]  # "ai.skills.incubation"
    # Pass repo_name to --repo-name

## 9. WEB FETCHER (DEFERRED MODULE)
The web_fetcher.py module is DISABLED by default. Enable ONLY when:
- User explicitly requests --enable-web-fetch
- A playwright-compatible skill is detected in USER_SKILLS_FOLDER
- User has provided a static download link pattern for Kimi outputs

If enabled, it runs as a SEPARATE thread in the daemon, fetching web content to DOWNLOAD_FOLDER before the main scanner processes them.

## 10. ERROR HANDLING
- All exceptions MUST be caught and logged. Daemon MUST NOT crash.
- If GitHub API returns 401/403, pause sync for 5 minutes and retry once.
- If dependency skill import fails, daemon enters DEGRADED mode (local-only operations).

## 11. SHUTDOWN
On receiving SIGTERM or user command --stop, write final timestamp to state/last_run.json, remove PID file, and exit cleanly.

## 12. PROHIBITED ACTIONS
- NEVER modify github-restful-api-connector skill files.
- NEVER create new skills autonomously.
- NEVER use LLM API calls inside the daemon loop (token conservation rule).
- NEVER upload files with NEEDS_APPROVAL status.
- NEVER store GITHUB_TOKEN or GITHUB_OWNER in local .env or state files.
- NEVER pass owner/repo format to --repo-name when calling github_repo_sync.py.

## 13. STATE FILES
The daemon maintains these state files (JSON):
- state/last_run.json: Timestamp of last successful scan
- state/pending_uploads.json: Queue of approved patch-level changes
- state/pending_approval.json: Queue of minor/major changes awaiting owner review
