---
title: "Agent Skill Improving - LLM Execution Directive"
name: agent-skill-improving
description: "Guardian Pattern v1.3.2: Framework Guard -> Self-Diagnosis -> Issue Classifier. Mandatory 3-step workflow (generate -> write -> validate). v1.3.2 adds pre-execution guide index (SCRIPT_CORRECTIONS.md / SKILL_CORRECTIONS.md) and LOCK-017."
version: "1.3.2"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-24T12:30:00+08:00"
fixes: []
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "SKILL.md"
  github_path: "agent-skill-improving/SKILL.md"
---

# LLM EXECUTION DIRECTIVE: agent-skill-improving v1.3.2

## 0. Preamble & Experience Guide Index

This file is an LLM execution directive. Not a human manual.
Every rule is mandatory. Violating any LOCK rule = report to owner immediately, stop execution.

### 0.1 Pre-Execution Guide Selection (MANDATORY)

Before generating or modifying ANY skill file, select the correct experience guide based on current task:

| Current Task | Required Guide | Path | Purpose |
|-------------|---------------|------|---------|
| .py / .md / .json / .html file generation or modification | SCRIPT_CORRECTIONS.md | assets/SCRIPT_CORRECTIONS.md | Code techniques: phased assembly, quote handling, chr() usage, docstring structure, ASCII enforcement |
| Skill structure design / directory planning / version strategy / naming convention | SKILL_CORRECTIONS.md | assets/SKILL_CORRECTIONS.md | Skill design patterns: directory layout, frontmatter rules, version locking, file mapping |
| Patch strategy selection / defect judgment / bug diagnosis | BOTH | assets/ | Cross-reference for decision making |

**Execution order:**
1. Identify current task type from the table above
2. Read the corresponding guide(s) from assets/
3. Apply the rules in the guide BEFORE generating any output
4. Proceed to Step 1 (Defect Confirmation)

**Consequence of skipping:** Repeated mistakes (quote nesting, docstring structure errors, version mismatch), wasted tokens, delayed delivery.

## 1. Operation Manual (Mandatory 3-Step)

### Step 1: Confirm Defect (Internal Thinking)

When agent discovers a skill defect, STOP. Do NOT start fixing immediately.

Check 1: Is this a known defect? (Search memory for similar past issues)
Check 2: Is this within current skill scope? (If not, report to owner)
Check 3: Is this fixable by the agent? (If requires owner decision, report)
Check 4: Is there a corresponding Issue? (If not, create one first)
Check 5: Does this involve file deletion? (If yes, MUST get owner confirmation)
Check 6: Is this a framework-level change? (If yes, report to owner, wait for approval)
Check 7: Is this a runtime bug? (If yes, agent can self-fix)
Check 8: Is this an agent-bug (agent violated rules)? (If yes, log and self-fix)
Check 9: Is this a frontmatter format issue? (If yes, use skill_files_designer to regenerate)
Check 10: Is this a naming/path issue? (If yes, check naming convention rules)
Check 11: Is this a version mismatch? (If yes, check version history and bump rules)
Check 12: Is this a cross-platform compatibility issue? (If yes, check pathlib/encoding rules)
Check 13: Is this a long content handling issue? (>500 chars or >50KB)? (If yes, use --from-file JSON)
Check 14: Is this a temporary file management issue? (If yes, check temp directory/backup rules)
Check 15: Is this a frontmatter extraction issue? (If yes, check SkillFrontmatterExtractor rules)
Check 16: Is this a .py ASCII enforcement issue? (If yes, check LOCK-016)
Check 17: Is this a docstring structure issue? (If yes, check phased assembly rules in SCRIPT_CORRECTIONS.md)
Check 18: Is this a file mapping issue? (If yes, check single file_mapping rule)
Check 19: Is this a fixes field issue? (If yes, check fixes format: [] / [N] / [N, M])
Check 20: Is this a github_path leading slash issue? (If yes, remove leading /)

### Step 2: Suggest Fix (Report to Owner)

Format:
```
[DEFECT-CONFIRMED] {skill_name} {file_name} {method_name}()
- Problem: {one sentence}
- Impact: {scope}
- Suggested Fix: {approach}
- Patch Strategy: A/B/C (see Section 4)
- Estimated Risk: low/medium/high
- Requires Owner Confirmation: yes/no
```

Wait for owner response. Do NOT proceed without confirmation.

### Step 3: Execute Fix (By Manual)

After owner confirms, execute according to this manual.

Sub-step 3.1: Read Target File
  - Read the file to be modified, understand structure and dependencies
  - If file is missing, report to owner, do NOT create arbitrarily

Sub-step 3.2: Generate Patch
  - Use Patch strategy A/B/C (Section 4)
  - If multi-file changes, generate patch list
  - Each patch must include: target file, target location, old content, new content

Sub-step 3.3: Apply Patch
  - Use replace_in_file() or write_to_file() to apply patch
  - If replace_in_file() fails 3 times, downgrade to write_to_file() (with backup)
  - After each patch application, verify file integrity

