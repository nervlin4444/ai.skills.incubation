---
title: "Script Error Correction Checklist"
name: agent-skill-improving
description: "Script error correction checklist. v2.5.0 adds 7 new checks: key compatibility, path tilde expansion, return type consistency, rename global update, non-code file frontmatter, version consistency, incomplete download filtering."
version: "v2.5.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-24T23:10:00+08:00"
fixes: [20, 21, 22, 23, 24, 25, 26]
auth_config:
 provider: "github"
 auth_method: "token"
 token_env_var: "GITHUB_TOKEN"
 env_file_path: ".env"
file_mapping:
 local_path: "assets/SCRIPT.CORRECTIONS.md"
 github_path: "agent-skill-improving/assets/SCRIPT.CORRECTIONS.md"
---

# Script Error Correction Checklist

## Trigger Table

| Trigger | Condition | Action |
|---------|-----------|--------|
| YA.HUO | Script cannot start / syntax error / encoding crash / import failure / bootstrap.py missing | Run "Ya Huo Checklist" |
| KA.KE | Script hangs / path not found / dependency missing / permission denied / replace_in_file keeps failing | Run "Ka Ke Checklist" |
| LOU.YOU | Script runs but output abnormal / emoji garbled / version in filename / temp files left / name hardcoded / writes temp script | Run "Lou You Checklist" |
| YUE.JIE | Script calls github.com API directly / two skills hit same website / interface mixed with local management | Run "Yue Jie Checklist" |

## Ya Huo Checklist

Condition: Script cannot start, syntax error, encoding crash, or bootstrap.py deprecated.

- [ ] **Python one-liner ban**: Planning to use `python -c "..."` with Chinese or multiline strings?
 - Prohibit: Python one-liner in PowerShell, especially with Chinese or triple-quote.
 - Must: Write to `.py` file then execute.
- [ ] **Docstring quote**: Outer docstring using `"""` wrapping content with double-quote examples?
 - Prohibit: Outer docstring uses double quotes, inner example also uses triple double quotes.
 - Must: Outer docstring统一 uses single quotes `'''`.
 - Check: Before generating any Python file, force-check "Docstring: outer uses single quotes".
- [ ] **Encoding declaration**: Python file top has `# -*- coding: utf-8 -*-`?
 - If handling Chinese content: must declare UTF-8.
- [ ] **PowerShell pipe encoding**: Passing Chinese via pipe `|` to Python stdin?
 - Prohibit: PowerShell pipe Chinese, default cp950/Big5.
 - Must: Use temp file中转 `Set-Content -Path $tempFile -Value $content -Encoding UTF8`.
- [ ] **bootstrap.py deprecated**: Trying to execute `bootstrap.py`?
 - Prohibit: bootstrap.py v2.3.x and earlier deprecated, no .py script execution.
 - Must: agent-bootstrap changed to pure text SKILL.md guidance, no script execution.
 - Check: If bootstrap.py found, stop immediately, report owner "bootstrap.py deprecated, use SKILL.md v2.5.0".
- [ ] **CLI only**: Trying to write temp script to call conversation_append.py?
 - Prohibit: Write backup_*.py / write_*.py / test_*.py / append_temp.py etc.
 - Must: Directly use conversation_append.py CLI `--user-input` and `--agent-response`.
- [ ] **Staged assembly strategy (v2.4.0)**: Generating .py file trying to nest `"""` or `'''` inside string?
 - Prohibit: Single string block containing both outer docstring and inner example code (quote nesting hell).
 - Must: Adopt "Stage 1 write business code -> Stage 2 write frontmatter -> Stage 3 join merge".
 - Check: If found self writing `"""` or `chr(34)*3` inside string, stop immediately, switch to staged assembly.

## Ka Ke Checklist

Condition: Script starts then hangs, path error, dependency issue, or replace_in_file keeps failing.

- [ ] **Script location**: New script located in `skills//scripts/`?
 - Prohibit: Write to user dir (e.g. `c:\Users\...`) or temp dir.
 - Must: All scripts in `skills//scripts/`.
- [ ] **Output location**: Generated output files in `skills//assets/`?
 - Prohibit: Output scattered in script dir or temp dir.
- [ ] **External dependency**: Script `import` module from other skill dir?
 - Prohibit: Cross-skill import, maintain two files.
 - Must: Single file self-contained, or inline dependency functions.
 - Exception: stdlib and installed third-party packages.
- [ ] **Path check**: Relative paths based on `__file__` or `os.path.dirname(os.path.abspath(__file__))`?
 - Prohibit: Hardcoded absolute paths.
 - Must: Dynamically compute script dir, then derive related paths.
