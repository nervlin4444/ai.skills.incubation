---
title: Kimi Agent Tracker LLM Execution Guide
name: kimi-agent-tracker
description: LLM execution instructions for the Kimi file download automation suite. Covers incremental pipeline, strategy selection, and daemon integration.
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
  local_path: "{baseDir}/SKILL.md"
  github_path: "kimi-agent-tracker/SKILL.md"
---

# Kimi Agent Tracker - LLM Execution Guide v1.3.0

> This file is an LLM execution instruction, not a human manual.
> LLM must read and execute strictly. No improvisation.

## Identity Split

### If you are Sub-Agent (L1 / L2 / L3)

Stop. Close. Execute your own task. This file is not for you.

### If you are Main Agent (L0)

Continue. You are the coordinator. When asked to operate kimi-agent-tracker, follow this guide.

## Core Pipeline (v1.3.0)

The download system uses a 4-stage incremental pipeline:

```
DISCOVERY  ->  DEDUPLICATE  ->  DOWNLOAD  ->  RECORD
   |                |               |             |
Scan page     Check downloads    Apply        Update
for links     .json + pending    strategy     state
              .json              by type      files
```

## Strategy Selection Rules (MANDATORY)

When generating or modifying download logic, you MUST classify files by extension and assign the correct strategy:

| Extension Group | Strategy | Browser Mode | Reason |
|---|---|---|---|
| `.md`, `.txt`, `.json`, `.csv`, `.yml`, `.yaml`, `.html`, `.js`, `.css`, `.xml`, `.sh`, `.bash` | `anchor_injection` | Headless | Fast, reliable for text files. Creates `<a download>` element via JS. |
| `.py` | `preview_extraction` | Headless (extended wait) | Kimi renders Python in preview panel. Extract from DOM after 10x3s retries. Fallback to visible if empty. |
| `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.mp3`, `.mp4`, `.webp`, `.svg`, `.ico`, `.woff`, `.woff2`, `.ttf`, `.eot` | `visible_fallback` | Visible (off-screen) | Binary files refuse headless download. Window moved to `-10000,-10000` to avoid UI interference. |

**NEVER** assign the wrong strategy. `.py` files must use `preview_extraction`, not `anchor_injection`.

## State File Management (MANDATORY)

All state files are JSON with `_meta` block:

### downloads.json
- Key: SHA256 hash of file content
- Value: `{file, hash, path, conversation, conversation_id, downloaded_at}`
- Purpose: Permanent record of successfully downloaded files
- Rule: NEVER delete entries. Append-only.

### pending.json
- Array of `{conversation_id, conversation_title, file_url, filename, file_ext, detected_at, retry_count, last_error, strategy}`
- Purpose: Queue of discovered but not-yet-downloaded files
- Rule: Remove item on success. Increment retry_count on failure. Max retry = daemon.max_retry_per_conversation.

### conversations.json
- Cache from `kimi_conversation_lister.py`
- Purpose: Avoid re-listing conversations every cycle
- Rule: Daemon refreshes this at cycle start.

## Daemon Cycle Flow

```
1. List conversations (lister.py or cache)
2. For each conversation (up to max_conversations_per_cycle):
   a. DISCOVER: downloader.py --url URL --discover-only
      -> New files added to pending.json
   b. DOWNLOAD: downloader.py --url URL
      -> Process pending files for this conversation
   c. Log results per conversation
3. Process remaining pending items (cross-conversation)
4. Sleep interval_sec
```

## Critical Rules

1. **LOCK-016 Compliance**: All `.py` files must be ASCII-only. No Chinese characters or fullwidth punctuation in code, comments, log messages, or error strings. Frontmatter `title`/`name` fields are exempt.

2. **Config-Driven**: All selectors, thresholds, and timeouts must be read from `kimi_tracker_config.json`. Never hardcode values in scripts.

3. **Deduplication Before Download**: Always check `downloads.json` and `pending.json` before opening a browser page. Skip if already recorded.

4. **Subprocess Isolation**: Daemon must call downloader.py as subprocess (not import). Each conversation gets independent process + timeout.

5. **Error Recording**: Every failed download must update `pending.json` with `retry_count` and `last_error`. After max retries, log and skip permanently.

6. **Window Hiding**: When using `visible_fallback`, always pass `--window-position=-10000,-10000 --window-size=1,1` to keep window off-screen.

## File Naming Convention

- `.py` scripts: `xxx_yyy_zzz.py` (underscore separators, exempt from dot-separation rule per agent-skill-improving v1.3.1)
- Config: `kimi_tracker_config.json`
- State files: `downloads.json`, `pending.json`, `conversations.json`
- Log files: `daemon.log`

## Frontmatter Requirements

All files in this skill must include unified frontmatter:
- `.md` files: YAML frontmatter at top
- `.py` files: Docstring with `---` wrapped YAML block
- `.json` files: `_meta` block inside JSON

Mandatory fields: `title`, `name`, `description`, `version`, `github_repository`, `target_branch`, `updated_at`, `fixes`, `auth_config`, `file_mapping`

## Version Lock

LOCK v1.3.0 PERMANENT - Incremental download pipeline, categorized strategies, state file management, deduplication, subprocess isolation, config-driven selectors, LOCK-016 ASCII compliance.
