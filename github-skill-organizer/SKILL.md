---
title: "GitHub Skill Organizer - LLM Execution Directive"
name: github-skill-organizer
description: "LLM execution directive for bi-directional skill sync. v1.0.14 fixes Issue #13: documents change_classifier.py and the mandatory 3-step upload workflow (compare -> classify -> upload)."
version: "1.0.14"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T13:00:00+08:00"
fixes: [13]

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"

file_mapping:
  local_path: "SKILL.md"
  github_path: "github-skill-organizer/SKILL.md"
---

# LLM EXECUTION DIRECTIVE: github-skill-organizer v1.0.14

## 0. 前置聲明

本文件是給 LLM 直接執行的指令。不是給人類閱讀的說明書。每一條規則都是強制性的。

## 1. 核心架構

本技能由以下組件構成：

  sync_engine.py          核心引擎（compare / upload / sync_changelog）
  change_classifier.py    變更分類器（必須步驟，產生 classification）
  skill_issue_reporter.py Issue 報告生成器
  scheduler_daemon.py     定時守護進程

## 2. 絕對禁止（LOCK 規則）

### 2.1 禁止直接將 compare_skill() 返回值傳入 upload_skill()

  原始錯誤: result = engine.compare_skill(...); engine.upload_skill(..., result)
  後果: compare_skill() 返回值缺少 approval_required / bump_type / new_version / reason，
        導致 upload_skill() 內部 KeyError 或邏輯錯誤。
  正確做法: 必須先調用 change_classifier.classify_change() 產生完整 classification，
            再傳入 upload_skill()。

### 2.2 禁止從 files[0] 推導 local_dir

  原始錯誤: local_dir = Path(files[0]).parent.parent
  後果: files[0] 是 SKILL.md 時，parent.parent 指向 skills 父目錄，導致所有技能一起上傳。
  正確做法: local_dir = Path(os.path.expanduser(str(self.cfg.user_skills_folder))) / skill_name

### 2.3 禁止在不展開 ~ 的情況下使用 Path()

  原始錯誤: Path("~/.workbuddy/skills")
  後果: Python Path 不會自動展開 ~，指向不存在的路徑。
  正確做法: Path(os.path.expanduser("~/.workbuddy/skills"))

### 2.4 禁止調用 _upload_via_api()

  原始錯誤: if self.github_api: result = self._upload_via_api(...)
  後果: _upload_via_api() 是 placeholder，只返回 {"status": "placeholder"}。
  正確做法: 強制使用 result = self._upload_via_cli(...)

### 2.5 禁止用臨時目錄名作為 skill_dir_name

  原始錯誤: skill_dir_name = Path(clean_dir).name
  後果: clean_dir 是 sync_clean_abc123，repo_base_path 傳入隨機名稱。
  正確做法: skill_dir_name = skill_name or Path(str(local_dir)).name

### 2.6 禁止用 files[0] 讀取 frontmatter

  原始錯誤: fm = self._read_frontmatter_from_file(files[0])
  後果: files[0] 可能不是 SKILL.md，讀取到錯誤的 frontmatter。
  正確做法: skill_md = skill_dir / "SKILL.md"; fm = self._read_frontmatter_from_file(skill_md)

### 2.7 禁止直接取整倉所有 blob 作為 github_files

  原始錯誤: github_files = {item["path"]: item["sha"] for item in tree_data["tree"] if item["type"] == "blob"}
  後果: 返回整倉所有文件（含其他技能），與本地路徑永遠不匹配。
  正確做法: 只保留 skill_name + "/" 前綴的路徑，去掉前綴。

### 2.8 禁止在 action 判定中遺漏 local_only

  原始錯誤: elif modified and not github_only: action = "local_ahead"
  後果: 只有 local_only（本地新增文件）時錯誤落入 diverged。
  正確做法: elif (modified or local_only) and not github_only: action = "local_ahead"

## 3. 強制規範（MUST 規則）

### 3.1 上傳前必須執行的三步流程（v1.0.14 Issue #13 新增）

  上傳技能到 GitHub 必須嚴格遵循以下三步順序，禁止跳過任何一步：

  Step 1: 比較本地與 GitHub（compare_skill）
    comparison = engine.compare_skill(skill_name, local_dir)
    返回值包含: action, modified_files, local_only_files, github_only_files, comparisons
    注意: 此返回值缺少 approval_required / bump_type / new_version / reason，不能直接傳入 upload_skill()

  Step 2: 分類變更（change_classifier - 必須步驟）
    from scripts.change_classifier import classify_change
    classification = classify_change(comparison)
    返回值包含完整的: approval_required, bump_type, new_version, reason
      + compare_skill() 的所有欄位
    這是產生完整 classification 的唯一正確方式。

  Step 3: 上傳（upload_skill）
    result = engine.upload_skill(skill_name, files, classification)
    其中 files 是本地需要上傳的文件列表（modified + local_only）

  錯誤示例（禁止）:
    comparison = engine.compare_skill("my-skill", "./my-skill")
    engine.upload_skill("my-skill", files, comparison)  # ← 缺少必要欄位，會失敗

  正確示例（必須）:
    comparison = engine.compare_skill("my-skill", "./my-skill")
    from scripts.change_classifier import classify_change
    classification = classify_change(comparison)
    files = [Path("./my-skill") / f for f in comparison["modified_files"] + comparison["local_only_files"]]
    engine.upload_skill("my-skill", files, classification)

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

