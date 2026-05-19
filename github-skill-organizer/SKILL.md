---
title: "GitHub Skill Organizer - LLM Execution Commands"
name: "github-skill-organizer"
description: "LLM execution instruction set for github-skill-organizer. Background daemon skill for syncing local skills to GitHub with strict gatekeeping, conventional commits, and semantic-release automation. Agent must follow every command exactly."
version: "v1.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-19T18:30:00+08:00"

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

> Version: v1.1.0
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
7. NEVER call LLM APIs inside the daemon loop
8. NEVER hold GITHUB_TOKEN directly — borrow from dependency skill only

**You are NOT `github-restful-api-connector`.** You orchestrate. It executes.

---

## 二、啟動口訣

    掃。驗。分。閘。交。

- 掃：Scan `DOWNLOAD_FOLDER`
- 驗：Validate frontmatter
- 分：Classify change level (Patch / Minor / Major)
- 閘：Apply gate (auto / pending_approval)
- 交：Hand off to `github-restful-api-connector` for actual push

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
| Patch | files <= 3 AND no SKILL.md AND no config/change AND no breaking change | patch (v1.0.0 → v1.0.1) | YES |
| Minor | files > 3 OR SKILL.md changed OR new dependency added OR new script added | minor (v1.0.0 → v1.1.0) | **NO — pending_approval** |
| Major | breaking change OR skill merge OR frontmatter spec change OR architecture refactor | major (v1.0.0 → v2.0.0) | **NO — pending_approval** |

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

### CMD-005: STAGE_PATCH

For Patch-level changes:

    1. Backup current GitHub state to `state/backup/{timestamp}/`
    2. Call github-restful-api-connector to push files
    3. Write commit: `git commit -m "fix(scope): description"` or `git commit -m "feat(scope): description"`
    4. Push to `main`
    5. semantic-release auto-generates Release Note
    6. Log result to `logs/sync/{timestamp}.json`

**If push fails**: Rollback from `state/backup/{timestamp}/`. Log failure. Notify master.

### CMD-006: STAGE_MINOR_MAJOR

For Minor/Major-level changes:

    1. Create bundle: `tar czf pending_approval/{skill_name}_{timestamp}.bundle.tar.gz {files}`
    2. Generate `pending_approval/{skill_name}_{timestamp}_APPROVAL_REQUEST.md` with:
       - Changed files list
       - Diff summary (first 20 lines per file)
       - Proposed version bump
       - Impact assessment
       - Proposed commit messages
    3. STOP. Do NOT push to GitHub.
    4. Notify master: `[PENDING] {skill_name} v{old} → v{new} awaiting approval`
    5. Wait for master command: `APPROVE {bundle_id}` or `REJECT {bundle_id}`

**If master says APPROVE**: Execute CMD-005 with approved bundle.
**If master says REJECT**: Move bundle to `logs/rejected/`. Record reason.

### CMD-007: DEPENDENCY_CHECK

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

---

## 六、與其他技能的協作

| 技能 | 協作點 | 本技能角色 |
|:---|:---|:---|
| `github-restful-api-connector` | 實際 GitHub API 呼叫 | Orchestrator — 決定何時呼叫、傳什麼參數 |
| `agent-skill-improving` | 發現技能缺陷後的改進流程 | 上傳改進後的檔案，按變更分級決定自動或待審 |
| `agent-mission-planning` | 新任務開始時的技能準備 | 確保本地技能與 GitHub 最新版本同步 |
| SOUL.md v5.0 | 身份內化與肌肉記憶 | 啟動時優先注入，確保「先啟動」口訣生效 |

---

## 七、版本歷史

| 版本 | 日期 | 變更內容 |
|:---|:---|:---|
| v1.0.0 | 2026-05-17 | 初始版本：掃描、驗證、分級、閘門、依賴檢查 |
| **v1.1.0** | **2026-05-19** | **新增 Conventional Commits 驗證、semantic-release 整合、六層安全防線、commit_validator.py、備份回滾機制** |

---

*LLM Execution Instruction Set v1.1.0*
*掃。驗。分。閘。交。*
*Agent 是執行者，不是決策者。Minor/Major 必須等待主人批准。*
