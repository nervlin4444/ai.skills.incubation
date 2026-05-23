---
title: "GitHub Skill Organizer - Usage Guide"
name: github-skill-organizer
description: "Human-readable usage guide for github-skill-organizer. v1.1.0 adds documentation for local_scanner v1.0.8, skill_installer v1.0.7, invalid_file_notifier v1.0.0, daemon_health_check v1.0.1, and the mandatory daemon restart workflow after .py file replacement. Retains v1.0.15 change_classifier API documentation."
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
  local_path: "scripts/USAGE.md"
  github_path: "github-skill-organizer/scripts/USAGE.md"
---

# github-skill-organizer Usage Guide

Version: v1.1.0
Last Updated: 2026-05-23 23:00:00
Core Changes: v1.1.0 adds invalid file detection, auto-notification, health check, and daemon restart workflow documentation.

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Mandatory 3-Step Upload Workflow](#2-mandatory-3-step-upload-workflow)
3. [Script Reference](#3-script-reference)
4. [Invalid File Handling](#4-invalid-file-handling)
5. [Daemon Health Check](#5-daemon-health-check)
6. [Daemon Restart Workflow](#6-daemon-restart-workflow)
7. [FAQ](#7-faq)
8. [Version History](#8-version-history)

## 1. Quick Start

### 1.1 Environment Setup

Create `~/.workbuddy/skills/github-skill-organizer/.env`:

    GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    GITHUB_OWNER=nervlin4444
    GITHUB_REPO=ai.skills.incubation

### 1.2 Install Dependencies

    cd ~/.workbuddy/skills/github-skill-organizer
    pip install -r requirements.txt  # if available

## 2. Mandatory 3-Step Upload Workflow

WARNING: Uploading skills to GitHub MUST strictly follow the 3-step sequence. Skipping any step causes errors.

### Step 1: Compare Local vs GitHub (compare_skill)

```python
from scripts.sync_engine import SyncEngine

engine = SyncEngine()
skill_name = "my-skill"
local_dir = "~/.workbuddy/skills/my-skill"

# Compare local vs GitHub
comparison = engine.compare_skill(skill_name, local_dir)

# Check results
if comparison["action"] == "identical":
    print("Local and GitHub fully identical, no upload needed")
    exit(0)
elif comparison["action"] == "github_ahead":
    print("GitHub version newer, recommend pull first")
    exit(1)

print(f"Action: {comparison["action"]}")
print(f"Modified: {comparison["modified_files"]}")
print(f"New files: {comparison["local_only_files"]}")
```

Note: `compare_skill()` return value LACKS `approval_required`, `bump_type`, `new_version`, `reason`. Cannot directly pass to `upload_skill()`.

### Step 2: Classify Changes (change_classifier - MANDATORY)

```python
from pathlib import Path
from scripts.change_classifier import ChangeClassifier

# MUST call: produce complete classification
classifier = ChangeClassifier()
changed_files = comparison.get("modified_files", []) + comparison.get("local_only_files", [])
skill_name = Path(comparison.get("local_dir", ".")).name
classification = classifier.classify(skill_name, changed_files)

print(f"Approval required: {classification["approval_required"]}")
print(f"Bump type: {classification["bump_type"]}")
print(f"New version: {classification["new_version"]}")
print(f"Reason: {classification["reason"]}")

# If owner confirmation needed
if classification["approval_required"]:
    print("WARNING: This upload requires owner confirmation. Please review changes then manually set approval_required=False")
    exit(1)
```

Backward-compatible wrapper function (v1.0.15 Issue #16 added, equivalent to above 4 lines):

```python
from scripts.change_classifier import classify_change

# One line, auto-extracts skill_name and changed_files
classification = classify_change(comparison)
```

Why MUST call change_classifier?

| Field | compare_skill() | ChangeClassifier().classify() | Purpose |
|-------|-----------------|------------------------------|---------|
| action | Yes | Yes | Determine sync direction |
| modified_files | Yes | Yes | List changed files |
| approval_required | No | Yes | Determine if owner confirmation needed |
| bump_type | No | Yes | Commit message type (major/minor/patch) |
| new_version | No | Yes | New version number |
| reason | No | Yes | Change reason description |
| current_version | No | Yes | Current version number |
| file_count | No | Yes | Number of changed files |
| has_forbidden | No | Yes | Whether forbidden pattern triggered |
| has_hardcode | No | Yes | Whether hardcoded path detected |

### Step 3: Upload (upload_skill)

```python
from pathlib import Path

# Prepare file list (modified + local_only)
files = []
for fname in comparison["modified_files"] + comparison["local_only_files"]:
    fpath = Path(local_dir) / fname
    if fpath.exists():
        files.append(fpath)

# Upload (pass complete classification)
result = engine.upload_skill(skill_name, files, classification)

if result["status"] == "uploaded":
    print(f"Upload success: {result["commit_message"]}")
else:
    print(f"Upload failed: {result.get("error", "Unknown error")}")
```

### Complete Example (No Steps Skipped)

```python
#!/usr/bin/env python3
"""Complete 3-step upload example - v1.0.15 Issue #16 corrected version"""

from pathlib import Path
from scripts.sync_engine import SyncEngine
from scripts.change_classifier import ChangeClassifier

# Config
SKILL_NAME = "my-skill"
LOCAL_DIR = "~/.workbuddy/skills/my-skill"

# Step 1: Compare
engine = SyncEngine()
comparison = engine.compare_skill(SKILL_NAME, LOCAL_DIR)

if comparison["action"] == "identical":
    print("No upload needed")
    exit(0)

if comparison["action"] == "github_ahead":
    print("GitHub newer, please pull first")
    exit(1)

# Step 2: Classify (MANDATORY)
classifier = ChangeClassifier()
changed_files = comparison.get("modified_files", []) + comparison.get("local_only_files", [])
skill_name = Path(comparison.get("local_dir", ".")).name
classification = classifier.classify(skill_name, changed_files)

if classification["approval_required"]:
    print(f"Owner confirmation needed: {classification["reason"]}")
    exit(1)

# Step 3: Upload
files = [Path(LOCAL_DIR) / f for f in
         comparison["modified_files"] + comparison["local_only_files"]]
files = [f for f in files if f.exists()]

result = engine.upload_skill(SKILL_NAME, files, classification)
print(f"Result: {result["status"]}")
```

## 3. Script Reference

| Script | Version | Responsibility | How to Call | Output |
|--------|---------|--------------|-------------|--------|
| `sync_engine.py` | 1.0.15 | Core engine (compare/upload/sync_changelog) + Issue #16 auto-defense | `from scripts.sync_engine import SyncEngine` | comparison dict / upload result dict |
| `change_classifier.py` | 1.0.1 | **Change classifier (MANDATORY step)** | `from scripts.change_classifier import ChangeClassifier` | classification dict |
| `skill_issue_reporter.py` | 1.0.13 | Issue report generator | `python scripts/skill_issue_reporter.py --skill-dir <path>` | Issue markdown + JSON |
| `scheduler_daemon.py` | 0.2.2 | Scheduled daemon process | `python scripts/scheduler_daemon.py --start` | stdout log to logs/daemon.out |
| `local_scanner.py` | 1.0.8 | Scan Downloads, detect invalid files | `from scripts.local_scanner import LocalScanner` | file_info dict (with is_invalid, reason) |
| `skill_installer.py` | 1.0.7 | Install skill files, archive invalid files | `from scripts.skill_installer import SkillInstaller` | install_result dict |
| `invalid_file_notifier.py` | 1.0.0 | Auto-create GitHub Issue for invalid files | `nohup python scripts/invalid_file_notifier.py --daemon &` | Creates Issue, updates logs/invalid_files/*.json |
| `daemon_health_check.py` | 1.0.1 | Verify daemon environment | `python scripts/daemon_health_check.py` | PASS/FAIL report + specific recommendations |

### change_classifier.py Detailed Usage

**Recommended usage** (direct class method call):

```python
from scripts.change_classifier import ChangeClassifier

classifier = ChangeClassifier()
classification = classifier.classify(skill_name, changed_files)

# Output fields:
#   - bump_type: "major" / "minor" / "patch"
#   - current_version: current version (e.g. "1.2.3")
#   - new_version: auto-calculated new version
#   - approval_required: bool
#   - reason: change reason description
#   - file_count: number of changed files
#   - has_forbidden: whether forbidden pattern triggered
#   - has_hardcode: whether hardcoded path detected
```

**Backward-compatible usage** (wrapper function, v1.0.15 added):

```python
from scripts.change_classifier import classify_change

# Input: compare_skill() return value
# Output: complete dict merging comparison + classification
classification = classify_change(comparison)
```

Classification rules:

| action | Version Change | approval_required | bump_type |
|--------|---------------|-------------------|-----------|
| identical | None | False | No upload needed |
| local_ahead | patch | False | patch |
| local_ahead | minor | False | minor |
| local_ahead | major | **True** | major |
| github_ahead | Any | False | Recommend pull first |
| diverged | Any | **True** | Requires manual judgment |

## 4. Invalid File Handling (v1.1.0+)

### 4.1 What is an Invalid File?

An invalid file is a skill file that has frontmatter/docstring markers (""" and ---) but local_scanner cannot extract the `name` field. Common causes:

- Docstring structure error: `---` followed by non-whitespace text before closing `"""`
- Using single quotes `'''` for docstring but local_scanner version < 1.0.8
- Frontmatter YAML syntax error

### 4.2 Automatic Handling Flow

```
[local_scanner scans Downloads]
  -> Detects .py file with """ and --- but cannot extract name
  -> Marks is_invalid=True, reason="py_docstring_frontmatter_unparseable"
[skill_installer processes]
  -> Archives to skills_moved/.invalid_files/ (NOT .unclassified/)
  -> Logs to logs/invalid_files/invalid_{timestamp}.json
  -> Log format: {"status": "pending", "file": "...", "reason": "...", "timestamp": "..."}
[invalid_file_notifier background daemon]
  -> Checks logs/invalid_files/ every 60 seconds
  -> Finds status=pending record -> Auto-creates GitHub Issue
  -> Issue title: [INVALID] [skill_name] file_name - reason
  -> Issue content: Root cause analysis + Fix steps + Auto-Close conditions
  -> Updates log status="notified", records issue_number
[Agent fixes file (assigned by owner)]
  -> Regenerates correct version via skill_files_designer
  -> Upload commit message includes Fixes #N
  -> GitHub auto-closes Issue
```

### 4.3 Manual Inspection Commands

```bash
# Check invalid files directory
ls ~/.workbuddy/skills_moved/.invalid_files/

# Check invalid file logs
ls ~/.workbuddy/skills/github-skill-organizer/logs/invalid_files/

# View specific invalid file log
cat ~/.workbuddy/skills/github-skill-organizer/logs/invalid_files/invalid_20260523_221500.json
```

### 4.4 Prohibited Actions

- **DO NOT** manually move files from `.invalid_files/` back to Downloads (causes circular archiving)
- **DO NOT** manually delete logs in `logs/invalid_files/`
- **DO NOT** manually create GitHub Issues for invalid files (notifier handles this automatically)
- Wait for owner-assigned fix task, then regenerate via `skill_files_designer`

## 5. Daemon Health Check (v1.1.0+)

### 5.1 When to Run

Run health check in these scenarios:

- After replacing any `.py` file in `scripts/`
- After updating `local_scanner.py` or `skill_installer.py`
- When daemon behaves unexpectedly (files wrongly classified)
- Before restarting daemon after any script update

### 5.2 How to Run

```bash
cd ~/.workbuddy/skills/github-skill-organizer
python3 scripts/daemon_health_check.py
```

### 5.3 Expected Output

```
======================================================================
DAEMON HEALTH CHECK v1.0.1
Timestamp: 2026-05-23T22:15:00.000000+00:00
======================================================================
[1/5] MODULE CACHE CHECK
  No cached modules found (good - fresh import)
[2/5] LOADING MODULES (bypass cache)
  local_scanner: loaded
  skill_installer: loaded
[3/5] FRONTMATTER EXTRACTION TEST
  [PASS] md_standard.md: extracted=test-md, expected=test-md
  [PASS] py_double_quote.py: extracted=test-py-dq, expected=test-py-dq
  [PASS] py_single_quote.py: extracted=test-py-sq, expected=test-py-sq
[4/5] FILENAME CLEANING TEST
  [PASS] skill_patch_validator_v1.3.0.20260523125716.py -> skill_patch_validator_v1.3.0.py
  [PASS] github_repo_sync_v0.3.3.20260523125615.py -> github_repo_sync_v0.3.3.py
  [PASS] SKILL_v1.3.1.20260523125716.md -> SKILL_v1.3.1.md
  [PASS] normal_file.py -> normal_file.py
[5/5] DAEMON PROCESS CHECK
  Daemon RUNNING:
    ... (PID info)
  ACTION REQUIRED: If you replaced any .py files, restart daemon:
    pkill -f scheduler_daemon
    python3 scripts/scheduler_daemon.py --start

======================================================================
SUMMARY
======================================================================
ALL CHECKS PASSED
```

### 5.4 What Each Check Does

| Check | Purpose | Failure Indication |
|-------|---------|-------------------|
| Module Cache Check | Detect old module cache in sys.modules | Old version still cached |
| Module Loading | Force reimport local_scanner + skill_installer | ImportError or wrong version |
| Frontmatter Extraction | Test `"""` and `'''` docstring formats | FAIL = local_scanner cannot parse your files |
| Filename Cleaning | Remove version+timestamp suffixes | FAIL = files keep wrong names after installation |
| Daemon Process Check | Show running daemon status and restart instructions | Not running or wrong PID |

## 6. Daemon Restart Workflow (v1.1.0+)

### 6.1 Why Restart is Mandatory

Python `sys.modules` caches imported modules in memory. Replacing a `.py` file on disk does NOT automatically update the cached module. The daemon process continues using the old version until restarted.

**Consequences of not restarting:**
- New files still classified using old local_scanner logic
- Invalid files go to `.unclassified/` instead of `.invalid_files/`
- Filename cleaning uses old regex patterns
- Health check passes but daemon behavior remains wrong

### 6.2 Correct Restart Procedure

```bash
# Step 1: Stop daemon
pkill -f scheduler_daemon

# Step 2: Verify file versions
grep "version:" ~/.workbuddy/skills/github-skill-organizer/scripts/local_scanner.py
# Expected: version: 1.0.8
grep "version:" ~/.workbuddy/skills/github-skill-organizer/scripts/skill_installer.py
# Expected: version: 1.0.7

# Step 3: Run health check
cd ~/.workbuddy/skills/github-skill-organizer
python3 scripts/daemon_health_check.py
# Expected: ALL CHECKS PASSED

# Step 4: Start daemon
python3 scripts/scheduler_daemon.py --start

# Step 5: Verify daemon started
ps aux | grep scheduler_daemon | grep -v grep
```

### 6.3 Verify After Restart

Check daemon log for correct version loading:

```bash
tail -20 ~/.workbuddy/skills/github-skill-organizer/logs/daemon.out
```

Expected lines:
- `Daemon started (PID: XXXX), interval=60s`
- `FIRST_CYCLE: Force full scan enabled`
- No `[ARCHIVE] ... (no frontmatter/name)` for files that should have valid frontmatter

## 7. FAQ

### Q: Why can't compare_skill() directly pass to upload_skill()?

`compare_skill()` only compares file differences, not upload strategy. `upload_skill()` needs:
- Is this change major/minor/patch? (bump_type)
- Does it need owner confirmation? (approval_required)
- What is the new version number? (new_version)
- What is the change reason? (reason)

These are determined by `ChangeClassifier().classify()` based on change content.

### Q: What happens if I skip change_classifier?

Before v1.0.13: Direct `KeyError: approval_required` crash.
After v1.0.14: `upload_skill()` auto-detects missing fields and attempts auto `classify_change()` completion. But this is defense mechanism, not to be relied upon. **Correct approach is still explicit ChangeClassifier().classify().**

### Q: Can old code using classify_change() still work?

v1.0.15 added `classify_change()` wrapper function in `change_classifier.py`. Old code works without modification. But **recommended migration** to new API `ChangeClassifier().classify()` because:
- More explicit parameter control (skill_name, changed_files, diff_summary)
- Better Python class design convention
- Documentation and examples use new API as standard

### Q: Where is change_classifier?

    github-skill-organizer/scripts/change_classifier.py

If not found, confirm skill package is fully downloaded.

### Q: How to determine if owner confirmation needed?

```python
if classification["approval_required"]:
    print("Owner confirmation needed")
else:
    print("Can auto-upload")
```

Usually major version changes (e.g. 1.0.0 -> 2.0.0) or diverged status require confirmation.

### Q: Why are my files going to .unclassified/ instead of the correct skill directory?

Possible causes:
1. **Daemon not restarted after local_scanner update** (most common) - Follow Section 6 restart workflow
2. **File has invalid frontmatter structure** - Check `.invalid_files/` directory
3. **File uses single-quote docstring `'''`** - Requires local_scanner >= 1.0.8
4. **Filename has version+timestamp suffix** - Requires skill_installer >= 1.0.7

Diagnostic steps:
```bash
# Check which directory files went to
ls ~/.workbuddy/skills_moved/.unclassified/
ls ~/.workbuddy/skills_moved/.invalid_files/
ls ~/.workbuddy/skills_moved/.identical/

# Run health check
cd ~/.workbuddy/skills/github-skill-organizer
python3 scripts/daemon_health_check.py
```

### Q: What should I do when I see `[INVALID]` Issues on GitHub?

1. Read the Issue for specific file and reason
2. Download the invalid file from `.invalid_files/` for inspection
3. Use `skill_files_designer` to regenerate correct version
4. Upload with `Fixes #N` in commit message
5. GitHub auto-closes the Issue

Do NOT manually close `[INVALID]` Issues - let the fix commit auto-close them.

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-05-23 | Add local_scanner v1.0.8, skill_installer v1.0.7, invalid_file_notifier v1.0.0, daemon_health_check v1.0.1 documentation; add Invalid File Handling section (4), Daemon Health Check section (5), Daemon Restart Workflow section (6); add FAQ entries for .unclassified/ and [INVALID] Issues |
| 1.0.15 | 2026-05-23 | Fix change_classifier API docs (Issue #16): all examples use `ChangeClassifier().classify()`; retain `classify_change()` backward-compatible wrapper |
| 1.0.14 | 2026-05-23 | Add mandatory 3-step upload workflow docs (compare -> classify -> upload); add change_classifier.py usage instructions; complete example code |
| 1.0.13 | 2026-05-23 | Unified frontmatter format; sync_engine.py safe classification access (Issue #12) |
| 1.0.12 | 2026-05-22 | Add skill_issue_reporter.py + CONTRIBUTING.md |
| 1.0.11 | 2026-05-22 | Subdirectory filter, local_only detection, forced CLI upload, CHANGELOG sync |
| 1.0.10 | 2026-05-21 | expanduser(~) path expansion fix |
| 1.0.9 | 2026-05-21 | local_dir path derivation fix |
| 1.0.8 | 2026-05-21 | CHANGELOG.md CI post-processing, sync_changelog() |
| 1.0.5 | 2026-05-21 | compare_skill path prefix filter + action detection fix |
| 1.0.4 | 2026-05-21 | Initial version, basic sync functionality |