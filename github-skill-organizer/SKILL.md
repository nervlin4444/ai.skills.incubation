---
title: GitHub Skill Organizer - LLM Execution Directive
name: github-skill-organizer
description: LLM execution directive for bi-directional skill sync. CRITICAL: This file is an INSTRUCTION for LLM, not a human manual. Every rule below is MANDATORY. Violation causes upload failure, skill pollution, or data loss.
version: 1.0.10
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-22T01:46:00+00:00
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: "{baseDir}/.env"
file_mapping:
  - local_path: "{baseDir}/SKILL.md"
    github_path: "github-skill-organizer/SKILL.md"
---

# LLM EXECUTION DIRECTIVE: github-skill-organizer v1.0.10

## 0. 前置聲明

本文件是給 LLM 直接執行的指令。不是給人類閱讀的說明書。每一條規則都是強制性的。違反任何一條都會導致上傳失敗、技能污染或數據丟失。

## 1. 核心架構

本技能由以下組件構成：

    sync_engine.py          核心引擎（禁止修改 compare_skill / upload_skill / _upload_via_cli 的簽名）
    skill_organizer_config.py   配置加載器
    skill_sync.py           技能同步協調器
    local_scanner.py        本地掃描器
    change_classifier.py    變更分類器
    commit_validator.py     提交驗證器
    version_manager.py      版本管理器
    repo_inventory.py       倉庫清單
    repo_migrator.py        倉庫遷移器
    repo_validator.py       倉庫驗證器
    scheduler_daemon.py     定時守護進程
    skill_installer.py      技能安裝器
    github_dependency_checker.py   依賴檢查器

## 2. 絕對禁止（LOCK 規則）

以下操作絕對禁止，一旦發現立即上報主人，不得擅自修改：

### 2.1 禁止從 files[0] 推導 local_dir

    原始錯誤: local_dir = Path(files[0]).parent.parent
    後果: 當 files[0] 是 SKILL.md（技能根目錄下的文件）時，parent.parent 指向 skills 的父目錄（如 ~/.workbuddy/skills/），導致所有技能被一起上傳，嚴重污染目標技能。
    正確做法: local_dir = Path(os.path.expanduser(str(self.cfg.user_skills_folder))) / (skill_name or repo_name)

### 2.2 禁止在不展開 ~ 的情況下使用 Path()

    原始錯誤: Path("~/.workbuddy/skills")
    後果: Python 的 Path 不會自動展開 ~，指向不存在的路徑，_create_clean_temp_dir 產生空臨時目錄，上傳失敗。
    正確做法: Path(os.path.expanduser("~/.workbuddy/skills")) 或 Path(os.path.expanduser(str(self.cfg.user_skills_folder)))

### 2.3 禁止調用 _upload_via_api()

    原始錯誤: if self.github_api: result = self._upload_via_api(...)
    後果: _upload_via_api() 是 placeholder，只返回 {"status": "placeholder"}，上傳實際從未執行。
    正確做法: 強制使用 result = self._upload_via_cli(repo_name, files, commit_msg, skill_name)

### 2.4 禁止用臨時目錄名作為 skill_dir_name

    原始錯誤: skill_dir_name = Path(clean_dir).name
    後果: clean_dir 是 sync_clean_abc123，--repo-base-path 傳入隨機名稱，文件放到錯誤路徑。
    正確做法: skill_dir_name = skill_name or Path(str(local_dir)).name

### 2.5 禁止用 files[0] 讀取 frontmatter

    原始錯誤: fm = self._read_frontmatter_from_file(files[0])
    後果: files[0] 可能不是 SKILL.md，讀取到錯誤的 frontmatter，repo_name 提取錯誤。
    正確做法: skill_md = skill_dir / "SKILL.md"; fm = self._read_frontmatter_from_file(skill_md)

