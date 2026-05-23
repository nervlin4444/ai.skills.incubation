---
title: "GitHub Skill Organizer - LLM Execution Directive"
name: github-skill-organizer
description: "LLM execution directive for bi-directional skill sync with invalid file detection and auto-notification. v1.1.0 adds local_scanner v1.0.8 (invalid file detection), skill_installer v1.0.7 (invalid file archiving), invalid_file_notifier v1.0.0 (auto GitHub Issue creation), and daemon_health_check v1.0.1 (module cache verification)."
version: "1.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T23:00:00+08:00"
fixes: []
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "SKILL.md"
  github_path: "github-skill-organizer/SKILL.md"
---

# LLM EXECUTION DIRECTIVE: github-skill-organizer v1.1.0

## 0. 前置聲明

本文件是給 LLM 直接執行的指令。不是給人類閱讀的說明書。每一條規則都是強制性的。
違反任何 LOCK 規則 = 立即上報主人，禁止繼續執行。

## 1. 組件清單（v1.1.0）

以下 7 個腳本構成完整技能。禁止 LLM 自行創造額外腳本。

| 腳本 | 版本 | 職責 | 調用場景 | 調用方式 | 輸出 |
|------|------|------|----------|----------|------|
| sync_engine.py | 1.0.15 | 核心引擎（compare/upload/sync_changelog） | 比較本地與 GitHub、執行上傳 | `from scripts.sync_engine import SyncEngine` | comparison dict / upload result dict |
| change_classifier.py | 1.0.1 | 變更分類器（必須步驟） | 產生完整 classification | `from scripts.change_classifier import classify_change` | classification dict |
| skill_issue_reporter.py | 1.0.13 | Issue 報告生成器 | 發現 bug 需要上報 | `python scripts/skill_issue_reporter.py --skill-dir <path>` | Issue markdown + JSON |
| scheduler_daemon.py | 0.2.2 | 定時守護進程 | 自動掃描 Downloads 並安裝技能 | `python scripts/scheduler_daemon.py --start` | stdout 日誌到 logs/daemon.out |
| local_scanner.py | 1.0.8 | 掃描 Downloads，檢測 invalid 文件 | daemon 內部調用，或手動測試 | `from scripts.local_scanner import LocalScanner` | file_info dict（含 is_invalid, reason） |
| skill_installer.py | 1.0.7 | 安裝技能文件，歸檔 invalid 文件 | daemon 內部調用 | `from scripts.skill_installer import SkillInstaller` | install_result dict |
| invalid_file_notifier.py | 1.0.0 | 自動創建 GitHub Issue 通知 invalid 文件 | 背景 daemon 獨立運行 | `nohup python scripts/invalid_file_notifier.py --daemon &` | 創建 Issue，更新 logs/invalid_files/*.json |
| daemon_health_check.py | 1.0.1 | 驗證 daemon 環境（模組緩存、frontmatter 提取、文件名清理） | 替換 .py 文件後必須運行 | `python scripts/daemon_health_check.py` | PASS/FAIL 報告 + 具體建議 |

## 2. 強制工作流程（禁止跳過任何步驟）

### 2.1 上傳技能到 GitHub（三步流程）

場景：本地技能目錄已修改，需要同步到 GitHub。

Step 1: 比較（compare_skill）
  輸入: skill_name, local_dir
  命令:
    from scripts.sync_engine import SyncEngine
    engine = SyncEngine()
    comparison = engine.compare_skill(skill_name, local_dir)
  輸出:
    {
      "status": "success",
      "action": "local_ahead" | "github_ahead" | "identical" | "diverged",
      "modified_files": ["file1.py", "file2.md"],
      "local_only_files": ["new_file.py"],
      "github_only_files": ["old_file.py"],
      "comparisons": [...]
    }
  注意: 此輸出缺少 approval_required / bump_type / new_version / reason。禁止直接傳入 upload_skill()。

Step 2: 分類（change_classifier - 必須步驟）
  輸入: comparison dict（Step 1 輸出）
  命令:
    from scripts.change_classifier import classify_change
    classification = classify_change(comparison)
  輸出:
    {
      # compare_skill 的所有原始欄位保留
      "approval_required": true | false,
      "bump_type": "major" | "minor" | "patch",
      "new_version": "1.2.0",
      "reason": "Add new feature: invalid file detection",
      "current_version": "1.1.0",
      "file_count": 3,
      "has_forbidden": false,
      "has_hardcode": false
    }
  注意: 這是產生完整 classification 的唯一正確方式。

Step 3: 上傳（upload_skill）
  輸入: skill_name, files list, classification dict（Step 2 輸出）
  命令:
    from pathlib import Path
    files = [Path(local_dir) / f for f in comparison["modified_files"] + comparison["local_only_files"]]
    files = [f for f in files if f.exists()]
    result = engine.upload_skill(skill_name, files, classification)
  輸出:
    {
      "status": "uploaded" | "error" | "approval_required",
      "commit_message": "feat(agent-skill-improving): sync SKILL.md v1.1.0",
      "commit_hash": "abc123",
      "files_uploaded": ["SKILL.md", "README.md"],
      "fixes": [13, 16],
      "error": "..."  # 若 status == error
    }

### 2.2 替換 .py 文件後的正確流程（v1.1.0 新增）

場景：下載了新版本的 local_scanner.py / skill_installer.py，需要替換到 skills 目錄。

錯誤做法（禁止）：
  直接覆蓋 .py 文件，不停止 daemon，期望 daemon 自動使用新版。
  後果: Python sys.modules 緩存不會自動刷新，daemon 記憶體中仍是舊版代碼。

正確做法（必須）：
  Step 1: 停止 daemon
    pkill -f scheduler_daemon
  Step 2: 驗證文件版本
    grep "version:" ~/.workbuddy/skills/github-skill-organizer/scripts/local_scanner.py
    # 預期輸出: version: 1.0.8
    grep "version:" ~/.workbuddy/skills/github-skill-organizer/scripts/skill_installer.py
    # 預期輸出: version: 1.0.7
  Step 3: 運行健康檢查
    cd ~/.workbuddy/skills/github-skill-organizer
    python3 scripts/daemon_health_check.py
    # 預期輸出: ALL CHECKS PASSED
  Step 4: 啟動 daemon
    python3 scripts/scheduler_daemon.py --start

### 2.3 invalid 文件處理流程（v1.1.0 新增）

場景：daemon 掃描到無法識別 frontmatter 的文件（如 docstring 結構錯誤的 .py 文件）。

流程（全自動，LLM 禁止介入）：
  [local_scanner 掃描 Downloads]
    -> 檢測到 .py 文件有 """ 和 --- 但無法提取 name
    -> 標記 is_invalid=True, reason="py_docstring_frontmatter_unparseable"
  [skill_installer 處理]
    -> 歸檔到 skills_moved/.invalid_files/（而非 .unclassified/）
    -> 記錄日誌到 logs/invalid_files/invalid_{timestamp}.json
    -> 日誌格式: {"status": "pending", "file": "...", "reason": "...", "timestamp": "..."}
  [invalid_file_notifier 背景執行]
    -> 每 60 秒檢查 logs/invalid_files/
    -> 發現 status=pending 記錄 -> 自動創建 GitHub Issue
    -> Issue 標題: [INVALID] [skill_name] file_name - reason
    -> Issue 內容: 根因分析 + 修復步驟 + Auto-Close 條件
    -> 更新日誌 status="notified", 記錄 issue_number
  [Agent 修復文件（由主人指派）]
    -> 通過 skill_files_designer 重新生成正確版本
    -> 上傳時 commit message 包含 Fixes #N
    -> GitHub 自動關閉 Issue

LLM 行為規範：
  - 禁止手動將 .invalid_files/ 中的文件移回 Downloads（這會導致循環歸檔）
  - 禁止手動刪除 logs/invalid_files/ 中的日誌
  - 發現 invalid 文件時，上報主人並等待指派修復任務

## 3. 絕對禁止（LOCK 規則）

### LOCK-001: 禁止直接將 compare_skill() 返回值傳入 upload_skill()
  後果: KeyError（approval_required / bump_type / new_version / reason）
  正確: 必須先調用 classify_change()

### LOCK-002: 禁止從 files[0] 推導 local_dir
  後果: 上傳所有技能（而非單一技能）
  正確: local_dir = Path(os.path.expanduser(str(self.cfg.user_skills_folder))) / skill_name

### LOCK-003: 禁止在不展開 ~ 的情況下使用 Path()
  後果: 指向不存在的路徑
  正確: Path(os.path.expanduser("~/.workbuddy/skills"))

### LOCK-004: 禁止調用 _upload_via_api()
  後果: 只返回 {"status": "placeholder"}
  正確: 強制使用 _upload_via_cli()

### LOCK-005: 禁止用臨時目錄名作為 skill_dir_name
  後果: repo_base_path 傳入隨機名稱
  正確: skill_dir_name = skill_name

### LOCK-006: 禁止用 files[0] 讀取 frontmatter
  後果: 讀取到錯誤的 frontmatter
  正確: skill_md = skill_dir / "SKILL.md"; fm = self._read_frontmatter_from_file(skill_md)

### LOCK-007: 禁止直接取整倉所有 blob 作為 github_files
  後果: 與本地路徑永遠不匹配
  正確: 只保留 skill_name + "/" 前綴的路徑，去掉前綴

### LOCK-008: 禁止在 action 判定中遺漏 local_only
  後果: 只有 local_only 時錯誤落入 diverged
  正確: elif (modified or local_only) and not github_only: action = "local_ahead"

### LOCK-009: 禁止替換 .py 文件後不重啟 daemon（v1.1.0 新增）
  後果: Python sys.modules 緩存不會自動刷新，daemon 記憶體中仍是舊版代碼。
         新文件仍被錯誤歸類（.unclassified/ 或 .identical/）。
  正確: 遵循 2.2 流程：停止 -> 驗證版本 -> 健康檢查 -> 啟動

### LOCK-010: 禁止手動干預 invalid 文件歸檔（v1.1.0 新增）
  後果: 破壞自動通知閉環，導致 Issue 重複創建或遺漏。
  正確: 等待 invalid_file_notifier 自動創建 Issue，由主人指派修復任務。

## 4. 強制規範（MUST 規則）

### MUST-001: compare_skill() 強制邏輯
  Step 1: 讀取本地 SKILL.md frontmatter，提取 owner/repo
  Step 2: 調用 GitHub tree API: /repos/{owner}/{repo}/git/trees/main?recursive=1
  Step 3: 過濾 github_files: 只保留 skill_name + "/" 開頭的路徑，去掉前綴
  Step 4: 遍歷本地文件，計算 SHA，與 github_files 比對
  Step 5: 遍歷 github_files，檢查本地缺失的文件
  Step 6: action 判定:
    - 無 modified, 無 local_only, 無 github_only -> identical
    - (modified 或 local_only) 且無 github_only -> local_ahead
    - 只有 github_only 且無 modified/local_only -> github_ahead
    - 其他 -> diverged

### MUST-002: change_classifier.classify_change() 強制邏輯
  輸入: compare_skill() 返回值
  輸出: 完整 classification dict
  分類規則:
    - action == "identical" -> 無需上傳
    - action == "local_ahead" -> 根據版本變更大小決定 bump_type
    - action == "github_ahead" -> 建議先 pull 再處理
    - action == "diverged" -> approval_required = True

### MUST-003: upload_skill() 強制流程
  Step 1: 檢查 classification["approval_required"]（使用 .get() 安全訪問）
  Step 2: 對所有 files 驗證 frontmatter（CHANGELOG.md 除外）
  Step 3: 運行 gate_checks
  Step 4: 從 SKILL.md 讀取 frontmatter，提取 repo_name
  Step 5: 強制調用 _upload_via_cli()
  Step 6: _upload_via_cli 內部:
    a. local_dir = Path(os.path.expanduser(str(self.cfg.user_skills_folder))) / skill_name
    b. clean_dir = _create_clean_temp_dir(local_dir)
    c. skill_dir_name = skill_name
    d. 調用 github_repo_sync.py --repo-name {repo_name} --local-dir {clean_dir} --repo-base-path {skill_dir_name} --force
    e. 記錄 pending_cleanup，不自動刪除

### MUST-004: local_scanner frontmatter 提取強制邏輯（v1.1.0）
  .py 文件必須同時支持 """ 和 ''' 兩種 docstring 格式
  .md 文件直接以 --- 開頭，無需 docstring
  正則模式:
    - .py: r'"""\s*---\s*(.*?)\s*---\s*"""'  和  r'''\s*---\s*(.*?)\s*---\s*''''
    - .md: r'^---\s*(.*?)\s*---'
  若檢測到 docstring 標記（""" 或 '''）且 --- 存在，但正則無法匹配 -> 標記 is_invalid=True
  理由: py_docstring_frontmatter_unparseable

### MUST-005: skill_installer 歸檔強制邏輯（v1.1.0）
  輸入: file_info dict（含 is_invalid, reason）
  若 is_invalid == True:
    - 歸檔到 skills_moved/.invalid_files/（而非 .unclassified/）
    - 記錄日誌到 logs/invalid_files/invalid_{timestamp}.json
    - 日誌格式: {status: "pending", file: "...", reason: "...", timestamp: "..."}
  若 is_invalid == False 但 name 缺失:
    - 歸檔到 skills_moved/.unclassified/（保持原有行為）

## 5. CHANGELOG.md 特殊處理

上傳時跳過 frontmatter 驗證。
同步時調用 sync_changelog(skill_name):
  - 檢查本地 CHANGELOG.md 是否有 frontmatter
  - 檢查遠程 CHANGELOG.md 是否有 frontmatter
  - 若遠程有而本地無 -> 下載覆蓋本地
  - 若本地有而遠程無 -> 提示上傳
  - 若內容相同 -> 報告 identical
  - 若內容不同 -> 報告 diverged，需人工審查

## 6. 刪除操作強制規範

任何文件或目錄的刪除操作必須經用戶確認。
禁止擅自執行 shutil.rmtree、os.remove、目錄清理。
臨時目錄清理必須記錄到 pending_cleanup/，由用戶確認後處理。

## 7. 錯誤上報規範

遇到以下情況必須上報主人，禁止擅自決定:
  - 路徑包含 ~ 但無法確定是否已 expanduser
  - files 列表包含非技能文件（如 LICENSE、.gitignore）
  - compare_skill 返回 diverged 但無法確定原因
  - upload_skill 返回 error 且 details 中無 returncode
  - 任何涉及刪除的操作請求
  - 發現 invalid 文件（is_invalid=True）
  - 健康檢查報告任何 FAIL
  - daemon 啟動後仍出現 .unclassified/ 或 .invalid_files/ 新增文件

## 8. fixes 欄位規範

所有技能文件必須包含 fixes 欄位:
  fixes: []        <- 無關聯 Issue
  fixes: [4]       <- 修復單一 Issue
  fixes: [4, 5]    <- 一次修復多個 Issue

上傳腳本自動掃描所有文件的 frontmatter:
  - 提取 fixes 列表（整數列表）
  - 合併去重
  - 自動在 commit message 末尾附加 Fixes #N
  - GitHub 自動關閉對應 Issue

## 9. 版本更新記錄

| 版本 | 修復內容 |
|------|---------|
| v1.1.0 | 新增 local_scanner v1.0.8（invalid 文件檢測）、skill_installer v1.0.7（invalid 文件歸檔）、invalid_file_notifier v1.0.0（自動創建 GitHub Issue）、daemon_health_check v1.0.1（模組緩存驗證）；新增 LOCK-009/010、MUST-004/005；新增 2.2/2.3 強制工作流程 |
| v1.0.15 | 修正 change_classifier API 文檔（Issue #16） |
| v1.0.14 | 新增 change_classifier.py 文檔（Issue #13）；強制三步上傳流程 |
| v1.0.13 | 統一 frontmatter 格式（fixes 欄位、移除 {baseDir}、單一 file_mapping） |
| v1.0.12 | 新增 skill_issue_reporter.py + CONTRIBUTING.md |
| v1.0.11 | 子目錄過濾、local_only 判定、強制 CLI 上傳、CHANGELOG 同步 |
| v1.0.10 | expanduser(~) 路徑展開修正 |
| v1.0.9 | local_dir 路徑推導修正 |
| v1.0.8 | CHANGELOG.md CI 後處理、sync_changelog() |
| v1.0.5 | compare_skill 路徑前綴過濾 + action 判定修正 |
| v1.0.4 | 初始版本，基礎同步功能 |