- [ ] **replace_in_file retry limit**: 3+ consecutive replace_in_file failures still retrying?
 - Prohibit: Infinite retry replace_in_file, waste time and tokens.
 - Must: After 3 failures confirm backup exists, downgrade to write_to_file rewrite entire file.
 - Check: Record [PATCH-APPLIED-VIA-WRITE] to improvement history.
- [ ] **Frontmatter parser test (v2.4.0)**: After modifying `_parse_yaml`, tested multiple file_mapping formats?
 - Prohibit: Only test single format (e.g. dict) and claim pass.
 - Must: Test three formats:
   1. dict format (`local_path: "..."` direct indent)
   2. list-of-dict format (`- local_path: "..."` list item)
   3. empty nested format (`file_mapping:` no value then indented lines)
 - Reason: v1.3.0 `_parse_yaml` had defect handling empty-value indented lines, causing file_mapping parsed as empty string.
- [ ] **Key compatibility check (v2.5.0 NEW)**: After renaming script or changing data structure, does downstream consumer use correct key name?
 - Prohibit: Only change upstream output key, not downstream read key.
 - Must: After rename, global search all reference points, or provide compatibility helper (e.g. _get_file_path() accepts both old/new keys).
 - Check: Run `grep -r "old_key" scripts/` confirm no residue.
 - Case: file_scouter.py outputs "file_path", but skill_installer.py expects "path", causing KeyError.
- [ ] **Path tilde expansion check (v2.5.0 NEW)**: Does script correctly handle `~/Downloads` paths with tilde?
 - Prohibit: Directly use `Path("~/Downloads")` or `os.path.join("~", "Downloads")` without expansion.
 - Must: Use `os.path.expanduser()` or `Path("~/Downloads").expanduser()`.
 - Check: When path contains `~`, must call `.expanduser()`.
 - Case: file_scouter.py derived path `Path(self.cfg.user_skills_folder).parent / "downloads"`, ignoring .env DOWNLOAD_FOLDER=~/Downloads, causing ~ not expanded and dir not found.
- [ ] **Return type consistency (v2.5.0 NEW)**: Does error handling branch return same type as success branch?
 - Prohibit: Success returns dict, error returns str (causes downstream `.get()` to fail with "str object has no attribute get").
 - Must: Error returns `{"status": "error", "reason": "..."}` not `"error message"`.
 - Check: Inspect all return statements for consistent type.
 - Case: skill_syncer.py download_all_skills() on exception sets `results["error"] = str(e)`, but daemon iterates calling `.get()` and crashes.

## Lou You Checklist

Condition: Script runs but output flawed, detail violations, or writes temp script.

- [ ] **Console Chinese output**: Using `print()` to output Chinese or emoji?
 - Prohibit: `print()` Chinese or emoji in Windows console (cp950 cannot display).
 - Must: Remove emoji, use plain text; or avoid `print()` Chinese, use English or silent mode.
- [ ] **Filename version suffix**: Script filename has version suffix (e.g. `script.v2.py`)?
 - Prohibit: Version in filename.
 - Must: Fixed filename (e.g. `script.py`), version in top docstring.
- [ ] **Temp file residue**: Left temp scripts (e.g. `write_*.py`, `test_*.py`, `append_temp.py`, `backup_conversation_now.py`)?
 - Prohibit: Create any temp script.
 - Must: Improve existing script, not create new temp script.
 - New ban: backup_conversation_now.py is temp script, absolutely prohibited.
- [ ] **CONVERSATION.md protection**: Trying to read `CONVERSATION.md` as context recovery source?
 - Prohibit: Agent reads `CONVERSATION.md` (10MB+, wastes tokens).
 - Must: Mark `CONVERSATION.md` as `ARCHIVE-ONLY`, recover state using `session.checkpoint.md` + `checklist.md`.
- [ ] **Name genericization**: Comments, docstring, error messages contain specific names (e.g. owner name, city names)?
 - Prohibit: Specific person names, place names, company names in generic scripts.
 - Must:统一 use "user", "current environment", "local".
- [ ] **CLI parameter completeness**: Calling conversation_append.py forgot `--conv-id` and `--date`?
 - Prohibit: Omit archive params, causing backup lost归属 info.
 - Must: Every call passes `--conv-id` and `--date`.
- [ ] **Fixes consistency boundary (v2.4.0)**: Does `check_fixes_consistency` regex match markdown explanatory text?
 - Prohibit: Global regex searching arbitrary text for "Fixes #N" (misjudges README.md explanatory text).
 - Must: Only detect lines starting with `#` (code comments), exclude markdown list items `- **Fixes**`.
 - Reason: README.md "auto-detect code Fixes declarations (e.g. `# Fixes #5`)" misjudged by old regex as code comment.