### 2.6 禁止直接取整倉所有 blob 作為 github_files

    原始錯誤: github_files = {item["path"]: item["sha"] for item in tree_data.get("tree", []) if item["type"] == "blob"}
    後果: GitHub tree API 返回整倉所有文件（含其他技能），與本地路徑永遠不匹配，錯誤判定為 diverged。
    正確做法: 只保留 skill_name + "/" 前綴的路徑，並去掉前綴。

### 2.7 禁止在 action 判定中遺漏 local_only

    原始錯誤: elif modified and not github_only: action = "local_ahead"
    後果: 當只有 local_only（本地新增文件）而無 modified 時，錯誤落入 diverged。
    正確做法: elif (modified or local_only) and not github_only: action = "local_ahead"

## 3. 強制規範（MUST 規則）

### 3.1 上傳前必須驗證的文件

    必須驗證: .py, .md, .json 等核心技能文件
    跳過驗證: CHANGELOG.md（由 semantic-release 自動生成，CI 後處理會加 frontmatter）
    排除上傳: LICENSE, LICENSE.md, LICENSE.txt（UPLOAD_EXCLUDES 已配置）

### 3.2 compare_skill() 強制邏輯

    Step 1: 讀取本地 SKILL.md frontmatter，提取 owner/repo
    Step 2: 調用 GitHub tree API: /repos/{owner}/{repo}/git/trees/main?recursive=1
    Step 3: 過濾 github_files: 只保留 skill_name + "/" 開頭的路徑，去掉前綴
    Step 4: 遍歷本地文件，計算 SHA，與 github_files 比對
    Step 5: 遍歷 github_files，檢查本地缺失的文件
    Step 6: action 判定:
        - 無 modified, 無 local_only, 無 github_only → identical
        - (modified 或 local_only) 且無 github_only → local_ahead
        - 只有 github_only 且無 modified/local_only → github_ahead
        - 其他 → diverged

### 3.3 upload_skill() 強制流程

    Step 1: 檢查 classification["approval_required"]
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

## 4. CHANGELOG.md 特殊處理

### 4.1 上傳時

    CHANGELOG.md 由 semantic-release 自動生成，本地版本可能無 frontmatter。
    上傳時跳過 frontmatter 驗證。
    GitHub Actions workflow 會在 semantic-release 完成後自動插入 frontmatter。

### 4.2 同步時

    調用 sync_changelog(skill_name):
        - 檢查本地 CHANGELOG.md 是否有 frontmatter
        - 檢查遠程 CHANGELOG.md 是否有 frontmatter
        - 若遠程有而本地無 → 下載覆蓋本地
        - 若本地有而遠程無 → 提示上傳
        - 若內容相同 → 報告 identical
        - 若內容不同 → 報告 diverged，需人工審查

## 5. 刪除操作強制規範

    任何文件或目錄的刪除操作必須經用戶確認。
    禁止擅自執行 shutil.rmtree、os.remove、目錄清理。
    臨時目錄清理必須記錄到 pending_cleanup/，由用戶確認後處理。

## 6. 錯誤上報規範

    遇到以下情況必須上報主人，禁止擅自決定：
    - 路徑包含 ~ 但無法確定是否已 expanduser
    - files 列表包含非技能文件（如 LICENSE、.gitignore）
    - compare_skill 返回 diverged 但無法確定原因
    - upload_skill 返回 error 且 details 中無 returncode
    - 任何涉及刪除的操作請求

## 7. 版本更新記錄

| 版本 | 修復內容 |
|------|---------|
| v1.0.5 | compare_skill 路徑前綴過濾 + action 判定修正 |
| v1.0.6 | upload_skill frontmatter 讀取修正 + API/CLI 路由修正 + skill_dir_name 修正 |
| v1.0.7 | 錯誤移除 per-file 驗證（已回滾） |
| v1.0.8 | 恢復 per-file 驗證（CHANGELOG.md 除外）+ LICENSE 排除 + sync_changelog 新增 |
| v1.0.9 | local_dir 路徑推導修正（不再從 files[0] 推導） |
| v1.0.10 | expanduser(~) 路徑展開修正 |
