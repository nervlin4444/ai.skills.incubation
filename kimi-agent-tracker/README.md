---
title: Kimi Agent Tracker Project Overview
name: kimi-agent-tracker
description: Playwright-based automation suite for Kimi AI platform. Extracts conversation metadata and downloads file attachments incrementally.
version: "4.0.0"
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: "2026-05-26T06:53:23.027+00:00"
fixes: []
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/README.md"
  github_path: "kimi-agent-tracker/README.md"
---

# Kimi Agent Tracker v4.0.0

Playwright-based automation suite for the Kimi AI platform. Extracts conversation metadata and downloads file attachments using an incremental pipeline.

## Architecture

```
+---------------+     +---------------+     +---------------+     +---------------+
|  DISCOVERY    | --> | DEDUPLICATE   | --> |   DOWNLOAD    | --> |    RECORD     |
|  (Scan page)  |     | (Check state) |     | (Strategy)  |     | (Update JSON) |
+---------------+     +---------------+     +---------------+     +---------------+
```

## Components

| Component | File | Purpose |
|---|---|---|
| Login Manager | `scripts/kimi_login_manager.py` | Persistent browser profile auth |
| Conversation Lister | `scripts/kimi_conversation_lister.py` | Extract conversation list |
| File Downloader | `scripts/kimi_downloader.py` | Incremental file download pipeline |
| Tracker Daemon | `scripts/tracker_daemon.py` | Background scheduler |
| Config | `.config/kimi_tracker_config.json` | Unified configuration |

## Download Strategy by File Type

| File Type | Strategy | Mode | Avg Speed |
|---|---|---|---|
| `.md`, `.txt`, `.json`, `.csv`, `.yml`, `.yaml`, `.html`, `.js`, `.css`, `.xml`, `.sh`, `.bash` | Anchor Injection | Headless | ~8s |
| `.py` | Preview Extraction | Headless (extended wait) | ~30-60s |
| `.zip`, `.pdf`, `.png`, `.jpg`, `.mp3`, `.mp4`, `.doc`, `.xls`, `.ppt`, `.rar`, `.7z`, `.tar`, `.gz` | Visible Fallback | Visible (off-screen) | ~15-30s |

## State Files

| File | Purpose | Format |
|---|---|---|
| `downloads.json` | Record of successfully downloaded files (SHA256 keyed) | JSON |
| `pending.json` | Queue of discovered but not-yet-downloaded files | JSON |
| `conversations.json` | Cached conversation list from Kimi | JSON |

## Incremental Pipeline

1. **Discovery**: Scan conversation page for all file links.
2. **Deduplication**: Compare against `downloads.json` (already downloaded) and `pending.json` (in queue).
3. **Queue**: New files are added to `pending.json`.
4. **Process**: Download pending files using type-appropriate strategy.
5. **Record**: On success, move from `pending.json` to `downloads.json`.

## Version History

| Version | Key Changes |
|---|---|
| v1.0.0 | Basic login + conversation listing |
| v1.1.0 | File link discovery |
| v1.1.1 | nest_asyncio fix, expand_path fix |
| v1.1.2 | Overlay dismissal, sandbox:// direct download |
| v1.1.3 | Screenshot diagnostics, sidebar selector removal |
| v1.1.4 | Mouse simulation (scroll + hover + click) |
| v1.1.5 | Physical mouse move/down/up |
| v1.1.6 | scrollIntoView + position re-query |
| v1.1.7 | in_viewport check, JS click fallback |
| v1.1.8 | Five-strategy degradation (anchor / mouse / keyboard / JS / fetch) |
| v1.2.0 | Content extraction from preview panel (DOM-based) |
| v1.2.1 | Config-driven extraction, size validation, sidebar removal |
| v1.3.0 | **Incremental download pipeline** (pending.json + downloads.json + dedup + categorized strategies) |

## Requirements

- Python 3.8+
- Playwright (`python3 -m pip install playwright`)
- nest_asyncio (`python3 -m pip install nest_asyncio`)
- Chromium browser profile at `~/.kimi_auth/browser_profile_chromium/`

## Quick Start

```bash
# 1. Validate login
python3 scripts/kimi_login_manager.py --validate

# 2. Discover files (add to pending, do not download)
python3 scripts/kimi_downloader.py --url "https://www.kimi.com/chat/CONV_ID" --discover-only

# 3. Process pending queue
python3 scripts/kimi_downloader.py --process-pending

# 4. Or full pipeline in one command
python3 scripts/kimi_downloader.py --url "https://www.kimi.com/chat/CONV_ID"

# 5. Start daemon
python3 scripts/tracker_daemon.py --start
```

## License

MIT License - nervlin4444/ai.skills.incubation
