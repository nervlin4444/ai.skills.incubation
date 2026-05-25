---
title: Kimi Agent Tracker Usage Manual
name: kimi-agent-tracker
description: Human-readable usage guide for the Kimi file download automation suite. CLI commands, troubleshooting, and incremental pipeline workflow.
version: v1.3.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T16:53:00+0800
fixes: []
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/USAGE.md"
  github_path: "kimi-agent-tracker/USAGE.md"
---

# Kimi Agent Tracker - Usage Manual v1.3.0

## Prerequisites

```bash
# Install dependencies
python3 -m pip install playwright nest_asyncio

# Install browser (one-time)
python3 -m playwright install chromium

# Verify login profile exists
ls ~/.kimi_auth/browser_profile_chromium/
```

## CLI Reference

### kimi_downloader.py

| Command | Purpose | Example |
|---|---|---|
| `--url URL` | Full pipeline for single conversation | `python3 scripts/kimi_downloader.py --url "https://www.kimi.com/chat/ID"` |
| `--url URL --discover-only` | Scan and add to pending, no download | `python3 scripts/kimi_downloader.py --url URL --discover-only` |
| `--process-pending` | Download all pending.json items | `python3 scripts/kimi_downloader.py --process-pending` |
| `--from-list PATH` | Batch from conversations.json | `python3 scripts/kimi_downloader.py --from-list .config/conversations.json` |
| `--visible` | Run browser in visible mode | Add to any command above |
| `--no-dedup` | Disable deduplication | Add to any command above |
| `--download-dir PATH` | Override download directory | `--download-dir ~/MyDownloads` |
| `--pending-record PATH` | Override pending.json path | `--pending-record ./custom_pending.json` |

### tracker_daemon.py

| Command | Purpose |
|---|---|
| `--start` | Start daemon in background |
| `--stop` | Stop running daemon |
| `--status` | Check if daemon is running |
| `--run-once` | Execute single cycle and exit |
| `--visible` | Use visible browser for all downloads |
| `--interval N` | Cycle interval in seconds (default: 900) |
| `--max-conversations N` | Max conversations per cycle (default: 3) |
| `--timeout N` | Timeout per conversation in seconds (default: 600) |

### kimi_login_manager.py

| Command | Purpose |
|---|---|
| `--validate` | Check if login session is valid |
| `--force-login` | Force re-login (opens browser for SMS) |
| `--diagnose` | Run diagnostic checks |

### kimi_conversation_lister.py

Run without arguments. Outputs conversation list to `.config/conversations.json`.

## Incremental Pipeline Workflow

### Day 1: Initial Setup

```bash
# 1. Validate login
python3 scripts/kimi_login_manager.py --validate

# 2. List conversations
python3 scripts/kimi_conversation_lister.py

# 3. Discover all files (add to pending)
python3 scripts/kimi_downloader.py --from-list .config/conversations.json --discover-only

# 4. Check pending queue
cat .config/pending.json | python3 -m json.tool | grep filename

# 5. Process pending queue
python3 scripts/kimi_downloader.py --process-pending
```

### Day 2+: Incremental Update

```bash
# Start daemon (auto-runs every 15 minutes)
python3 scripts/tracker_daemon.py --start

# Or manual incremental run
python3 scripts/tracker_daemon.py --run-once
```

The daemon will:
1. Check for new conversations
2. Discover new files (add to pending)
3. Skip already-downloaded files (checks downloads.json)
4. Download only new pending items
5. Update state files

## State File Inspection

```bash
# Check pending queue
python3 -c "import json; d=json.load(open('.config/pending.json')); print(f'Pending: {len(d["pending"])} items')"

# Check download history
python3 -c "import json; d=json.load(open('.config/downloads.json')); print(f'Downloaded: {len(d["downloaded"])} files')"

# Find duplicates
ls ~/skills_moved/.duplicate_downloads/
```

## Troubleshooting

### Issue: "No file links found"

- Conversation may have no file attachments
- Try `--visible` mode to see actual page state
- Check if conversation is accessible (not deleted)

### Issue: "Preview panel not found" (for .py files)

- Kimi preview loading is slow. Increase `max_wait_attempts` in config.json
- Try `--visible` mode to observe preview panel behavior
- Check if file is actually a text file (not corrupted)

### Issue: "All strategies failed" (for binary files)

- Binary files require visible mode. Ensure `--visible` is used
- Check if browser profile has valid login session
- Verify download directory permissions

### Issue: Daemon timeout

- Increase `per_conversation_timeout_sec` in config.json (default: 600)
- Reduce `max_conversations_per_cycle` (default: 3)
- Check if specific conversation has many files (47+ files = slow)

### Issue: "Duplicate moved" but file is new

- Deduplication uses SHA256 hash. If two files have identical content, they are duplicates
- To force re-download: `--no-dedup` or delete entry from downloads.json

### Issue: Pending queue grows indefinitely

- Some files may consistently fail. Check `retry_count` in pending.json
- After max retries, item is skipped but remains in pending
- Manual cleanup: edit pending.json and remove stuck items

## File Locations

| Purpose | Default Path |
|---|---|
| Downloaded files | `~/Downloads/` |
| Duplicate files | `~/skills_moved/.duplicate_downloads/` |
| Browser profile | `~/.kimi_auth/browser_profile_chromium/` |
| Config | `~/.workbuddy/skills/kimi-agent-tracker/.config/kimi_tracker_config.json` |
| Downloads record | `~/.workbuddy/skills/kimi-agent-tracker/.config/downloads.json` |
| Pending queue | `~/.workbuddy/skills/kimi-agent-tracker/.config/pending.json` |
| Conversation cache | `~/.workbuddy/skills/kimi-agent-tracker/.config/conversations.json` |
| Daemon log | `~/.workbuddy/skills/kimi-agent-tracker/.logs/daemon.log` |
| Diagnostic screenshots | `~/.workbuddy/skills/kimi-agent-tracker/.logs/diagnose/` |

## Configuration Tuning

Edit `.config/kimi_tracker_config.json`:

```json
{
  "download": {
    "extraction": {
      "max_wait_attempts": 15,
      "wait_interval_sec": 5,
      "min_content_length": 50
    },
    "anchor_injection": {
      "timeout_sec": 30
    }
  },
  "daemon": {
    "max_conversations_per_cycle": 2,
    "per_conversation_timeout_sec": 900,
    "interval_sec": 1800
  }
}
```

## Safety Rules

- Never delete `downloads.json` unless you want to re-download everything
- Backup `pending.json` before manual editing
- Daemon `--stop` sends SIGTERM; if stuck, use `--stop` twice or `kill -9 PID`
- Visible mode windows are moved off-screen but still consume resources; close when done
