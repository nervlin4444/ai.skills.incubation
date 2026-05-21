---
title: GitHub Skill Organizer - 人類使用指南
name: github-skill-organizer
description: Bi-directional sync engine between local skills and GitHub repository. Includes upload gate, download sync, SHA-based comparison, and CHANGELOG.md frontmatter automation. v1.0.10 fixes all known path derivation bugs.
version: 1.0.11
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-22T01:46:00+00:00
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: "{baseDir}/.env"
file_mapping:
  - local_path: "{baseDir}/README.md"
    github_path: "github-skill-organizer/README.md"
---

# GitHub Skill Organizer v1.0.10

## 功能概述

雙向同步引擎，連接本地技能目錄與 GitHub 倉庫。包含上傳閘門、下載同步、SHA 比對、以及 CHANGELOG.md frontmatter 自動化。

## 目錄結構

    github-skill-organizer/
    ├── README.md                 ← 本文件（人類指南）
    ├── LLM/SKILL.md              ← LLM 執行指令
    ├── scripts/
    │   ├── sync_engine.py        ← 核心同步引擎 v1.0.10
    │   ├── skill_organizer_config.py
    │   ├── skill_sync.py
    │   ├── local_scanner.py
    │   ├── change_classifier.py
    │   ├── commit_validator.py
    │   ├── version_manager.py
    │   ├── repo_inventory.py
    │   ├── repo_migrator.py
    │   ├── repo_validator.py
    │   ├── scheduler_daemon.py
    │   ├── skill_installer.py
    │   └── github_dependency_checker.py
    └── config/
        └── sync.config.json

## 版本迭代問題記錄（v1.0.4 → v1.0.10）

### 問題 1: compare_skill() 路徑前綴未對齊 [CRITICAL]
- 版本: v1.0.4 存在, v1.0.5 修復
- 現象: GitHub tree API 返回 "skill-name/SKILL.md", 本地掃描 "SKILL.md"
- 後果: 所有技能比較永遠不匹配, 錯誤判定為 diverged
- 修復: 過濾 github_files 只保留 skill_name + "/" 前綴, 並去掉前綴

### 問題 2: compare_skill() action 判定遺漏 local_only [HIGH]
- 版本: v1.0.4 存在, v1.0.5 修復
- 現象: elif modified and not github_only 遺漏 local_only 情況
- 後果: 本地新增文件時錯誤判定為 diverged
- 修復: elif (modified or local_only) and not github_only

### 問題 3: upload_skill() fm 被 files[0] 覆蓋 [HIGH]
- 版本: v1.0.4 存在, v1.0.6 修復
- 現象: fm = self._read_frontmatter_from_file(files[0]), files[0] 可能不是 SKILL.md
- 後果: repo_name 提取錯誤, 可能傳錯倉庫名
- 修復: 固定從 skill_dir / "SKILL.md" 讀取 frontmatter

### 問題 4: API placeholder 被調用 [CRITICAL]
- 版本: v1.0.4 存在, v1.0.6 修復
- 現象: if self.github_api: 走 _upload_via_api(), 但該方法只返回 {"status": "placeholder"}
- 後果: 上傳實際未執行, 只返回假成功
- 修復: 強制使用 _upload_via_cli()

### 問題 5: skill_dir_name 使用臨時目錄名 [CRITICAL]
- 版本: v1.0.4 存在, v1.0.6 修復
- 現象: skill_dir_name = Path(clean_dir).name, clean_dir 是 sync_clean_abc123
- 後果: --repo-base-path 傳入隨機名稱, 文件放到錯誤路徑
- 修復: skill_dir_name = skill_name or Path(str(local_dir)).name

### 問題 6: local_dir 從 files[0] 推導指向 skills 父目錄 [CRITICAL]
- 版本: v1.0.4 存在, v1.0.9 修復
- 現象: local_dir = Path(files[0]).parent.parent, files[0]=SKILL.md 時 parent.parent=~/.workbuddy/skills/
- 後果: 上傳包含所有 15+ 個技能目錄, 嚴重污染目標技能
- 修復: local_dir = Path(os.path.expanduser(str(self.cfg.user_skills_folder))) / (skill_name or repo_name)

