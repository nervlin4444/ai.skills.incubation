---
title: Kimi Agent Tracker v4.0.0
name: kimi-agent-tracker
description: Automated file extraction from Kimi chat pages using Playwright. Supports .py/.md/.json/.zip downloads via proven selector-agnostic strategies. Includes persistent login, conversation listing, auto-download, and daemon mode.
version: "4.0.0"
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: "2026-05-26T06:53:23.027+00:00"
auth_config:
  provider: none
  auth_method: none
  token_env_var: none
  env_file_path: none
file_mapping:
  local_path: "{baseDir}/SKILL.md"
  github_path: "kimi-agent-tracker/SKILL.md"
---

# Kimi Agent Tracker v3.6.1

## 1. Identity and Purpose

You are the Kimi Agent Tracker skill execution engine. Your sole purpose is to automate file extraction from Kimi (kimi.com) chat conversations using Playwright browser automation.

Scope boundary:
- In-scope: Login persistence, conversation scanning, file detection, auto-download, daemon mode.
- Out-of-scope: GitHub upload (delegate to github-skill-organizer), file content analysis (delegate to agent-skill-improving).

## 2. Directory Structure

    kimi-agent-tracker/
    ├── SKILL.md                          <- This file. LLM execution instructions.
    ├── README.md                         <- Human-readable overview and quickstart.
    ├── scripts/
    │   ├── kimi_downloader.py            <- Main download script v3.6.1
    │   ├── kimi_selector_probe.py        <- Diagnostic probe v1.0.8 (for selector debugging)
    │   ├── kimi_login_persistent.py      <- Persistent browser login (7-14 day session)
    │   ├── kimi_conversation_lister.py   <- List all conversations with file counts
    │   └── tracker_daemon.py             <- Daemon wrapper for continuous monitoring
    ├── config/
    │   └── tracker_config.json           <- Daemon configuration (auto-created on first run)
    ├── data/
    │   └── last_processed.json           <- Tracks already-downloaded files (deduplication state)
    ├── assets/
    │   ├── WEB.CORRECTIONS.md            <- Browser automation anti-patterns (mandatory read before debugging)
    │   └── USAGE.md                      <- Human usage tutorial with screenshots.
    └── logs/
        └── tracker.log                   <- Daemon execution log.

**Path rule:** All skill data stays under skill directory. NO files in ~/.kimi_auth/ except browser profile (managed by login script).

## 3. Prerequisites

Before any script execution, verify these dependencies. If missing, emit installation commands and STOP.

    python3 --version          # Requires 3.10+
    python3 -m pip --version
    python3 -c "import playwright; print('playwright OK')"
    python3 -m playwright --version

If playwright not installed:

    python3 -m pip install playwright pyperclip
    python3 -m playwright install chromium

Persistent profile directory (auto-created by login script):

    ~/.kimi_auth/browser_profile_chromium/

## 4. Execution Order (One-Shot Mode)

For manual single-run extraction, execute in this exact order:

Step 1: Login (if session expired)

    python3 scripts/kimi_login_persistent.py

Step 2: List conversations with files

    python3 scripts/kimi_conversation_lister.py

Step 3: Download files from target conversation

    python3 scripts/kimi_downloader.py       --url "https://www.kimi.com/chat/CONVERSATION_ID"       --visible       --max-files 20

Output: All files saved to ~/Downloads/ with original filenames.

## 5. Daemon Mode (Continuous Monitoring)

Daemon monitors configured conversations and auto-downloads new files. Zero-config on first run.

### 5.1 Quick Start (3 Commands)

    # 1. Edit config to add conversation URLs
    vim config/tracker_config.json

    # 2. Start daemon
    python3 scripts/tracker_daemon.py --start

    # 3. Check status / stop
    python3 scripts/tracker_daemon.py --status
    python3 scripts/tracker_daemon.py --stop

### 5.2 Config File (Auto-Created)

First run auto-creates `config/tracker_config.json`:

    {
      "poll_interval_seconds": 300,
      "conversations": [
        {
          "url": "https://www.kimi.com/chat/CONVERSATION_ID_1",
          "label": "project-alpha",
          "max_files_per_run": 10
        }
      ],
      "download_dir": "~/Downloads",
      "headless": true,
      "deduplication": true
    }

Edit the "conversations" array to add your target URLs. All other fields are optional.

### 5.3 Daemon Behavior
- Polls each conversation URL every N seconds (default 300s = 5min).
- Detects new files not in data/last_processed.json state.
- Auto-downloads new files to configured directory.
- Logs all actions to logs/tracker.log.
- Skips already-downloaded files when deduplication enabled.

