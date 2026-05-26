---
title: Agent Skill Acquiring - LLM Execution Directive
name: agent-skill-acquiring
description: Skill acquisition and profile management. Executes multi-keyword search, directory scan with security check, profile extraction, and markdown book display.
version: v2.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T12:10:00+08:00
fixes: []
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/SKILL.md"
  github_path: "agent-skill-acquiring/SKILL.md"
---

## 🔴 Identity Split (Stop Here If Not Skill Acquirer)

### If You Are Sub-Agent (L1 / L2 / L3) and NOT Skill Acquirer Role
This file is irrelevant. Stop reading. Close this file. Execute your assigned task.

### If You Are Main Agent (L0) or Skill Acquirer (L1 Sub-Agent)
Continue reading. This file is your execution directive.

---

## ⚠️ Cognitive Correction

### Wrong Understanding
❌ "Search with single description string"
❌ "Scan all directories every search"
❌ "No security check during extract"
❌ "No usage logging after search"

### Correct Understanding
✅ Search with keywords list, match against name/description/keywords/alias
✅ Search reads skill_profile.json (fast), extract scans directories (slow)
✅ Extract runs security check (dangerous pattern scan)
✅ Search logs adoption to usage_log.json when --log flag is set

---

## 🔴 Mnemonic (Reflex, No Semantic Understanding Needed)

    Search. Extract. Book.

Meaning: Search skills by keywords → Extract metadata from directories → Display as book table.

---

## 🚨 Immediate Execution (3 Commands)

### [ ] Command 1: Search Skills
```bash
python scripts/skill_profile_search.py web crawl --log
```
- Reads skill_profile.json
- Matches keywords against name/description/keywords/alias
- Sorts: user skills first, then external
- Returns top 5 results as markdown table
- Logs adoption if --log is set

### [ ] Command 2: Extract Profile
```bash
python scripts/skill_profile_extract.py
```
- Scans user/ and external/ directories
- Extracts frontmatter from SKILL.md or .py docstring
- Runs security check (dangerous patterns)
- Generates 10-char summary (Chinese preferred)
- Extracts keywords (Chinese + English)
- Updates skill_profile.json

### [ ] Command 3: Display Book
```bash
python scripts/skill_profile_book.py --page skills
```
- Reads skill_profile.json
- Outputs markdown table: Alias | Skill Name | Skill Summary | Function Summary

---

## ❌ Red Lines

- [ ] Do NOT scan directories during search (read JSON only)
- [ ] Do NOT skip security check during extract
- [ ] Do NOT write skill_profile.json without UTF-8 no-BOM
- [ ] Do NOT create skill_profile.json manually (use extract)
- [ ] Do NOT log adoption without user confirmation
- [ ] Do NOT search without keywords (empty search returns nothing)

---

## ⚡ Exception Handling

### Exception 1: Profile Not Found
- Trigger: skill_profile.json does not exist
- Action: Output [PROFILE-NOT-FOUND] → Run extract first
- Forbidden: Create empty profile manually

### Exception 2: Security Check Failed
- Trigger: Dangerous pattern found in .py file
- Action: Output [SECURITY-FAILED] → Record warning in profile → Do NOT block extract
- Forbidden: Ignore security warnings

### Exception 3: Frontmatter Extractor Not Found
- Trigger: skill_files_designer.py not in expected path
- Action: Fallback to builtin extractor → Output [FALLBACK-EXTRACTOR] → Continue
- Forbidden: Abort extract due to missing dependency

---

## 🔒 Version Lock

🔒 LOCK v2.0.0 PERMANENT — Search/Extract/Book commands, JSON-only search, security check in extract, UTF-8 no-BOM storage.

---

*LLM Execution Directive v2.0.0*
*Do NOT modify core workflow*