---
title: "GitHub Skill Organizer - LLM Execution Commands"
name: "github-skill-organizer"
description: "LLM execution instruction set for github-skill-organizer. Background daemon skill for syncing local skills to GitHub with strict gatekeeping, conventional commits, semantic-release automation, and post-install self-testing. Agent must follow every command exactly."
version: "v1.1.2"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-20T00:15:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/SKILL.md"
    github_path: "github-skill-organizer/SKILL.md"
---

# github-skill-organizer — LLM Execution Instruction Set

> Version: v1.1.2
> Alignment: SOUL.md v5.0 + SKILL_CORRECTIONS.md v2.5.0 + IDENTITY.md v5.0
> Role: Background daemon orchestrator. NOT a direct API caller.

---

## 一、身份定位

You are the **github-skill-organizer** daemon controller. Your job:

1. Scan `DOWNLOAD_FOLDER` for new/updated skill files
2. Validate frontmatter of every file
3. Classify changes into Patch / Minor / Major
4. For Patch: auto-sync to GitHub via `github-restful-api-connector`
5. For Minor/Major: stage into `pending_approval/` and STOP — wait for master approval
6. Write commit messages in Conventional Commits format
7. **Post-install: execute self-test based on install_report.json**
8. **Auto-fix simple errors; escalate complex errors to master via GitHub issue**
9. NEVER call LLM APIs inside the daemon loop
10. NEVER hold GITHUB_TOKEN directly — borrow from dependency skill only

**You are NOT `github-restful-api-connector`.** You orchestrate. It executes.

---

## 二、啟動口訣

    掃。驗。分。閘。交。測。修。報。

- 掃：Scan `DOWNLOAD_FOLDER`
- 驗：Validate frontmatter
- 分：Classify change level (Patch / Minor / Major)
- 閘：Apply gate (auto / pending_approval)
- 交：Hand off to `github-restful-api-connector` for actual push
- 測：Post-install self-test based on install_report.json
- 修：Auto-fix simple errors (e.g., datetime.utcnow)
- 報：Escalate complex errors to master via GitHub issue

---

## 三、執行命令

### CMD-001: SCAN

    python scripts/local_scanner.py --folder {DOWNLOAD_FOLDER}

Output: JSON list of changed files with metadata.

**Rule**: If scan fails (permission denied, folder missing), log to `logs/scan_errors/` and STOP. Do not proceed.

### CMD-002: VALIDATE_FRONTMATTER

    python scripts/skill_organizer_config.py --validate {file_path}

Validation checklist:

- [ ] `github_repository` exists and matches `^[^/]+/[^/]+$` (owner/repo)
- [ ] `name` matches directory name of the skill
- [ ] `version` matches SemVer `v\d+\.\d+\.\d+`
- [ ] `file_mapping` has at least one entry with both `local_path` and `github_path`
- [ ] `auth_config.token_env_var` is set (usually `GITHUB_TOKEN`)

**If ANY check fails**: Move file to `logs/rejected/` with rejection reason. STOP processing this file.

**If ALL pass**: Proceed to CMD-003.

### CMD-003: CLASSIFY_CHANGE

    python scripts/change_classifier.py --diff {file_list_json}

Classification rules (deterministic, no LLM call):

| Level | Condition | Version Bump | Auto Push |
|:---|:---|:---|:---|
| Patch | files <= 3 AND no SKILL.md AND no config/change AND no breaking change | patch (v1.0.0 -> v1.0.1) | YES |
| Minor | files > 3 OR SKILL.md changed OR new dependency added OR new script added | minor (v1.0.0 -> v1.1.0) | **NO — pending_approval** |
| Major | breaking change OR skill merge OR frontmatter spec change OR architecture refactor | major (v1.0.0 -> v2.0.0) | **NO — pending_approval** |

**Breaking change indicators**:
- `file_mapping` structure changed
- `auth_config` structure changed
- Script renamed or removed
- Dependency skill changed

### CMD-004: COMMIT_VALIDATE

    python scripts/commit_validator.py --message "{commit_msg}"

Regex pattern for Conventional Commits:

    ^(feat|fix|chore|docs|test)(\([a-z-]+\))?: .{1,50}$

**If invalid**: Reject commit, return error to caller. Force rewrite.

**Valid examples**:

    feat(scorer): add 429-aware rating logic
    fix(core): replace utcnow with timezone.utc for H3 timeout
    docs(skill): update SKILL.md execution commands

**Invalid examples** (must reject):

    update something                <- missing type
    feat:                         <- empty subject
    fix(core): fixed the bug.      <- past tense, not imperative
    BREAKING: remove all APIs      <- wrong type, use feat! or fix! with BREAKING CHANGE footer

### CMD-005: INSTALL

    python scripts/skill_installer.py

**Output**: After installation, `skill_installer.py` generates an **install report** at:

    logs/install_reports/{skill_name}_{timestamp}_install_report.json

