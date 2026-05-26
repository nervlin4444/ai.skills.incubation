---
title: Agent Skill Acquiring - LLM Execution Directive
name: agent-skill-acquiring
description: Skill acquisition and profile management. Executes multi-keyword search, directory scan with security check, profile extraction, and markdown book display.
version: v2.0.1
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T17:30:00+08:00
fixes: [37, 38, 39, 40]
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
❌ "Book table wrapped in ``` code blocks"
❌ "Alias can be left empty"
❌ "Security check uses AST parsing"
❌ "Source determined by directory path"
❌ "Search finds skills immediately after git clone"

### Correct Understanding
✅ Search with keywords list, match against name/description/keywords/alias
✅ Search reads skill_profile.json (fast), extract scans directories (slow)
✅ Extract runs security check (dangerous pattern scan)
✅ Search logs adoption to usage_log.json when --log flag is set
✅ Book output is RAW markdown table, NEVER wrapped in ```
✅ Empty alias must be filled by Agent with Chinese suggestion for batch confirmation
✅ Security check uses STRING MATCH (not AST), may flag comments/strings
✅ Source determined by auth_config.provider in frontmatter (not directory path)
✅ Must run extract AFTER adding new skills before search can find them

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
- Scans skills directory (single-directory layout)
- Extracts frontmatter from SKILL.md or .py docstring
- Detects source via auth_config.provider (user vs connector)
- Runs security check (dangerous patterns, STRING MATCH)
- Generates 10-char summary (Chinese preferred)
- Extracts keywords (Chinese + English)
- Marks empty alias as [PENDING-ALIAS]
- Updates skill_profile.json

### [ ] Command 3: Display Book
```bash
python scripts/skill_profile_book.py --page skills
```
- Reads skill_profile.json
- Outputs RAW markdown table (3 columns: Alias | Summary | Function)
- User skills sorted by usage ranking (descending)
- External skills sorted by alias name (ascending)
- Empty alias displays as [skill_name function_summary]

---

## 🔒 LOCK Rules (Absolute Prohibitions)

### LOCK-001: NEVER Wrap Book Table in ``` Code Blocks
- Book output must be RAW markdown table
- Agent must render table directly, not as code snippet
- Violation: Table appears as plain text, not rendered

### LOCK-002: NEVER Leave Alias Empty
- Extract marks empty alias as [PENDING-ALIAS]
- Agent must review pending aliases after extract
- Agent must suggest Chinese aliases based on skill_name + function_summary
- User confirms batch suggestion, Agent writes back to profile
- Violation: Book table shows [PENDING-ALIAS] or [skill_name], unprofessional

### LOCK-003: NEVER Scan Directories During Search
- Search reads skill_profile.json ONLY
- Directory scanning is extract's responsibility
- Violation: Search becomes slow, defeats JSON-index purpose

### LOCK-004: NEVER Skip Security Check During Extract
- Dangerous patterns must be scanned in all .py files
- Warnings recorded, not blocking
- Violation: Malicious scripts marked as safe

### LOCK-005: NEVER Ignore Pending Alias After Extract
- [PENDING-ALIAS] count > 0 after extract → Agent must review and suggest
- Violation: Book table incomplete

### LOCK-006: NEVER Assume AST Parsing in Security Check
- Security check uses STRING MATCH (not AST)
- Comments and strings containing dangerous patterns WILL trigger warnings
- This is BY DESIGN (fast, no Python compilation needed)
- Violation: Agent reports "false positive" as bug when it's expected behavior

### LOCK-007: NEVER Assume Source by Directory Path
- Source is determined by auth_config.provider in frontmatter
- provider=none → user, provider=github → connector
- Directory path is IGNORED for source classification
- Violation: Agent assumes external skills in same directory are "user"

---

## ⚡ Exception Handling

### Exception 1: Profile Not Found
- Trigger: skill_profile.json does not exist
- Action: Output [PROFILE-NOT-FOUND] → Run extract first
- Forbidden: Create empty profile manually

### Exception 2: Security Check Failed
- Trigger: Dangerous pattern found in .py file
- Action: Output [SECURITY-FAILED] → Record warning in profile → Do NOT block extract
- Note: String match may flag comments/strings (expected behavior, not bug)
- Forbidden: Ignore security warnings

### Exception 3: Frontmatter Extractor Not Found
- Trigger: skill_files_designer.py not in expected path
- Action: Fallback to builtin extractor → Output [FALLBACK-EXTRACTOR] → Continue
- Forbidden: Abort extract due to missing dependency

### Exception 4: All Skills Marked as External
- Trigger: auth_config.provider missing in all frontmatter
- Action: Check frontmatter completeness → Output [SOURCE-DETECTION-FAILED] → Default to user
- Forbidden: Leave all skills as external without investigation

### Exception 5: Pending Alias After Extract
- Trigger: [PENDING-ALIAS] count > 0 after extract
- Action: Agent reviews skills with pending alias → Suggests Chinese aliases → User batch confirms → Writes back to profile
- Forbidden: Ignore pending aliases, leave book table incomplete

### Exception 6: Search Returns Empty After Git Clone
- Trigger: New skills cloned but search returns nothing
- Action: Output [EXTRACT-REQUIRED] → Run extract to update skill_profile.json
- Root Cause: Search reads JSON only, does not scan directories
- Forbidden: Assume search is broken, blame JSON index

---

## 🔒 Version Lock

🔒 LOCK v2.0.1 PERMANENT — Search/Extract/Book commands, JSON-only search, security check in extract, UTF-8 no-BOM storage, raw markdown table output, alias pending workflow, string-match security check, frontmatter-based source detection.

---

*LLM Execution Directive v2.0.1*
*Do NOT modify core workflow*
*Fixes #37 #38 #39 #40*