Sub-step 3.4: Validate
  - Run skill_integrity_checker to verify file integrity
  - Check frontmatter format, file_mapping, fixes field
  - If validation fails, report to owner, do NOT proceed

Sub-step 3.5: Update Version
  - Update version number in frontmatter (follow semantic versioning)
  - Update updated_at timestamp (ISO 8601 format)
  - Update fixes field (if fixing an Issue)
  - Update description (if behavior changes)

Sub-step 3.6: Upload to GitHub
  - Use github-skill-organizer skill to upload modified files
  - Commit message must include Fixes #{issue_number}
  - Verify upload success (check GitHub commit history)

Sub-step 3.7: Record History
  - Record improvement history in SKILL_CORRECTION.md
  - Include: problem description, fix approach, validation results, lessons learned

## 2. Absolute Prohibitions (LOCK Rules)

| LOCK | Prohibition | Consequence | Correct Action |
|------|-------------|-------------|----------------|
| LOCK-001 | Agent generates skill files without using skill_files_designer | Missing frontmatter, missing file_mapping, no identity card | Must use skill_files_designer.SkillFileWriter to generate |
| LOCK-002 | Agent directly uses open()/write_text() to write .py/.md/.json/.html files | File structure errors, frontmatter format errors, encoding issues | Must use skill_files_designer.SkillFileWriter |
| LOCK-003 | Agent modifies files without backup | Unrecoverable errors, data loss | Must backup before modification (backup_{id}_{ts}.json) |
| LOCK-004 | Agent modifies files without validation | Defects not detected, files uploaded with errors | Must run skill_integrity_checker after modification |
| LOCK-005 | Agent does not update version number after modification | Version confusion, unable to track changes | Must update version, updated_at, description |
| LOCK-006 | Agent does not update fixes field when fixing Issue | Issue not auto-closed, tracking confusion | Must update fixes: [N] or fixes: [N, M] |
| LOCK-007 | Agent uses old script names (skill_improving / skill_validate) | Script not found, execution failure | Must use new names: skill_integrity_checker / skill_patch_validator |
| LOCK-008 | Agent modifies github_repository or target_branch in frontmatter | Upload to wrong repo, skill lost | These fields are locked, report to owner if change needed |
| LOCK-009 | Agent generates .py files with Chinese or full-width punctuation | SyntaxError on some platforms, inconsistent behavior | All .py content must be ASCII (except frontmatter title/name) |
| LOCK-010 | Agent generates .py files with docstring structure errors | local_scanner cannot extract frontmatter, file classified as invalid | Must follow phased assembly: business code -> frontmatter -> join |
| LOCK-011 | Agent generates .py files with triple-quote nesting | Docstring提前结束, 后续内容裸出为Python代码, SyntaxError | Use chr(34)*3 or chr(39)*3 instead of literal triple quotes in strings |
| LOCK-012 | Agent generates files without fixes field | Missing Issue tracking, commit message lacks Fixes #N | All skill files must include fixes: [] / [N] / [N, M] |
| LOCK-013 | Agent uses {baseDir} in file_mapping | local_scanner cannot resolve path, file install fails | Use actual relative path, e.g. scripts/xxx.py |
| LOCK-014 | Agent uses list-of-dict format for single file_mapping | Inconsistent format, parser confusion | Use dict format: {local_path: ..., github_path: ...} |
| LOCK-015 | Agent uses leading / in github_path | GitHub API double slash error, compare_skill mismatch | github_path must be relative, no leading / |
| LOCK-016 | Agent does not verify file after write_to_file() | File may be corrupted, frontmatter may be malformed | Must verify: AST check + frontmatter extraction + file size check |
| **LOCK-017** | **Agent generates or modifies skill files without reading corresponding experience guide** | **Repeat mistakes, waste tokens, delayed delivery** | **Must read SCRIPT_CORRECTIONS.md (code) or SKILL_CORRECTIONS.md (structure) from assets/ before any generation** |

## 3. Script Name Mapping (Old -> New)

| Old Name (ABANDONED) | New Name (CURRENT) | Version | Status |
|---------------------|-------------------|---------|--------|
| skill_improving.py | skill_patch_validator.py | v1.3.1 | Active |
| skill_validate.py | skill_integrity_checker.py | v1.3.1 | Active |
| frontmatter_generator.py | skill_files_designer.py (merged) | v1.3.1 | Active |
| file_creation_guard.py | skill_files_designer.py (merged) | v1.3.1 | Active |
| skill_bootstrap.py | skill_folder_designer.py | v1.3.1 | Active |
| skill_frontmatter_extractor.py | skill_files_designer.py (merged) | v1.3.1 | Deprecated |

**CRITICAL:** Agent MUST NOT call old script names. If old name found in code or instructions, report to owner immediately.

## 4. Patch Strategy (A/B/C)

