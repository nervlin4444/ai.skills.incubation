---
title: "GitHub Skill Organizer - Human Overview"
name: "github-skill-organizer"
description: "Human-readable project overview, architecture guide, commit strategy, security controls, and post-install self-testing. Background daemon for syncing local skills to GitHub with strict gatekeeping."
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
  - local_path: "{baseDir}/README.md"
    github_path: "github-skill-organizer/README.md"
---

# github-skill-organizer

> 版本：v1.1.2
> 對齊：SKILL.md v1.1.2 + SOUL.md v5.0 + SKILL_CORRECTIONS.md v2.5.0
> 更新重點：**安裝後自測機制、自動修復簡單錯誤、複雜錯誤自動開 Issue**

---

## 一、這是什麼？

`github-skill-organizer` 是一個 **背景守護進程**，負責在你的本地工作站與 GitHub 技能倉庫之間自動同步 skill 檔案。

它解決的核心問題：**多個工作站（OpenClaw / Hermes / WorkBuddy）如何共享同一套 skill，且版本不亂、變更可追溯、安全可控、安裝後自動驗證。**

---

## 二、與現有技能的關係

| 技能 | 職責 | 本技能如何使用它 |
|:---|:---|:---|
| `github-restful-api-connector` | 單次 GitHub API 操作（上傳/下載/創建倉庫/開 Issue）| 作為 **底層依賴**，本技能調用它完成實際同步與問題上報 |
| `github-skill-organizer` | **策略編排** + 背景排程 + 版本判定 + 閘門檢查 + Commit 策略執行 + **安裝後自測** | 不重建輪子，只負責「何時同步、如何分級、是否批准、點樣寫 commit、點樣驗證」 |

**必須先安裝 `github-restful-api-connector`，本技能才能運作。**

---

## 三、核心概念

### 3.1 安裝後自測機制（v1.1.2 新增）

過往問題：Agent 安裝腳本後直接上傳，結果 `datetime.utcnow()` 等問題要到 runtime 才發現，導致 daemon 崩潰、版本混亂。

解決方案：`skill_installer.py` 安裝後**自動生成變更檢測報告**，Agent 根據報告執行針對性測試。

**流程**：

    安裝完成
        ↓
    生成 install_report.json（logs/install_reports/）
        ↓
    Agent 讀取報告 → 找出修改過的方法
        ↓
    根據風險標記決定測試策略
        ↓
    ├─ 簡單錯誤（如 datetime.utcnow）→ Agent 自動修復 → 重測 → 通過
        ↓
    └─ 複雜錯誤（如架構問題）→ STOP → 開 GitHub Issue → 等待主人定奪
        ↓
    全部通過或主人批准 → 才執行上傳

### 3.2 install_report.json 結構

    {
      "skill_name": "github-skill-organizer",
      "installed_at": "2026-05-20T00:15:00+08:00",
      "changes": {
        "get_last_run_time": {"type": "modified", "risks": ["Deprecated datetime.utcnow()"]},
        "scan": {"type": "modified", "risks": []}
      },
      "test_recommendations": [
        "Re-test modified method: get_last_run_time() — verify change did not break existing behavior",
        "Re-test modified method: scan() — verify change did not break existing behavior"
      ],
      "risk_flags": [
        "get_last_run_time: Deprecated datetime.utcnow(), use datetime.now(timezone.utc)"
      ],
      "auto_fix_candidates": [
        {
          "method": "get_last_run_time",
          "issue": "datetime.utcnow() deprecated",
          "suggested_fix": "Replace datetime.utcnow() with datetime.now(timezone.utc)",
          "confidence": "high",
          "auto_fixable": true
        }
      ],
      "requires_manual_review": false
    }

### 3.3 三個資料夾

| 資料夾 | 用途 | 誰放東西進去 |
|:---|:---|:---|
| `DOWNLOAD_FOLDER` | Kimi / 網頁 / 手動下載的 skill 檔案暫存區 | 你、Agent、網頁抓取器 |
| `USER_SKILLS_FOLDER` | 本地 skill 正式安裝目錄 | 本技能的 `skill_installer.py` |
| `pending_approval/` | Minor/Major 變更等待你批准 | 本技能的 `sync_engine.py` |