- [ ] **Rename global reference update (v2.5.0 NEW)**: After renaming script, did global search and update all reference points?
 - Prohibit: Only change filename, not import statements, docs, Issue body, config file old name references.
 - Must: After rename, run global search `grep -r "old_name" .` (including .py, .md, .json, Issue body strings).
 - Check: Confirm scheduler_daemon.py, daemon_health_check.py, invalid_file_notifier.py, README.md, USAGE.md all updated.
 - Case: local_scanner->file_scouter, sync_engine->skill_uploader/skill_syncer, multiple old references caused daemon fail to start.
- [ ] **Non-code file frontmatter (v2.5.0 NEW)**: Do .md / .json / .env.example etc. non-.py files have frontmatter?
 - Prohibit: Thinking only .py needs ID, ignoring .md / .json / .env / .html files.
 - Must: All skill-related files统一 add frontmatter (.md uses YAML frontmatter, .py uses docstring YAML, .env uses comment YAML).
 - Check: Before outputting any file, confirm frontmatter exists, _meta ID must be complete.
 - Case: USAGE.md, README.md, .env.example.md initially lacked frontmatter, later unified.
- [ ] **Version consistency (v2.5.0 NEW)**: Are all files in same skill bundle using unified version?
 - Prohibit: SKILL.md v1.2.0 but scripts v1.0.0, or sync.config.json version out of sync.
 - Must: Batch update all file versions (`grep -h "version" *.py *.md | sort | uniq -c` should show one value).
 - Check: Run version consistency validation before outputting files.
 - Case: README.md v1.2.0, SKILL.md v1.1.1, sync.config.json v1.0.3, scripts v1.0.0混乱, later batch unified to v1.2.0.
- [ ] **Incomplete download filtering (v2.5.0 NEW)**: When scanning Downloads dir, filtering .opdownload / .crdownload / .part / .tmp?
 - Prohibit: Treat incomplete download temp files as valid files.
 - Must: Auto-skip .opdownload (Opera), .crdownload (Chrome), .part (Firefox), .tmp (generic) when scanning.
 - Check: Test with `touch test.py.opdownload` confirm filtered.
 - Case: file_scouter.py scanning Downloads did not filter incomplete downloads, risk processing temp files.

## Yue Jie Checklist (v2.3.0)

Condition: Script involves github.com API call, cross-skill network access, or interface mixed with local management.

**Core principle: Interface stays interface, local stays local. Draw clear boundary, no shared API access.**

- [ ] **API call isolation**: Script directly calling `urllib.request.urlopen()` or `requests.post()` to `api.github.com`?
 - Prohibit: Any skill script directly calls GitHub API (bypasses connector).
 - Must: All `github.com` API calls go through `github-restful-api-connector` `rest_request()`统一 interface.
 - Reason: Unified auth management, unified error handling, unified logging, unified retry.
- [ ] **Skill boundary**: Two different skills accessing same website or API endpoint?
 - Prohibit: Without special performance needs, two skills should not hit same object/website.
 - Must: Each external service managed by one skill, others access indirectly through that skill interface.
 - Example: `github-skill-organizer` needs create Issue -> call `github-restful-api-connector` `rest_request()`, not implement HTTP itself.
- [ ] **Local vs remote separation**: Script handling both "local file management" and "remote API upload"?
 - Prohibit: Same script mixes local management and remote upload, causing unclear responsibility.
 - Must: Local management (generate files, validate format, directory structure) by `github-skill-organizer`; remote upload (GitHub API calls) by `github-restful-api-connector`.
- [ ] **Dynamic import path**: If script needs import connector, using dynamic path detection not hardcoded?
 - Prohibit: Hardcoded `sys.path.insert(0, "/home/user/skills/...")`.
 - Must: Use relative path detection, try multiple candidate locations (`Path(__file__).parent.parent.parent / "github-restful-api-connector" / "scripts"`, `Path.home() / ".workbuddy" / "skills" / ...`).
- [ ] **Error handling consistency**: Does GitHub API error handling match connector behavior?
 - Prohibit: Self-writing 401/403/404/422 logic, inconsistent with connector.
 - Must: Catch connector `RuntimeError`, unified handling.

## Error Records Archive (reference only, not checklist)

Historical error records for LLM reference, user traceability.

