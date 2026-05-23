---
title: "GitHub Skill Organizer"
name: github-skill-organizer
description: "GitHub skill repository sync manager with invalid file detection and auto-notification. v1.1.0 adds local_scanner v1.0.8, skill_installer v1.0.7, invalid_file_notifier v1.0.0, and daemon_health_check v1.0.1. Supports batch upload, comparison, conflict detection, CHANGELOG sync, and standard Issue reporting."
version: "1.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T23:00:00+08:00"
fixes: []

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"

file_mapping:
  local_path: "README.md"
  github_path: "github-skill-organizer/README.md"
---

# github-skill-organizer

Version: 1.1.0
Last Updated: 2026-05-23 23:00:00
Core Changes: v1.1.0 adds invalid file detection, auto-notification daemon, and health check.

## Features

| Feature | Description | Status |
|---------|-------------|--------|
| Batch sync upload | Local skill directory -> GitHub repo subdirectory | Done |
| Auto read repo | Read github_repository from SKILL.md frontmatter | Done |
| Auto create repo | Create when not exists (auto_init=False) | Done |
| Conflict detection | Compare local vs remote file SHA to avoid overwrite | Done |
| Safe clone | Token not in command line, supports credential helper | Done |
| Auto skill name detection | Read name field from SKILL.md | Done |
| Subdirectory filter | compare_skill only compares skill subdirectory | Done v1.0.11 |
| File exclusion | Auto exclude .backups, __pycache__, LICENSE | Done v1.0.11 |
| CHANGELOG sync | Check and sync CHANGELOG.md frontmatter | Done v1.0.11 |
| Standard Issue report | skill_issue_reporter.py强制格式输出 | Done v1.0.12 |
| fixes field support | Auto read file frontmatter fixes to generate Fixes #N commit | Done v1.0.13 |
| **Invalid file detection** | **local_scanner detects files with unparseable frontmatter/docstring** | **Done v1.1.0** |
| **Invalid file archiving** | **skill_installer archives invalid files to .invalid_files/ with reason** | **Done v1.1.0** |
| **Auto Issue creation** | **invalid_file_notifier auto-creates GitHub Issue for invalid files** | **Done v1.1.0** |
| **Health check** | **daemon_health_check verifies module cache, frontmatter extraction, filename cleaning** | **Done v1.1.0** |

## Usage

### 1. Environment Setup

Create `~/.workbuddy/skills/github-skill-organizer/.env`:

    GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    GITHUB_OWNER=nervlin4444
    GITHUB_REPO=ai.skills.incubation

### 2. Sync Skill to GitHub

```bash
python scripts/github_repo_sync.py \
  --local-dir ~/.workbuddy/skills/my-skill \
  --repo-name ai.skills.incubation
```

### 3. Clone Repo to Local

```bash
python scripts/github_repo_sync.py \
  --clone \
  --repo-name ai.skills.incubation \
  --clone-method credential
```

### 4. Check Sync Status

```bash
# Compare local vs remote differences
python scripts/sync_engine.py compare --skill-dir ~/.workbuddy/skills/my-skill
```

### 5. Issue Report (v1.0.12+)

When sync issues or skill defects need reporting, use standard Issue reporter:

```bash
# Interactive generation
python scripts/skill_issue_reporter.py \
  --skill-dir ~/.workbuddy/skills/my-skill \
  --interactive \
  --output-dir ./improve/issues

# Programmatic generation (Agent recommended)
cat issue_input.json | python scripts/skill_issue_reporter.py \
  --skill-dir ~/.workbuddy/skills/my-skill \
  --from-stdin
```

**Supporting files**:
- `references/CONTRIBUTING.md` - Standard Issue report format specification (structured template + JSON)
- `scripts/skill_issue_reporter.py` - Issue report generator (forced format, auto-classification, word count validation)

**Classification standards**:
| Category | Description | Handling |
|----------|-------------|----------|
| [FRAMEWORK] | Architecture decision issues | Report to owner |
| [RUNTIME] | Runtime logic errors | Agent self-fix |
| [AGENT-BUG] | Agent violates rules | Agent self-fix, log record |

### 6. Invalid File Handling (v1.1.0+)

When daemon detects files with unparseable frontmatter:

```bash
# 1. Check invalid files directory
ls ~/.workbuddy/skills_moved/.invalid_files/

# 2. Check invalid file logs
ls ~/.workbuddy/skills/github-skill-organizer/logs/invalid_files/

# 3. Check GitHub Issues (auto-created by invalid_file_notifier)
# Issues titled: [INVALID] [skill_name] file_name - reason
```

