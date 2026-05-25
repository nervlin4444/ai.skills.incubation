---
title: Kimi Agent Tracker - LLM Execution Guide
name: kimi-agent-tracker
description: LLM execution instruction for the Kimi Agent Tracker skill. Defines download strategy rules, failure recovery patterns, and mandatory diagnostics based on v1.2.1 field experience.
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
  local_path: "{baseDir}/SKILL.md"
  github_path: "kimi-agent-tracker/SKILL.md"
---

# SKILL: kimi-agent-tracker v1.2.1

## Role Definition

You are the execution agent for the Kimi Agent Tracker. Your job is to automate file downloads from Kimi AI chat conversations using Playwright.

## Execution Rules

### RULE 1: Download Strategy Hierarchy (LOCKED)

When downloading files from Kimi conversations, you MUST follow this exact priority order:

1. **PRIMARY**: Content Extraction from Preview Panel DOM
   - Click the file link to open Kimi's preview panel
   - Wait for panel to appear (selectors from config: `extraction.preview_selectors`)
   - Validate panel dimensions: width > 200px AND height > 200px (prevents matching sidebar)
   - Extract text content from DOM (`pre`, `code`, `.view-lines`, `.markdown-body` — from `extraction.content_selectors`)
   - Validate content: minimum length from `extraction.min_content_length` (default 100)
   - For .py files: validate presence of `def ` OR `import ` OR `class `
   - Write directly to local file with UTF-8 encoding (NO BOM)
   - This bypasses all browser download mechanisms

2. **SECONDARY**: Browser Download Fallback (binary files only: .zip, .pdf, .png)
   - Anchor injection with `download` attribute
   - Mouse click on visible element
   - Check browser default download directory

3. **FORBIDDEN**: Never attempt these failed strategies for text files
   - `page.click()` on `sandbox://` links
   - `expect_download()` with Playwright
   - Fetch API on `sandbox://` URLs (returns "Failed to fetch")
   - Physical mouse simulation on off-viewport elements
   - `[class*="sidebar"]` as preview panel selector

### RULE 2: Preview Panel Detection (CRITICAL)

The selector `[class*="sidebar"]` is BANNED from preview panel detection. It matches the conversation sidebar, not the file preview panel.

Correct preview panel selectors (from config):
- `[class*="preview"]`
- `[class*="panel"]` (verify not sidebar by dimensions)
- `[class*="drawer"]`
- `[class*="file-view"]`
- `[class*="code"]`
- `.monaco-editor`
- `[role="dialog"]`

Dimension validation: after finding a matching element, verify `bounding_box().width > 200 && bounding_box().height > 200`.

### RULE 3: Content Validation

After extracting content, validate:
- Minimum length: `extraction.min_content_length` (default 100 chars)
- Content indicators for .py files: presence of `def `, `import `, or `class `
- If content < min_length or wrong format, retry with different selector from `extraction.content_selectors`
- Maximum wait attempts: `extraction.max_wait_attempts` (default 5)
- Wait interval between attempts: `extraction.wait_interval_ms` (default 2000ms)

### RULE 4: File Type Routing

| Extension | Strategy | Reason |
|-----------|----------|--------|
| .py, .md, .txt, .json, .csv, .yml, .yaml, .html, .js, .css, .xml | Content Extraction | Text renderable in preview panel |
| .zip, .rar, .7z, .tar, .gz, .pdf, .doc, .png, .jpg, .mp4 | Browser Download | Binary, not renderable as text |

### RULE 5: Configuration Management

ALL tunable parameters MUST be in `.config/kimi_tracker_config.json`. NEVER hardcode:
- Timeouts
- Selectors (use `extraction.preview_selectors` and `extraction.content_selectors`)
- Directory paths
- Retry counts
- Content validation thresholds

## Failure Recovery Matrix

| Error Pattern | Diagnosis | Action |
|---------------|-----------|--------|
| `[EXTRACT-FAIL] Preview panel not found` | Wrong selector matched sidebar | Check dimension validation; verify `extraction.preview_selectors` in config |
| `[EXTRACT-FAIL] Content empty` | Panel opened but content not loaded | Increase `extraction.max_wait_attempts` or `extraction.wait_interval_ms` |
| `42 chars extracted` | Matched wrong element (sidebar text) | Fixed in v1.2.1 — dimension validation prevents this. If persists, check screenshot. |
| `[SKIP] Browser download failed` | Binary file, extraction not applicable | Verify file extension is in binary list |
| `Login invalid` | Session expired | Execute `kimi_login_manager.py --force-login --visible` |
| `Navigation timeout` | Page load slow | Increase `login.timeout_sec` in config |

## Diagnostic Requirements

When ANY download fails:
1. Capture full-page screenshot to `.logs/diagnose/download/`
2. Log the exact selector that matched and its dimensions
3. Log content length and first 200 chars
4. Do NOT silently skip — always log the specific failure reason

## Version Lock

- Current: v1.2.1
- Download strategy: Content Extraction (primary) + Browser Download (binary fallback)
- Critical fix: Preview panel dimension validation (width>200, height>200)
- NEVER revert to pre-v1.2.0 download triggering strategies for text files
- NEVER use `[class*="sidebar"]` as preview panel selector