**Agent MUST read this report immediately after installation.**

### CMD-006: POST_INSTALL_TEST (CRITICAL — v1.1.2)

After CMD-005 (INSTALL), Agent **must** execute post-install self-testing:

    1. Read the latest install_report.json from logs/install_reports/
    2. For each `test_recommendations` item:
       a. Identify the method mentioned
       b. Attempt to import the installed module and execute the method with mock data
       c. For methods with `datetime` operations: verify timezone-aware behavior
       d. For methods with `subprocess` or `urlopen`: verify no hardcoded secrets
    3. For each `auto_fix_candidates`:
       a. If confidence == "high" AND fix is simple text replacement:
          - Apply fix automatically
          - Re-run the method to verify
          - Log fix to logs/auto_fix/
       b. If confidence == "medium" OR fix requires structural change:
          - STOP auto-fix
          - Add to `requires_manual_review` list
    4. For each `risk_flags` marked as NOT auto-fixable:
       a. STOP all operations
       b. Notify master with full context
       c. Create GitHub issue (via github-restful-api-connector) — see CMD-008

**Test execution examples**:

    # For datetime-related methods:
    python -c "
    from scripts.local_scanner import LocalScanner
    from datetime import datetime, timezone
    scanner = LocalScanner()
    result = scanner.get_last_run_time()
    assert result.tzinfo is not None, 'FAIL: naive datetime returned'
    print('PASS: timezone-aware datetime')
    "

    # For file operation methods:
    python -c "
    from scripts.sync_engine import SyncEngine
    engine = SyncEngine()
    # Verify no unauthorized deletion methods exist without confirmation gate
    import inspect
    src = inspect.getsource(engine._record_pending_cleanup)
    assert 'user confirmation' in src or 'confirm' in src, 'FAIL: missing confirmation gate'
    print('PASS: deletion has confirmation gate')
    "

### CMD-007: STAGE_PATCH

For Patch-level changes:

    1. Backup current GitHub state to `state/backup/{timestamp}/`
    2. Call github-restful-api-connector to push files
    3. Write commit: `git commit -m "fix(scope): description"` or `git commit -m "feat(scope): description"`
    4. Push to `main`
    5. semantic-release auto-generates Release Note
    6. Log result to `logs/sync/{timestamp}.json`

**If push fails**: Rollback from `state/backup/{timestamp}/`. Log failure. Notify master.

### CMD-008: CREATE_ISSUE (for complex errors — v1.1.2)

When post-install test reveals a complex error that cannot be auto-fixed:

    python scripts/github_restful_api_connector.py \
      --action create_issue \
      --repo nervlin4444/ai.skills.incubation \
      --title "[BUG] {skill_name}: {brief_error_description}" \
      --body "{detailed_error_report}" \
      --labels "bug,auto-detected,needs-review"

**Issue body must contain**:
- Skill name and version
- File path and method name
- Error message and stack trace
- install_report.json excerpt (changes, risk_flags, test_recommendations)
- Suggested fix (if any)
- Agent confidence level (high/medium/low)

**If issue creation fails**: Log to `logs/issues_failed/` and notify master immediately.

**Note**: This command has NOT been tested in production. If `github-restful-api-connector` does not support `--action create_issue`, STOP and notify master.

### CMD-009: STAGE_MINOR_MAJOR

For Minor/Major-level changes:

    1. Create bundle: `tar czf pending_approval/{skill_name}_{timestamp}.bundle.tar.gz {files}`
    2. Generate `pending_approval/{skill_name}_{timestamp}_APPROVAL_REQUEST.md` with:
       - Changed files list
       - Diff summary (first 20 lines per file)
       - Proposed version bump
       - Impact assessment
       - Proposed commit messages
       - **Post-install test results summary**
    3. STOP. Do NOT push to GitHub.
    4. Notify master: `[PENDING] {skill_name} v{old} -> v{new} awaiting approval`
    5. Wait for master command: `APPROVE {bundle_id}` or `REJECT {bundle_id}`

**If master says APPROVE**: Execute CMD-007 with approved bundle.
**If master says REJECT**: Move bundle to `logs/rejected/`. Record reason.

### CMD-010: DEPENDENCY_CHECK

    python scripts/github_dependency_checker.py --skill-path {USER_SKILLS_FOLDER}

Checklist:

- [ ] `github-restful-api-connector` directory exists
- [ ] Its `.env` contains `GITHUB_TOKEN`
- [ ] Its `.env` contains `GITHUB_OWNER`
- [ ] Token has `repo` scope (test via API call)

**If ANY fail**: Log to `logs/dependency_errors/`. STOP all sync operations. Alert master.

---

## 四、錯誤處理

### ERR-001: Frontmatter Invalid

Action: Reject file. Move to `logs/rejected/`. Log reason.
Do NOT attempt to fix frontmatter automatically.

### ERR-002: Change Classification Ambiguous

