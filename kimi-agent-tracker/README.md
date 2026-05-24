---
title: "Kimi Agent Tracker - Usage Guide"
name: "kimi-agent-tracker"
description: "Kimi platform automation tracker human-readable guide. Handles conversation list extraction, sandbox file download, SHA256 deduplication archive. Includes standalone daemon mode. v1.0.2 hotfix: F-001 login validation false-positive fixed, loop detection for login completion, diagnose directory isolation."
version: "1.0.2"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T00:10:00+08:00"
fixes: [24]
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/README.md"
  github_path: "kimi-agent-tracker/README.md"
---

# Kimi Agent Tracker

Version: 1.0.2 | Updated: 2026-05-25
Core Fix: v1.0.2 — F-001 login validation false-positive fixed. validate_login() now uses avatar/conversation-item selectors instead of sidebar container. login() uses loop detection instead of blind sleep.

## Table of Contents

1. [Background & Motivation](#1-background--motivation)
2. [Architecture Overview](#2-architecture-overview)
3. [File Inventory](#3-file-inventory)
4. [Installation](#4-installation)
5. [Usage Guide](#5-usage-guide)
6. [Download Mechanisms](#6-download-mechanisms)
7. [Deduplication & File Handling](#7-deduplication--file-handling)
8. [Diagnostic Mode](#8-diagnostic-mode)
9. [Sandbox Version Behavior](#9-sandbox-version-behavior)
10. [Daemon Mode](#10-daemon-mode)
11. [Troubleshooting](#11-troubleshooting)
12. [Directory Structure](#12-directory-structure)
13. [Version History](#13-version-history)

## 1. Background & Motivation

When collaborating with Kimi AI long-term, files generated across multiple conversations (skill packs, reports, scripts) need automated collection. This tracker encapsulates Kimi-specific logic as an independent skill, depending on chrome-playwright-connector for browser capabilities.

## 2. Architecture Overview

    +-------------------+        +-------------------------+
    | kimi-agent-tracker|  -->   | chrome-playwright-      |
    | (Kimi logic)      |        | connector               |
    +-------------------+        | (Generic browser)       |
                                 +-------------------------+
                                          |
                                          v
                                 +-------------------------+
                                 | kimi-agent-tracker/     |
                                 | ├── downloads/          |
                                 | ├── .duplicate/         |
                                 | ├── .config/            |
                                 | │   └── downloads.json  |
                                 | ├── .logs/              |
                                 | │   └── diagnose/       |
                                 | └── scripts/            |
                                 +-------------------------+

## 3. File Inventory

| File | Version | Purpose |
|------|---------|---------|
| kimi_login_manager.py | v1.0.2 | SMS login and persistent profile maintenance |
| kimi_conversation_lister.py | v1.0.2 | Conversation list extraction from sidebar |
| kimi_downloader.py | v1.0.2 | Auto-download core |
| state_manager.py | v1.0.2 | SHA256 deduplication and state tracking |
| tracker_daemon.py | v1.0.2 | Standalone daemon |

## 4. Installation

    # 1. Install dependencies (skip if connector already installed)
    /Users/kevinlinz/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m pip install playwright --user
    /Users/kevinlinz/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m playwright install chromium

    # 2. Ensure connector is deployed in sibling directory
    ls ../chrome-playwright-connector/scripts/browser_connector.py

## 5. Usage Guide

### Step 1: Login (one-time)

    python scripts/kimi_login_manager.py --visible --stay-open 300

### Step 2: Validate Login

    python scripts/kimi_login_manager.py --validate

### Step 3: Extract Conversation List

    python scripts/kimi_conversation_lister.py --count 4 --visible

### Step 4: Batch Download (single)

    python scripts/kimi_downloader.py --from-list .config/conversations.json --visible

### Step 5: Start Daemon (auto-timed)

    python scripts/tracker_daemon.py --start

    # Check status
    python scripts/tracker_daemon.py --status

    # Stop daemon
    python scripts/tracker_daemon.py --stop

    # Single test (foreground)
    python scripts/tracker_daemon.py --run-once

## 6. Download Mechanisms

| File Type | Kimi Behavior | Agent Strategy |
|-----------|---------------|----------------|
| .zip, .py, .csv | Direct browser download | expect_download() capture |
| .md, .txt | Preview panel -> download icon -> format select | Direct click first + retry + preview panel fallback |

## 7. Deduplication & File Handling

- SHA256 deduplication, state saved in .config/downloads.json
- Duplicate files moved to .duplicate/, NEVER deleted
- Unique filename mechanism (_1, _2, _3...)

## 8. Diagnostic Mode

When extraction or download fails, diagnostic results print DIRECTLY to terminal.
Success/failure visible at a glance.

    Example output:
    [DIAGNOSE] Conversation: "POS Terminal Fix"
    [OK]     Sidebar detected: 12 nodes
    [OK]     Download: skill.py (SHA256: a1b2c3...)
    [FAIL]   Download: report.md (timeout)
    [INFO]   HTML dump: .logs/diagnose/sidebar_20260524_105600.html

Diagnostic HTML dumps saved to .logs/diagnose/ (skill-level folder).

## 9. Sandbox Version Behavior

Kimi does NOT retain historical versions. Same sandbox path in different conversations always points to the latest version.

    00:00 Conversation A -> skill.py (v1)
    00:25 Conversation B -> skill.py (v2) -> overwrites same path
    00:35 Conversation C -> skill.py (v3) -> overwrites again

"Old overwrites new" risk does NOT exist in Kimi -> download direction.

## 10. Daemon Mode

Standalone daemon, no external cron/launchd needed.

| Parameter | Description |
|-----------|-------------|
| --start | Background start |
| --stop | Stop |
| --status | Terminal status output |
| --run-once | Foreground single execution |
| --interval N | Cycle interval (default 900s) |
| --count N | Conversations per extraction (default 10) |

Status output example:
    [DAEMON] Status: RUNNING
    [DAEMON] PID: 12345
    [DAEMON] Last cycle: 2026-05-24 10:30:00
    [DAEMON] Downloaded: 27 | Duplicates: 8

## 11. Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Login failed / validate returns True but not logged in | validate_login() false-positive (sidebar skeleton) | v1.0.2 fixed: uses avatar selector. If still fails, use --force-login |
| Browser closes before SMS input | stay_open too short or blind sleep | v1.0.2 fixed: loop detection. Use --stay-open 300 |
| No conversations | Sidebar DOM changed | Use --diagnose, check .logs/diagnose/ |
| Download timeout | expect_download missed | Check .logs/ for retry record |
| Daemon already running | PID file exists | Check --status or --stop |
| ModuleNotFoundError: playwright | Managed Python missing package | Run: python3 -m pip install playwright --user |

## 12. Directory Structure

    {baseDir}/
    ├── .logs/
    │   └── diagnose/
    ├── .config/
    │   ├── downloads.json
    │   └── conversations.json
    ├── downloads/
    ├── .duplicate/
    └── scripts/

## 13. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.2 | 2026-05-25 | Hotfix: F-001 validate_login() false-positive fixed (avatar selector). login() loop detection replaces blind sleep. Diagnose files saved to skill-level .logs/diagnose/. Added playwright dependency check. |
| 1.0.1 | 2026-05-24 | Fix Issue #24: Synchronize all script versions, add version column to file inventory table |
| 1.0.0 | 2026-05-21 | Initial version |

## Author

Kevin Lin (nervlin4444)