### Strategy A: replace_in_file (Low Risk)
```python
replace_in_file(file_path, old_content, new_content)
```
- Use when: Precise location known, small change, no structural impact
- Retry: 3 times (handle whitespace/indentation differences)
- If all 3 fail: Downgrade to Strategy B

### Strategy B: Multi-line Insert Retry (Medium Risk)
```python
# Try inserting at specific line
lines = file_path.read_text().splitlines()
lines.insert(line_number, new_content)
file_path.write_text('\n'.join(lines))
```
- Use when: replace_in_file fails, need to add new section
- Retry: 3 times (handle line number drift)
- If all 3 fail: Downgrade to Strategy C

### Strategy C: write_to_file with Backup (High Risk)
```python
# Backup first
backup_path = file_path.with_suffix('.backup_' + timestamp + file_path.suffix)
shutil.copy2(file_path, backup_path)
# Write new content
file_path.write_text(new_content)
```
- Use when: A and B both fail, or file needs complete rewrite
- MUST backup before write
- After write: Run skill_integrity_checker immediately
- If checker fails: Restore from backup, report to owner

## 5. Validation Checklist (Post-Modification)

After ANY file modification, run skill_integrity_checker and verify:

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| 5.1 AST Syntax | python -m py_compile | No SyntaxError |
| 5.2 Frontmatter Extraction | SkillFrontmatterExtractor.extract() | Returns valid dict with required fields |
| 5.3 Required Fields | Check dict keys | Has: title, name, description, version, github_repository, target_branch, file_mapping |
| 5.4 fixes Field | Check fixes value | Is list of integers: [] / [N] / [N, M] |
| 5.5 file_mapping Format | Check structure | Dict format (not list-of-dict), no {baseDir}, no leading / |
| 5.6 github_path | Check path format | Relative path, no leading / |
| 5.7 Version Format | Check version string | Semantic versioning: x.y.z |
| 5.8 updated_at | Check timestamp | ISO 8601 format with timezone |
| 5.9 File Size | Check file size | Reasonable size (not 0 bytes, not >1MB unexpectedly) |
| 5.10 Encoding | Check file encoding | UTF-8 without BOM |

## 6. Version Update Rules

### Semantic Versioning for Skills

| Change Type | Version Bump | Example | Owner Approval |
|-------------|-------------|---------|---------------|
| Bug fix (patch) | z+1 | 1.2.3 -> 1.2.4 | No |
| New feature (minor) | y+1, z=0 | 1.2.3 -> 1.3.0 | Yes |
| Breaking change / architecture change (major) | x+1, y=0, z=0 | 1.2.3 -> 2.0.0 | Yes |
| Documentation only | No bump | 1.2.3 -> 1.2.3 | No |

### Version Update Checklist
1. Update version in frontmatter
2. Update updated_at timestamp
3. Update description (if behavior changes)
4. Update fixes field (if fixing Issue)
5. Record in version history table
6. Update all referencing files (README, USAGE, etc.)

## 7. Exception Handling

| Exception | Cause | Handling |
|-----------|-------|----------|
| FileNotFoundError | File missing or path error | Report to owner, do NOT create arbitrarily |
| PermissionError | No write permission | Report to owner, do NOT use sudo or chmod |
| SyntaxError | Code syntax error | Report to owner, do NOT attempt auto-fix |
| KeyError | Missing required field | Report to owner, specify missing field |
| ValueError | Invalid value format | Report to owner, specify expected format |
| ImportError | Module not found | Report to owner, check skill installation |
| AttributeError | Method/attribute missing | Report to owner, check version compatibility |
| json.JSONDecodeError | Invalid JSON format | Report to owner, do NOT attempt auto-fix |
| re.error | Invalid regex pattern | Report to owner, specify pattern and error |

## 8. Record History

After each improvement, record in SKILL_CORRECTION.md:

```markdown
## YYYY-MM-DD: {brief description}
- Skill: {skill_name}
- File: {file_name}
- Issue: #{issue_number}
- Problem: {detailed description}
- Fix: {approach}
- Patch Strategy: A/B/C
- Validation: {results}
- Lessons Learned: {insights}
```

## 9. Version History

| Version | Changes |
|---------|---------|
| v1.3.2 | Add Section 0.1 Pre-Execution Guide Index (SCRIPT_CORRECTIONS.md / SKILL_CORRECTIONS.md); add LOCK-017 (must read experience guide before generation); add Check 17-20 in Step 1 |
| v1.3.1 | Add LOCK-009~016; add Patch Strategy A/B/C; add Validation Checklist; add Version Update Rules; add Exception Handling table |
| v1.3.0 | Rename scripts: skill_integrity_checker / skill_patch_validator / skill_files_designer / skill_folder_designer; merge SkillFrontmatterExtractor into skill_files_designer |
| v1.2.0 | Add Self-Diagnosis mechanism; add Issue Classifier |
| v1.1.0 | Add Framework Guard; add mandatory 3-step workflow |
| v1.0.0 | Initial version, basic improvement workflow |