### 3.4 變更分級閘門

| 級別 | 條件 | 版本遞增 | 誰批准 |
|:---|:---|:---|:---|
| **Patch** | 檔案 <=3、無架構檔變更、無硬編碼路徑、無 SKILL.md 變更 | `v1.0.0 -> v1.0.1` | Agent 自動（若開啟） |
| **Minor** | 檔案 >3、或新增依賴、或修改 SKILL.md、或新增腳本 | `v1.0.0 -> v1.1.0` | **必須主人批准** |
| **Major** | 破壞性變更、skill 合併、架構重構、frontmatter 規範改動 | `v1.0.0 -> v2.0.0` | **必須主人批准** |

**Agent 絕對不能擅自上傳 Minor/Major 變更。**

### 3.5 Frontmatter 嚴格驗證

每個 skill 檔案的 frontmatter 中，`github_repository` **必須** 符合 `owner/repo` 格式：

    github_repository: "nervlin4444/ai.skills.incubation"

以下格式一律 **報錯並拒絕處理**：

- `github-skill-organizer`（缺少 owner）
- `ai.skill.automation`（缺少 repo/skill-name）
- 空白或缺失

---

## 四、Commit 策略（詳細）

本技能採用 **Conventional Commits** 格式，配合 **semantic-release** 全自動生成 Release Note。主人與 Agent 只需寫好 commit message，其餘由機械人處理。

### 4.1 Commit Message 格式規範

    <type>(<scope>): <subject>

    <body>

    Closes #<issue-number>

| 欄位 | 說明 | 必填 |
|:---|:---|:---|
| `type` | `feat`（新功能）/ `fix`（修復）/ `chore`（雜項）/ `docs`（文件）/ `test`（測試）| 是 |
| `scope` | 模組名稱：`scorer` / `core` / `skill` / `report` / `merger` / `frontmatter` | 建議 |
| `subject` | 簡短描述，50 字內，動詞開頭 | 是 |
| `body` | 詳細說明改動邊個檔案、解決咩問題、影響範圍 | 建議 |
| `Closes #N` | 如有對應 issue，自動關閉 | 可選 |

### 4.2 三種執行結果對應的 Commit 策略

| 結果 | Commit Type | 版本號變化 | Release Note 欄目 | 說明 |
|:---|:---|:---|:---|:---|
| **6a: 順利執行** | `feat(scope): 新增某某功能` | `v1.1.0 -> v1.2.0` | Features | Kimi 輸出檔案，Agent 順利執行，無需修改 |
| **6a: 順利執行（修復類）** | `fix(scope): 修正某某問題` | `v1.2.0 -> v1.2.1` | Bug Fixes | Kimi 輸出修復檔案，Agent 順利執行 |
| **6b: 小改動後順利** | 兩個 commit：`feat: ...` + `fix: ...` | 按最後一個有效 type 遞增 | 合併顯示 | Kimi 的 commit 記錄原始設計，Agent 的 commit 記錄本地修正 |
| **6c: 執行失敗** | `chore: 嘗試加入某某功能（WIP，見 #23）` | **不變** | 不出 release | 不觸發版本遞增，issue 保留待後續處理 |
| 純文件更新 | `docs(skill): 更新 SKILL.md 使用說明` | **不變** | 不出 release | 只改說明書，不影響功能 |

### 4.3 semantic-release 自動化流程

1. Agent 執行 `git commit` 跟足上述格式
2. Push 到 `main` 分支
3. GitHub Actions 觸發 `semantic-release`
4. 自動分析所有 commit：
   - 有 `feat` → 遞增 Minor 版本（v1.2.0）
   - 有 `fix` → 遞增 Patch 版本（v1.2.1）
   - 有 `BREAKING CHANGE` 標記 → 遞增 Major 版本（v2.0.0）
   - 只有 `chore` / `docs` / `test` → **跳過，不出 release**
