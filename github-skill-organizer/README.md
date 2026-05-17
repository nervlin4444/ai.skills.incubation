---
title: GitHub Skill Organizer - Human Overview
name: github-skill-organizer
description: Human-readable project overview, architecture guide, and design rationale. Authentication borrowed from github-restful-api-connector.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/README.md"
  github_path: "github-skill-organizer/README.md"
---

# GitHub Skill Organizer

## 這是什麼？

`github-skill-organizer` 是一個**背景守護進程**，負責在你的本地工作站與 GitHub 技能倉庫之間自動同步 skill 檔案。

它解決的核心問題：**多個工作站（OpenClaw / Hermes / WorkBuddy）如何共享同一套 skill，且版本不亂。**

## 與現有技能的關係

| 技能 | 職責 | 本技能如何使用它 |
|---|---|---|
| `github-restful-api-connector` | 單次 GitHub API 操作（上傳/下載/創建倉庫） | 作為**底層依賴**，本技能調用它完成實際同步 |
| `github-skill-organizer` | **策略編排** + 背景排程 + 版本判定 + 閘門檢查 | 不重建輪子，只負責「何時同步、如何分級、是否批准」 |

**必須先安裝 `github-restful-api-connector`，本技能才能運作。**

## 認證管理

本技能**不持有** GitHub PAT 或 Owner 資訊。所有認證由 `github-restful-api-connector` 管理：
- `GITHUB_TOKEN`：存在於 `github-restful-api-connector/.env`
- `GITHUB_OWNER`：存在於 `github-restful-api-connector/.env`

本技能只讀取 `DEPENDENCY_SKILL_PATH` 來定位依賴技能，再從其 `.env` 借用認證資訊（僅用於日誌顯示和報錯提示，不直接發送 API 請求）。

## 核心概念

### 三個資料夾

| 資料夾 | 用途 | 誰放東西進去 |
|---|---|---|
| `DOWNLOAD_FOLDER` | Kimi / 網頁 / 手動下載的 skill 檔案暫存區 | 你、Agent、網頁抓取器 |
| `USER_SKILLS_FOLDER` | 本地 skill 正式安裝目錄 | 本技能的 `skill_installer.py` |
| `pending_approval/` | Minor/Major 變更等待你批准 | 本技能的 `sync_engine.py` |

### 變更分級閘門

| 級別 | 條件 | 版本遞增 | 誰批准 |
|---|---|---|---|
| **Patch** | 檔案 <=3、無架構檔變更、無硬編碼路徑 | `v1.0.0 -> v1.0.1` | Agent 自動（若開啟） |
| **Minor** | 檔案 >3、或新增依賴、或修改 SKILL.md | `v1.0.0 -> v1.1.0` | **必須主人批准** |
| **Major** | 破壞性變更、skill 合併、架構重構 | `v1.0.0 -> v2.0.0` | **必須主人批准** |

**Agent 絕對不能擅自上傳 Minor/Major 變更。**

### Frontmatter 嚴格驗證

每個 skill 檔案的 frontmatter 中，`github_repository` **必須**符合 `owner/repo` 格式：

    github_repository: "nervlin4444/ai.skills.incubation"

以下格式一律**報錯並拒絕處理**：
- `github-skill-organizer`（缺少 owner）
- `ai.skill.automation`（缺少 repo/skill-name）
- 空白或缺失

找不到有效 `github_repository` 的檔案會被記錄到 `logs/rejected/` 並停止處理。

## 目錄結構

    github-skill-organizer/
    ├── SKILL.md                          <- LLM 執行指令（Agent 讀取）
    ├── README.md                         <- 本檔案（人類閱讀）
    ├── .env.example                      <- 環境變數範本（無 GITHUB_TOKEN）
    ├── config/
    │   └── sync.config.json              <- 同步規則與版本判定配置
    ├── scripts/
    │   ├── USAGE.md                      <- CLI 用法教程
    │   ├── scheduler_daemon.py           <- 背景守護主程式
    │   ├── skill_organizer_config.py     <- 配置讀取與驗證
    │   ├── local_scanner.py              <- 掃描 DOWNLOAD_FOLDER
    │   ├── skill_installer.py            <- 安裝檔案到正確 skill 目錄
    │   ├── change_classifier.py          <- 變更分級與版本號遞增
    │   ├── sync_engine.py                <- 上傳閘門與 GitHub 同步
    │   └── github_dependency_checker.py  <- 依賴技能檢測
    ├── logs/                             <- 執行日誌
    ├── state/                            <- Daemon 狀態檔案（JSON）
    └── pending_approval/                 <- 等待批准的變更批次

## 快速開始

### 1. 安裝依賴技能

先確保 `github-restful-api-connector` 已安裝在 `USER_SKILLS_FOLDER` 中，且其 `.env` 已配置 `GITHUB_TOKEN` 和 `GITHUB_OWNER`。

### 2. 配置環境

複製範本並填入：

    cp .env.example .env

編輯 `.env`：

    DOWNLOAD_FOLDER=~/Downloads/skills-inbox
    USER_SKILLS_FOLDER=~/skills
    DEPENDENCY_SKILL=github-restful-api-connector
    DEPENDENCY_SKILL_PATH=~/skills/github-restful-api-connector

### 3. 測試單次執行

    python scripts/scheduler_daemon.py --sync-now

### 4. 啟動背景守護

    python scripts/scheduler_daemon.py --start

## 設計原則

1. **零 Token 消耗**：Daemon 循環內禁止呼叫 LLM API，所有判定均為確定性規則
2. **認證隔離**：PAT 和 Owner 資訊由 `github-restful-api-connector` 統一管理，本技能不持有
3. **閉環風險控制**：Patch 可自動，Minor/Major 必須進 `pending_approval/`
4. **跨平台**：Windows / macOS / Linux / QNAP NAS 均支援
5. **不依賴外部 YAML 函式庫**：frontmatter 解析內建於 `local_scanner.py`

## 版本歷史

| 版本 | 日期 | 變更 |
|---|---|---|
| v1.0.0 | 2026-05-17 | 初始版本，含背景 Daemon、變更分級、上傳閘門、嚴格 frontmatter 驗證 |