### 問題 7: expanduser(~) 未展開 [CRITICAL]
- 版本: v1.0.9 引入, v1.0.10 修復
- 現象: Path("~/.workbuddy/skills") 不會自動展開 ~
- 後果: 指向不存在的路徑, _create_clean_temp_dir 產生空目錄, 上傳失敗
- 修復: Path(os.path.expanduser(str(self.cfg.user_skills_folder)))

### 問題 8: 對所有文件驗證 frontmatter [HIGH]
- 版本: v1.0.4 存在, v1.0.7 錯誤移除, v1.0.8 修正
- 現象: for f in files 驗證所有文件 frontmatter
- 後果: CHANGELOG.md / LICENSE 無 frontmatter → 驗證失敗, 上傳被拒絕
- 修復: 跳過 CHANGELOG.md 驗證（CI 後處理會加 frontmatter）, LICENSE 排除在 UPLOAD_EXCLUDES

### 問題 9: semantic-release 生成的 CHANGELOG.md 無 frontmatter [MEDIUM]
- 版本: 設計問題, v1.0.8 增加 CI 後處理
- 現象: semantic-release 自動生成 CHANGELOG.md 不含 frontmatter
- 後果: 上傳驗證失敗（問題 8）, 或本地 sync 時不匹配
- 修復: GitHub Actions workflow 增加 post-process 步驟, 動態插入 frontmatter

### 問題 10: upload_skill() 未過濾 files 列表 [CRITICAL]
- 版本: v1.0.10 存在, v1.0.11 修復
- 現象: Agent 傳入的 files 列表包含 .backups/*.bak、__pycache__/*.pyc、LICENSE、config/sync.config.json
- 後果: 41 個檔案中 23 個被拒絕, 只有 18 個通過 frontmatter 驗證
- 根因: upload_skill() 直接遍歷 files 驗證 frontmatter, 沒有先用 _should_exclude() 過濾
- 修復: 新增 _is_excluded_path() 方法, 在驗證前過濾 files 列表, 檢查文件本身及所有父目錄
- 額外: config/sync.config.json 補上統一 frontmatter（符合記憶規範 #14/#16）

## 使用方法

### 比較本地與 GitHub

    from sync_engine import SyncEngine
    engine = SyncEngine()
    result = engine.compare_skill("github-skill-organizer")
    print(result["action"])  # identical / local_ahead / github_ahead / diverged

### 上傳技能

    files = [str(f) for f in skill_dir.rglob("*") if f.is_file() and not f.name.startswith(".")]
    classification = {
        "approval_required": False,
        "bump_type": "patch",
        "new_version": "1.0.10",
        "reason": "Bug fixes",
    }
    result = engine.upload_skill("github-skill-organizer", files, classification)

### 同步 CHANGELOG.md

    result = engine.sync_changelog("github-skill-organizer")
    engine.notify_user_changelog_sync(result)

## 配置

編輯 `.env` 文件：

    DOWNLOAD_FOLDER=~/Downloads
    USER_SKILLS_FOLDER=~/.workbuddy/skills
    DEPENDENCY_SKILL=github-restful-api-connector
    DEPENDENCY_SKILL_PATH=~/.workbuddy/skills/github-restful-api-connector
    SCAN_INTERVAL_SECONDS=60
    AUTO_APPROVE_PATCH=true
    PATCH_MAX_FILES=3

## 注意事項

1. **絕對不要**從 files[0].parent.parent 推導 local_dir
2. **必須使用** os.path.expanduser() 展開 ~ 路徑
3. **CHANGELOG.md** 由 semantic-release 生成，上傳時跳過 frontmatter 驗證
4. **LICENSE** 已排除在 UPLOAD_EXCLUDES 中，不會被上傳
5. 所有刪除操作必須經用戶確認，記錄到 pending_cleanup/