### 3.3 change_classifier.classify_change() 強制邏輯（v1.0.14 新增）

  輸入: compare_skill() 的返回值
  輸出: 完整的 classification dict，包含以下欄位:
    - compare_skill() 的所有原始欄位（status, owner, repo, action, comparisons 等）
    - approval_required: bool（major version 變更需要主人確認）
    - bump_type: str（"major" / "minor" / "patch"）
    - new_version: str（根據 bump_type 自動計算的新版本號）
    - reason: str（變更原因描述）

  分類規則:
    - action == "identical" → 無需上傳
    - action == "local_ahead" → 根據版本變更大小決定 bump_type
    - action == "github_ahead" → 建議先 pull 再處理
    - action == "diverged" → approval_required = True

### 3.4 upload_skill() 強制流程

  Step 1: 檢查 classification["approval_required"]（v1.0.13 Issue #12 修復: 使用 .get() 安全訪問）
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

  v1.0.13 Issue #12 修復: upload_skill() 內部安全訪問 classification 欄位:
    approval_required = classification.get("approval_required", False)
    bump_type = classification.get("bump_type", "patch")
    new_version = classification.get("new_version", "")  # 若空則從 SKILL.md 提取
    reason = classification.get("reason", "")  # 若空則從 action/counts 生成

  v1.0.14 Issue #13 防禦: 如果 classification 明顯不完整（缺少 change_classifier 產生的欄位），
  自動調用 change_classifier.classify_change() 補全:
    if "bump_type" not in classification or "approval_required" not in classification:
        from scripts.change_classifier import classify_change
        classification = classify_change(classification)

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

  遇到以下情況必須上報主人，禁止擅自決定:
    - 路徑包含 ~ 但無法確定是否已 expanduser
    - files 列表包含非技能文件（如 LICENSE、.gitignore）
    - compare_skill 返回 diverged 但無法確定原因
    - upload_skill 返回 error 且 details 中無 returncode
    - 任何涉及刪除的操作請求

## 7. fixes 欄位規範

### 7.1 所有技能文件必須包含 fixes 欄位

  fixes 是 frontmatter 的強制欄位，必須存在:
    fixes: []        ← 無關聯 Issue（新增/優化/文檔/常規維護）
    fixes: [4]       ← 修復單一 Issue
    fixes: [4, 5]    ← 一次修復多個 Issue

  禁止:
    - 省略 fixes 欄位
    - fixes: "new" 或 fixes: "enhancement"（字符串）
    - fixes: 5（單一整數，非列表）

### 7.2 上傳腳本自動讀取 fixes

  github_repo_sync.py 上傳前掃描所有文件的 frontmatter:
    - 提取 fixes 列表（整數列表）
    - 合併去重
    - 自動在 commit message 末尾附加 Fixes #N
    - GitHub 收到 commit 後自動關閉對應 Issue

### 7.3 Agent 行為規範

  修復 Issue 時:
    - 在代碼註釋中寫入 # Fixes #N
    - 在 frontmatter 中加入 fixes: [N]
    - 更新 version 號

  非修復修改時:
    - 保持 fixes: []
    - 更新 version 號（如適用）

## 8. 版本更新記錄

| 版本 | 修復內容 |
|------|---------|
| v1.0.5 | compare_skill 路徑前綴過濾 + action 判定修正 |
| v1.0.6 | upload_skill frontmatter 讀取修正 + API/CLI 路由修正 + skill_dir_name 修正 |
| v1.0.7 | 錯誤移除 per-file 驗證（已回滾） |
| v1.0.8 | 恢復 per-file 驗證（CHANGELOG.md 除外）+ LICENSE 排除 + sync_changelog 新增 |
| v1.0.9 | local_dir 路徑推導修正（不再從 files[0] 推導） |
| v1.0.10 | expanduser(~) 路徑展開修正 |
| v1.0.11 | 子目錄過濾、local_only 判定、強制 CLI 上傳、CHANGELOG 同步 |
| v1.0.12 | 新增 skill_issue_reporter.py + CONTRIBUTING.md（從 agent-skill-improving 遷移） |
| v1.0.13 | 統一 frontmatter 格式（fixes 欄位、移除 {baseDir}、單一 file_mapping）；sync_engine.py 安全訪問 classification（Issue #12） |
| v1.0.14 | 新增 change_classifier.py 文檔（Issue #13）；強制三步上傳流程（compare -> classify -> upload）；upload_skill() 自動防禦調用 change_classifier |