### 5.4 Foreground Mode (Debugging)

    python3 scripts/tracker_daemon.py --start --foreground

Runs in current terminal without forking. Useful for debugging. Ctrl+C to stop.

## 6. Selector Probe (Debugging)

When download fails on a new Kimi UI version, run the diagnostic probe to discover working selectors:

    python3 scripts/kimi_selector_probe.py       --url "https://www.kimi.com/chat/CONVERSATION_ID"       --visible       --max-per-type 2

The probe outputs:
- DOM diagnosis (iframe count, shadow hosts, right-side elements, top-right buttons).
- Working content extraction strategy (Monaco API, innerText, download button).
- Screenshots to ~/Downloads/probe_screenshots/ for visual verification.

Before modifying kimi_downloader.py, MUST read assets/WEB.CORRECTIONS.md and follow the Trigger Table to identify the correct checklist.

## 7. Critical Anti-Patterns (from WEB.CORRECTIONS.md)

These mistakes have been proven to waste hours. Never repeat them.

Anti-pattern 1: Using networkidle for SPA navigation
- Wrong: page.goto(url, wait_until="networkidle")
- Right: page.goto(url, wait_until="domcontentloaded") then asyncio.sleep(5.0)
- Reason: Kimi uses WebSocket heartbeat. networkidle never fires.

Anti-pattern 2: Assuming semantic class names
- Wrong: div[class*="file-card-info-name"]
- Right: Read card.text_content() then regex extract filename
- Reason: Vue scoped styles use hash suffixes. Class names are implementation detail.

Anti-pattern 3: Reading pre.innerText for Monaco Editor
- Wrong: await page.wait_for_selector("pre").inner_text()
- Right: window.monaco.editor.getEditors()[0].getValue() OR bounding-box innerText
- Reason: Monaco virtual scrolling only renders visible lines. innerText returns 32 chars.

Anti-pattern 4: Expecting downloads in default browser folder
- Wrong: Assume file appears in ~/Downloads/
- Right: shutil.copy2(temp_path, ~/Downloads/filename)
- Reason: Playwright saves to temp UUID path under /var/folders/...

Anti-pattern 5: Single click method only
- Wrong: await el.click()
- Right: Try force_click -> normal_click -> js_dispatch -> double_click -> child_anchor
- Reason: pointer-events interception and synthetic event systems block standard clicks.

Anti-pattern 6: Putting config/state in system user folders
- Wrong: ~/.kimi_auth/tracker_config.json
- Right: config/tracker_config.json under skill directory
- Reason: System folders may be cleaned or migrated. Skill data stays with skill.

## 8. File Download Strategy Matrix

| File Type | Primary Strategy | Fallback Strategy |
|-----------|-----------------|-------------------|
| .py       | Direct download (expect_download) | Preview panel download button |
| .json     | Direct download (expect_download) | Preview panel download button |
| .zip      | Direct download (expect_download) | Preview panel download button |
| .md       | Preview panel -> download icon    | JS innerText extraction       |
| .env      | Direct download                   | JS innerText extraction       |

## 9. Version History

| Version | Date       | Change Summary |
|---------|------------|--------------|
| v1.0.0  | 2026-05-20 | Initial login + lister scripts |
| v2.0.0  | 2026-05-22 | Persistent profile support |
| v3.0.0  | 2026-05-23 | Auto-download with preview extraction |
| v3.5.0  | 2026-05-25 | Retry mechanism + dual-path scanning |
| v3.6.0  | 2026-05-25 | Proven JS content extraction (D strategy) |
| v3.6.1  | 2026-05-26 | File copy to ~/Downloads/; daemon zero-config; paths under skill dir |

## 10. Interface Boundaries

- File download: This skill handles entirely.
- GitHub upload: Delegate to github-skill-organizer/scripts/skill_validate.py or sync_engine.py.
- File validation: Delegate to agent-skill-improving/scripts/skill_integrity_checker.py.
- Daemon PID management: Delegate to daemon-script-connector when available.

## 11. Emergency Stop Conditions

STOP immediately and report to user if:
- Browser launch fails (Chromium not installed).
- Navigation fails after 3 retries.
- All download strategies fail for 3 consecutive files.
- Persistent profile directory corrupted.

Do NOT attempt to fix by creating temporary scripts. Follow WEB.CORRECTIONS.md checklists instead.
