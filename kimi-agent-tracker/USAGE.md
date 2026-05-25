---
title: Kimi Agent Tracker - Usage Guide
name: kimi-agent-tracker
description: Human-readable usage guide for the Kimi Agent Tracker. Covers installation, configuration, CLI commands, and troubleshooting based on v1.2.1 operational experience.
version: "1.2.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T15:01:00+00:00"
auth_config:
  provider: kimi
  auth_method: persistent_profile
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/USAGE.md"
  github_path: "kimi-agent-tracker/USAGE.md"
---

# Kimi Agent Tracker - Usage Guide v1.2.1

## Installation

```bash
# 1. Install Python dependencies
python3 -m pip install playwright nest_asyncio

# 2. Install Playwright Chromium browser
python3 -m playwright install chromium

# 3. Verify installation
python3 scripts/kimi_login_manager.py --help
```

## Configuration

All settings are in `.config/kimi_tracker_config.json`:

```json
{
  "platform": {
    "base_url": "https://www.kimi.com"
  },
  "login": {
    "timeout_sec": 30,
    "max_retry": 2
  },
  "daemon": {
    "interval_sec": 900,
    "visible": false,
    "conversation_count": 10,
    "download_dir": "~/Downloads",
    "duplicate_dir": "~/skills_moved/.duplicate_downloads"
  },
  "download": {
    "deduplicate": true,
    "unique_filename": true,
    "strategy": "extraction",
    "extraction": {
      "preview_selectors": [
        "[class*="preview"]",
        "[class*="panel"]",
        "[class*="drawer"]",
        "[class*="file-view"]",
        "[class*="code"]",
        ".monaco-editor",
        "[role="dialog"]",
        ".ant-drawer",
        "[class*="content"]",
        "[class*="file-preview"]",
        "[class*="doc-preview"]"
      ],
      "content_selectors": [
        "[class*="preview"] pre",
        "[class*="panel"] pre",
        "[class*="code"] pre",
        ".monaco-editor .view-lines",
        "pre[class*="code"]",
        "code[class*="language"]",
        "[class*="markdown-body"]",
        "pre"
      ],
      "min_content_length": 100,
      "max_wait_attempts": 5,
      "wait_interval_ms": 2000
    }
  },
  "logging": {
    "level": "INFO",
    "log_dir": "{baseDir}/.logs"
  }
}
```

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `daemon.interval_sec` | 900 | Seconds between daemon cycles (15 min) |
| `daemon.visible` | false | Run browser in visible mode (set true for debugging) |
| `daemon.download_dir` | ~/Downloads | Where downloaded files are saved |
| `download.deduplicate` | true | Skip files already downloaded (by SHA256) |
| `download.unique_filename` | true | Prefix files with conversation title |
| `download.extraction.min_content_length` | 100 | Minimum chars for valid content extraction |
| `download.extraction.max_wait_attempts` | 5 | Number of retries waiting for preview content |
| `download.extraction.wait_interval_ms` | 2000 | Milliseconds between content check attempts |

## CLI Commands

### F-001: Login Management

```bash
# First-time login (requires SMS verification)
python3 scripts/kimi_login_manager.py --force-login --visible --stay-open 300

# Validate existing session
python3 scripts/kimi_login_manager.py --validate

# Diagnose login state (screenshots + selector analysis)
python3 scripts/kimi_login_manager.py --diagnose
```

### F-002: Conversation Listing

```bash
# List recent conversations
python3 scripts/kimi_conversation_lister.py --count 10

# With diagnostics
python3 scripts/kimi_conversation_lister.py --count 10 --diagnose
```

### F-003: File Download

```bash
# Download from single conversation URL
python3 scripts/kimi_downloader.py --url "https://www.kimi.com/chat/..."

# Batch download from conversation list
python3 scripts/kimi_downloader.py --from-list .config/conversations.json

# Visible mode (for debugging)
python3 scripts/kimi_downloader.py --url "..." --visible
```

### F-005: Daemon Control

```bash
# Start background monitoring
python3 scripts/tracker_daemon.py --start

# Run single cycle (foreground, for testing)
python3 scripts/tracker_daemon.py --run-once

# Check status
python3 scripts/tracker_daemon.py --status

# Stop daemon
python3 scripts/tracker_daemon.py --stop
```

## How Downloads Work (v1.2.1)

### For Text Files (.py, .md, .txt, .json, etc.)

The script uses **Content Extraction** instead of browser download:

1. Clicks the file link in the conversation
2. Waits for Kimi's preview panel to open (right side of screen)
3. Validates the panel is actually a file preview (dimensions > 200x200px, not sidebar)
4. Extracts the file content directly from the preview panel's DOM
5. Validates content length (default: > 100 chars)
6. For .py files: validates presence of `def ` / `import ` / `class `
7. Writes the content to a local file with UTF-8 encoding

This bypasses all browser download dialogs and sandbox:// protocol limitations.

### For Binary Files (.zip, .pdf, .png, etc.)

Falls back to traditional browser download triggering.

## Troubleshooting

### "Preview panel not found" or "Content empty"

The preview panel selector may be matching the wrong element. Check:

```bash
# Run in visible mode to see what's happening
python3 scripts/kimi_downloader.py --url "..." --visible

# Check diagnostic screenshots
ls -lt .logs/diagnose/download/
```

**Common cause (fixed in v1.2.1)**: The selector `[class*="sidebar"]` used to match the conversation sidebar instead of the file preview panel. The script now validates panel dimensions (width > 200px, height > 200px) to exclude the sidebar.

### "42 chars extracted" (content too short)

The script extracted text from the wrong DOM element (e.g., sidebar text instead of file content). The content validation (min 100 chars) should catch this. If it persists:

1. Check `.logs/diagnose/` screenshots
2. Adjust `extraction.content_selectors` in config.json
3. Increase `extraction.max_wait_attempts` if the preview loads slowly

### "Login invalid" when daemon starts

The Kimi session has expired (typically 7-14 days). Re-authenticate:

```bash
python3 scripts/kimi_login_manager.py --force-login --visible --stay-open 300
# Complete SMS verification in the browser window
python3 scripts/kimi_login_manager.py --validate
```

### Files not appearing in ~/Downloads

Check if `download_dir` in config.json uses `~/` (tilde). The script auto-expands this to your home directory. Verify:

```bash
ls -lt ~/Downloads/
# or check config path
python3 -c "import os; print(os.path.expanduser('~/Downloads'))"
```

### Daemon stops with "asyncio loop" error

Install nest_asyncio:

```bash
python3 -m pip install nest_asyncio --user
```

## Operational Notes

### Session Persistence

The persistent profile is saved at `~/.kimi_auth/browser_profile_chromium/`. Do not delete this directory unless you want to force re-authentication.

### Duplicate Handling

Downloaded files are tracked by SHA256 hash in `.config/downloads.json`. If the same file appears in multiple conversations, it will be moved to the `duplicate_dir` instead of overwriting.

### Rate Limiting

If running the daemon with short intervals, be aware that frequent page loads may trigger Kimi's rate limiting. The default 900-second interval is conservative.

## Version History

- **v1.2.1** (2026-05-25): Fixed preview panel selector — added dimension validation (width>200, height>200) to prevent matching conversation sidebar.
- **v1.2.0** (2026-05-25): Content extraction strategy for text files. Bypasses browser download entirely by extracting from Kimi's preview panel DOM.
- **v1.1.0** (2026-05-25): Unified config.json, nest_asyncio fix, removed .env dependency.
- **v1.0.x** (2026-05-24): Initial release with basic Playwright download.