| ID | Date | Trigger | Summary | Status |
|----|------|---------|---------|--------|
| 1 | 2026-05-05 | LOU.YOU | Created multiple temp scripts (append_simple.py, append_v3.py etc.), did not improve existing script | Resolved |
| 2 | 2026-05-05 | KA.KE | Temp script written to user dir, not in skills//scripts/ | Resolved |
| 3 | 2026-05-05 | YA.HUO | PowerShell pipe Chinese to Python stdin, encoding error | Resolved |
| 4 | 2026-05-05 | YA.HUO | Docstring using `"""` caused premature close, SyntaxError | Resolved |
| 5 | 2026-05-05 | YA.HUO | Windows console default cp950, print() Chinese UnicodeEncodeError | Resolved |
| 6 | 2026-05-05 | YA.HUO | PowerShell Python one-liner command, quote parsing conflict | Resolved |
| 7 | 2026-05-09 | LOU.YOU | Script filename with version suffix, Agent cannot stably reference | Resolved |
| 8 | 2026-05-09 | KA.KE | Script external dependency conversation_append.py, increased maintenance complexity | Resolved |
| 9 | 2026-05-09 | LOU.YOU | Agent reads CONVERSATION.md to recover state, consumes massive tokens | Resolved |
| 10 | 2026-05-09 | YA.HUO | Docstring quote conflict repeatedly appears, thinking habit not eradicated | Resolved |
| 11 | 2026-05-12 | LOU.YOU | Agent writes backup_conversation_now.py temp script to execute backup, bypasses existing CLI | Resolved |
| 12 | 2026-05-12 | YA.HUO | Agent tries to execute deprecated bootstrap.py script, causes loop | Resolved |
| 13 | 2026-05-12 | KA.KE | replace_in_file fails due to full-width punctuation, Agent陷入 infinite analysis loop | Resolved |
| 14 | 2026-05-22 | YUE.JIE | skill_issue_reporter.py uses urllib.request directly calling GitHub API, bypasses connector. Later fixed to call github_restful_core.rest_request() | Resolved |
| 15 | 2026-05-22 | YUE.JIE | skill_issue_reporter.py and CONTRIBUTING.md wrongly placed in agent-skill-improving, responsibility归属 error. Later migrated to github-skill-organizer | Resolved |
| 16 | 2026-05-23 | YA.HUO | In Python string generating .py file, inner `"""` conflicts with outer string causing SyntaxError. Later switched to staged assembly (business code separated from frontmatter, line-by-line add() then join) | Resolved |
| 17 | 2026-05-23 | KA.KE | `_parse_yaml` parser cannot handle `file_mapping:` empty-value followed by list/dict nested lines, causing file_mapping parsed as empty string. Later fixed to auto-init list/dict | Resolved |
| 18 | 2026-05-23 | BAN.JIAO | `check_fixes_consistency` regex matched README.md explanatory text "Fixes #5", misjudged as code comment. Later fixed to only detect `#` starting lines (code comments), exclude markdown list items | Resolved |
| 19 | 2026-05-23 | BAN.JIAO | Did not adopt staged assembly strategy, causing repeated quote nesting issues, wasted massive tokens and time. Later established "Stage 1 write business code -> Stage 2 write frontmatter -> Stage 3 join merge" standard flow | Resolved |
| 20 | 2026-05-24 | KA.KE | file_scouter.py output key "file_path", but skill_installer.py expects "path", causing KeyError. Later fixed skill_installer to provide compatibility helper _get_file_path() accepting both keys | Resolved |
| 21 | 2026-05-24 | KA.KE | file_scouter.py derived path Path(self.cfg.user_skills_folder).parent / "downloads", ignoring .env DOWNLOAD_FOLDER=~/Downloads, causing ~ not expanded and dir not found. Later fixed to use self.cfg.download_folder directly | Resolved |
| 22 | 2026-05-24 | YA.HUO | skill_syncer.py download_all_skills() on exception returns string results["error"] = str(e), but daemon expects dict, causing "str object has no attribute get". Later fixed to统一 return dict | Resolved |
| 23 | 2026-05-24 | LOU.YOU | After renaming local_scanner->file_scouter, sync_engine->skill_uploader/skill_syncer, scheduler_daemon.py, daemon_health_check.py, invalid_file_notifier.py, README.md, USAGE.md still referenced old filenames, causing daemon fail to start. Later global search replace | Resolved |
| 24 | 2026-05-24 | LOU.YOU | USAGE.md, README.md, .env.example.md non-.py files initially lacked frontmatter ID, violating ID system. Later supplemented统一 frontmatter | Resolved |
| 25 | 2026-05-24 | LOU.YOU | Version inconsistency in same skill bundle: README.md v1.2.0, SKILL.md v1.1.1, sync.config.json v1.0.3, scripts v1.0.0, causing Agent confusion. Later batch unified to v1.2.0 | Resolved |
| 26 | 2026-05-24 | LOU.YOU | file_scouter.py scanning Downloads did not filter .opdownload / .crdownload / .part incomplete downloads, risk processing temp files. Later added suffix filtering | Resolved |

---

*Last updated: 2026-05-24*
*This file is LLM execution instruction set, human-readable explanation see README.md*