5. 自動寫入 GitHub Releases，列出改動檔案與 issue 關聯
6. 自動打 tag

**主人與 Kimi 無需手寫 CHANGELOG.md，無需記版本號。**

---

## 五、安全控制方法

### 5.1 變更分級閘門（第一道防線）

| 級別 | 檔案數量 | 架構檔變更 | 自動上傳 | 人工批准 |
|:---|:---|:---|:---|:---|
| Patch | <= 3 | 無 | 允許 | 不需要 |
| Minor | > 3 或 有 | 可能有 | 禁止 | **必須** |
| Major | 任何 | 破壞性 | 禁止 | **必須** |

### 5.2 Pending Approval 緩衝區（第二道防線）

Minor/Major 變更不直接 push，而是：

    1. 打包為 `<skill-name>_<timestamp>.bundle.tar.gz`
    2. 放入 `pending_approval/`
    3. 生成 `APPROVAL_REQUEST.md`（含變更摘要、影響檔案列表、建議版本號、**自測結果摘要**）
    4. 通知主人審查
    5. 主人說 YES → 才執行實際 push
    6. 主人說 NO → 歸檔到 `logs/rejected/` 並記錄原因

### 5.3 安裝後自測（第三道防線，v1.1.2 新增）

**為何需要？**
- 過往 Agent 安裝後直接上傳，`datetime.utcnow()` 等問題到 runtime 才暴露
- 本機制在**上傳前**捕獲問題，避免污染 GitHub 倉庫

**運作方式**：

| 階段 | 執行者 | 動作 |
|:---|:---|:---|
| 安裝完成 | `skill_installer.py` | 生成 `install_report.json`，標記變更方法與風險 |
| 測試執行 | Agent | 根據 `test_recommendations` 逐個方法測試 |
| 簡單修復 | Agent | `datetime.utcnow()` → `datetime.now(timezone.utc)` 等已知模式 |
| 複雜問題 | Agent | STOP → 開 GitHub Issue → 等待主人 |
| 上傳 | Agent | 只有全部通過或主人批准後才 push |

### 5.4 認證隔離（第四道防線）

- 本技能 **不直接持有** `GITHUB_TOKEN`
- 所有 API 呼叫透過 `github-restful-api-connector` 轉發
- `github-restful-api-connector` 的 `.env` 為唯一認證源

### 5.5 零 Token 消耗（第五道防線）

- Daemon 循環內 **禁止** 呼叫 LLM API
- 所有判定（變更分級、frontmatter 驗證、版本遞增）均為確定性規則（if/else 邏輯）

### 5.6 刪除確認門（第六道防線，v1.1.2 強化）

**核心規則**：OS 上的任何刪除動作（`shutil.rmtree`、`os.remove`、目錄清理）**必須經主人確認**。

- `sync_engine.py` 的臨時目錄：上傳後**記錄到 `logs/pending_cleanup/`，不自動刪除**
- Agent 要刪除任何東西前，必須問主人
- 違反 = 觸發 SKILL_CORRECTIONS.md「偏軌」錯誤

---

## 六、目錄結構

    github-skill-organizer/
    ├── SKILL.md                          <- LLM 執行指令（Agent 讀取）
    ├── README.md                         <- 本檔案（人類閱讀）
    ├── .env.example                      <- 環境變數範本（無 GITHUB_TOKEN）
    ├── .github/
    │   └── workflows/
    │       └── release.yml               <- semantic-release 自動化 workflow
    ├── .releaserc.json                   <- semantic-release 配置
    ├── config/
    │   └── sync.config.json              <- 同步規則與版本判定配置
    ├── scripts/
    │   ├── USAGE.md                      <- CLI 用法教程
    │   ├── scheduler_daemon.py           <- 背景守護主程式
    │   ├── skill_organizer_config.py     <- 配置讀取與驗證
    │   ├── local_scanner.py              <- 掃描 DOWNLOAD_FOLDER
    │   ├── skill_installer.py            <- 安裝檔案 + **生成 install_report.json**
    │   ├── change_classifier.py          <- 變更分級與版本號遞增
    │   ├── sync_engine.py                <- 上傳閘門 + **clean temp dir + deletion gate**
    │   ├── github_dependency_checker.py  <- 依賴技能檢測
    │   └── commit_validator.py           <- Commit message 格式驗證
    ├── logs/                             <- 執行日誌
    │   ├── rejected/                     <- 被拒絕的檔案記錄
    │   ├── install_reports/              <- **安裝後變更檢測報告（v1.1.2）**
    │   ├── test_failures/                <- **自測失敗記錄（v1.1.2）**
    │   ├── issues_failed/                <- **Issue 創建失敗記錄（v1.1.2）**
    │   └── pending_cleanup/              <- **待主人確認的刪除清單（v1.1.2）**
    ├── state/                            <- Daemon 狀態檔案（JSON）
    │   └── backup/                       <- 自動備份目錄
    └── pending_approval/                 <- 等待批准的變更批次