**Do NOT manually move files from .invalid_files/ back to Downloads.**
Wait for owner-assigned fix task, then regenerate via skill_files_designer.

### 7. Daemon Health Check (v1.1.0+)

After replacing any .py file, run health check before restarting daemon:

```bash
cd ~/.workbuddy/skills/github-skill-organizer
python3 scripts/daemon_health_check.py
```

Expected output: `ALL CHECKS PASSED`
If any FAIL, report to owner immediately.

## fixes Field Description (v1.0.13+)

All skill files frontmatter must include `fixes` field:

```yaml
fixes: []        # No associated Issue (new/enhancement/docs)
fixes: [4]       # Fix Issue #4
fixes: [4, 5]    # Fix multiple Issues at once
```

Upload script auto-scans all file frontmatter:
- Extract fixes list (integer list)
- Merge and deduplicate
- Auto append Fixes #N to commit message
- GitHub auto-closes corresponding Issue

## Version History

| Version | Date | Changes | Author | Verified |
|---------|------|---------|--------|----------|
| 1.1.0 | 2026-05-23 | Add local_scanner v1.0.8 (invalid file detection), skill_installer v1.0.7 (invalid archiving), invalid_file_notifier v1.0.0 (auto Issue creation), daemon_health_check v1.0.1 (module cache verification); add LOCK-009/010, MUST-004/005 | Kevin Lin | Done |
| 1.0.15 | 2026-05-23 | Fix change_classifier API docs (Issue #16): all examples use ChangeClassifier().classify(); retain classify_change() backward-compatible wrapper | Kevin Lin | Done |
| 1.0.14 | 2026-05-23 | Add change_classifier.py docs (Issue #13); mandatory 3-step upload workflow | Kevin Lin | Done |
| 1.0.13 | 2026-05-23 | Unified frontmatter format (fixes field, remove {baseDir}, single file_mapping); sync_engine.py safe classification access (Issue #12) | Kevin Lin | Done |
| 1.0.12 | 2026-05-22 | Add skill_issue_reporter.py + CONTRIBUTING.md | Kevin Lin | Done |
| 1.0.11 | 2026-05-22 | Subdirectory filter, local_only detection, forced CLI upload, skill_dir_name fix, expanduser path expansion, _is_excluded_path filter, CHANGELOG sync, LICENSE exclusion | Kevin Lin | Done |
| 1.0.10 | 2026-05-21 | Fix local_dir pointing to skills parent directory causing all skills upload bug | Kevin Lin | Done |
| 1.0.9 | 2026-05-21 | Emergency fix local_dir calculation error | Kevin Lin | Done |
| 1.0.8 | 2026-05-21 | Add CHANGELOG.md CI post-processing, sync_changelog() | Kevin Lin | Done |
| 1.0.7 | 2026-05-21 | Fix upload_skill circular validation error | Kevin Lin | Done |
| 1.0.6 | 2026-05-21 | Fix upload_skill repeated frontmatter reading | Kevin Lin | Done |
| 1.0.5 | 2026-05-21 | Fix compare_skill path prefix misalignment, action detection missing local_only | Kevin Lin | Done |
| 1.0.4 | 2026-05-21 | Initial version, basic sync functionality | Kevin Lin | Done |

## Supporting Files

| File | Description |
|------|-------------|
| scripts/github_repo_sync.py | Batch sync upload script (github-restful-api-connector skill) |
| scripts/sync_engine.py | Core sync engine (compare/upload/sync) |
| scripts/change_classifier.py | Change classifier (mandatory step for upload) |
| scripts/skill_issue_reporter.py | Standard Issue report generator (v1.0.12+, v1.0.13 uses unified interface) |
| scripts/scheduler_daemon.py | Scheduled daemon process |
| scripts/local_scanner.py | Download folder scanner with invalid file detection (v1.0.8) |
| scripts/skill_installer.py | Skill file installer with invalid archiving (v1.0.7) |
| scripts/invalid_file_notifier.py | Auto GitHub Issue creator for invalid files (v1.0.0) |
| scripts/daemon_health_check.py | Daemon environment verification (v1.0.1) |
| references/CONTRIBUTING.md | Standard Issue report format specification |
| .github/workflows/release.yml | semantic-release configuration |
| .releaserc.json | Version release rules |