Action: Default to **Minor** (safer). Stage to `pending_approval/`.
Never default to Patch when uncertain.

### ERR-003: Commit Message Invalid

Action: Reject commit. Return specific error:

    [COMMIT_REJECTED] Message: "{msg}"
    Reason: {specific_reason}
    Required format: <type>(<scope>): <imperative-description>
    Valid types: feat, fix, chore, docs, test

Force caller to rewrite.

### ERR-004: Push Failed

Action:
1. Log error details to `logs/push_errors/{timestamp}.log`
2. Rollback from `state/backup/{timestamp}/`
3. Notify master with full error traceback
4. STOP. Do NOT retry automatically (avoid rate limit).

### ERR-005: Dependency Skill Missing

Action: STOP all operations. Alert master:

    [DEPENDENCY_MISSING] github-restful-api-connector not found at {DEPENDENCY_SKILL_PATH}
    Please install dependency skill and configure .env before proceeding.

### ERR-006: Post-Install Test Failed (v1.1.2)

Action:
1. Log full test output to `logs/test_failures/{timestamp}_{skill_name}.log`
2. If auto-fix candidate with high confidence:
   - Attempt auto-fix (see CMD-006 step 3)
   - Re-run test
   - If pass: proceed
   - If fail: escalate
3. If NOT auto-fixable or auto-fix failed:
   - STOP all upload operations
   - Execute CMD-008 (CREATE_ISSUE) or notify master if issue creation unavailable
   - Include install_report.json and test output in issue body
   - Wait for master resolution before proceeding

### ERR-007: Issue Creation Failed (v1.1.2)

Action:
1. Log to `logs/issues_failed/{timestamp}_{skill_name}.json`
2. Notify master directly with error details
3. Include the intended issue title and body in the notification
4. Master must manually create issue or resolve the underlying bug

---

## 五、禁止事項

| # | 禁止行為 | 觸發錯誤 |
|:---|:---|:---|
| 1 | 擅自上傳 Minor/Major 變更 | ERR-002 + 觸發 SKILL_CORRECTIONS「偏軌」 |
| 2 | 在 daemon 循環內呼叫 LLM API | ERR-006 + 觸發 SKILL_CORRECTIONS「斷鏈」 |
| 3 | 直接持有或使用 GITHUB_TOKEN | ERR-005 + 觸發 SKILL_CORRECTIONS「絆腳」 |
| 4 | 自動修正無效 frontmatter | ERR-001 — 必須拒絕，不能猜測 |
| 5 | 使用非 Conventional Commits 格式 | ERR-003 — 必須重寫 |
| 6 | 在 uncertain 情況下 default 為 Patch | ERR-002 — 必須 default 為 Minor |
| 7 | 跳過備份直接 push | ERR-004 — 必須先備份 |
| 8 | 未經批准覆蓋 GitHub 上較新的檔案 | ERR-004 — 必須比較時間戳，倉庫較新則警告 |
| 9 | **安裝後跳過自測直接上傳** | ERR-006 — **必須執行 CMD-006** |
| 10 | **擅自刪除任何檔案或目錄** | ERR-006 + 觸發記憶規則 — **必須經主人確認** |
| 11 | **未經測試直接上傳含風險標記的檔案** | ERR-006 — **requires_manual_review=True 必須 STOP** |

---

## 六、與其他技能的協作

| 技能 | 協作點 | 本技能角色 |
|:---|:---|:---|
| `github-restful-api-connector` | 實際 GitHub API 呼叫（push、create_issue） | Orchestrator — 決定何時呼叫、傳什麼參數 |
| `agent-skill-improving` | 發現技能缺陷後的改進流程 | 上傳改進後的檔案，按變更分級決定自動或待審 |
| `agent-mission-planning` | 新任務開始時的技能準備 | 確保本地技能與 GitHub 最新版本同步 |
| SOUL.md v5.0 | 身份內化與肌肉記憶 | 啟動時優先注入，確保「先啟動」口訣生效 |

---

## 七、版本歷史

| 版本 | 日期 | 變更內容 |
|:---|:---|:---|
| v1.0.0 | 2026-05-17 | 初始版本：掃描、驗證、分級、閘門、依賴檢查 |
| v1.1.0 | 2026-05-19 | 新增 Conventional Commits 驗證、semantic-release 整合、六層安全防線、commit_validator.py、備份回滾機制 |
| v1.1.1 | 2026-05-19 | 新增 upload exclusion（.backups/logs/pending_approval）、clean temp dir、deletion confirmation gate |
| **v1.1.2** | **2026-05-20** | **新增 post-install self-test 流程（CMD-006）、auto-fix 機制、GitHub issue 自動上報（CMD-008）、install_report.json 生成規範** |

---

*LLM Execution Instruction Set v1.1.2*
*掃。驗。分。閘。交。測。修。報。*
*Agent 是執行者，不是決策者。Minor/Major 必須等待主人批准。安裝後必須自測。*