---

## 七、快速開始

### 7.1 安裝依賴技能

先確保 `github-restful-api-connector` 已安裝在 `USER_SKILLS_FOLDER` 中，且其 `.env` 已配置 `GITHUB_TOKEN` 和 `GITHUB_OWNER`。

### 7.2 配置環境

複製範本並填入：

    cp .env.example .env

編輯 `.env`：

    DOWNLOAD_FOLDER=~/Downloads/skills-inbox
    USER_SKILLS_FOLDER=~/skills
    DEPENDENCY_SKILL=github-restful-api-connector
    DEPENDENCY_SKILL_PATH=~/skills/github-restful-api-connector

### 7.3 配置 semantic-release（一次性）

確保 `.github/workflows/release.yml` 與 `.releaserc.json` 已存在於 repo 根目錄。首次 push 到 GitHub 後，Actions 會自動啟用。

### 7.4 測試單次執行

    python scripts/scheduler_daemon.py --sync-now

### 7.5 啟動背景守護

    python scripts/scheduler_daemon.py --start

---

## 八、設計原則

1. **零 Token 消耗**：Daemon 循環內禁止呼叫 LLM API，所有判定均為確定性規則
2. **認證隔離**：PAT 和 Owner 資訊由 `github-restful-api-connector` 統一管理，本技能不持有
3. **閉環風險控制**：Patch 可自動，Minor/Major 必須進 `pending_approval/`
4. **Commit 自動化**：Conventional Commits + semantic-release，消除人手寫 CHANGELOG 的負擔
5. **安裝後自測**：上傳前必須通過變更檢測與方法級測試，避免 runtime 崩潰
6. **刪除確認門**：任何檔案/目錄刪除必須經主人確認，Agent 絕對不能擅自刪除
7. **問題上報**：複雜錯誤自動開 GitHub Issue，簡單錯誤 Agent 自動修復
8. **跨平台**：Windows / macOS / Linux / QNAP NAS 均支援
9. **不依賴外部 YAML 函式庫**：frontmatter 解析內建於 `local_scanner.py`

---

## 九、版本歷史

| 版本 | 日期 | 變更內容 |
|:---|:---|:---|
| v1.0.0 | 2026-05-17 | 初始版本，含背景 Daemon、變更分級、上傳閘門、嚴格 frontmatter 驗證 |
| v1.1.0 | 2026-05-19 | 新增 Commit 策略詳細規範、semantic-release 整合、六層安全防線、commit_validator.py |
| v1.1.1 | 2026-05-19 | 新增 upload exclusion（防止 .backups/logs/pending_approval 洩漏）、clean temp dir、deletion confirmation gate |
| **v1.1.2** | **2026-05-20** | **新增安裝後自測機制、方法級變更檢測、簡單錯誤自動修復、設計七道安全閘；修正語法錯誤** |

---

*人類可讀解釋書 v1.1.2*
*本文件是操作手冊，不是執行指令。*
*發現缺陷 → 建議主人 → 等待確認 → 按手冊執行。*
*安裝後 → 自動檢測 → 針對性測試 → 簡單修復 / 複雜上報。*
