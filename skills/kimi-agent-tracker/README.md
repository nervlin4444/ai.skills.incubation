---
title: "Kimi Agent Tracker - Usage Guide"
name: "kimi-agent-tracker"
description: "Kimi 平台專用自動化追蹤器的人類可讀說明書。負責對話列表提取、sandbox 文件下載、SHA256 去重歸檔。包含獨立 daemon 模式。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T17:15:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/README.md"
  github_path: "kimi-agent-tracker/README.md"
---

Kimi Agent Tracker
==================

Kimi 平台專用自動化追蹤器。

Version: 1.0.0 | Updated: 2026-05-21

Table of Contents
-----------------

1.  Background & Motivation
2.  Architecture Overview
3.  File Inventory
4.  Installation
5.  Usage Guide
6.  Download Mechanisms
7.  Deduplication & File Handling
8.  Sandbox Version Behavior
9.  Daemon Mode
10. Troubleshooting
11. Directory Structure
12. Author

Background & Motivation
-----------------------

當與 Kimi AI 長期協作時，多個對話中產生的文件（技能包、報告、腳本）需要自動化收集。本追蹤器將 Kimi 專用邏輯封裝為獨立技能，依賴 chrome-playwright-connector 提供瀏覽器能力。

Architecture Overview
---------------------

    +-------------------+        +-------------------------+
    | kimi-agent-tracker|  -->   | chrome-playwright-      |
    | (Kimi 專用邏輯)    |        | connector               |
    +-------------------+        | (通用瀏覽器能力)         |
                                 +-------------------------+
                                          |
                                          v
                                 +-------------------------+
                                 | kimi-agent-tracker/     |
                                 | ├── downloads/          |
                                 | ├── .duplicate/         |
                                 | ├── .config/            |
                                 | │   └── downloads.json  |
                                 | └── .logs/              |
                                 +-------------------------+

File Inventory
--------------

| File | Purpose |
|------|---------|
| kimi_login_manager.py | SMS 登入與 persistent profile 維護 |
| kimi_conversation_lister.py | 對話列表提取 |
| kimi_downloader.py | 自動下載核心 |
| state_manager.py | SHA256 去重與狀態追蹤 |
| tracker_daemon.py | 獨立守護程序 |

Installation
------------

    # 1. 安裝依賴（connector 已安裝則跳過）
    pip3 install playwright
    python3 -m playwright install chromium

    # 2. 確保 connector 已部署於同級目錄
    ls ../chrome-playwright-connector/scripts/browser_connector.py

Usage Guide
-----------

### Step 1: 登入（一次性）

    python scripts/kimi_login_manager.py --visible --stay-open 30

### Step 2: 提取對話列表

    python scripts/kimi_conversation_lister.py --count 4 --visible

### Step 3: 批量下載（單次）

    python scripts/kimi_downloader.py --from-list .config/conversations.json --visible

### Step 4: 啟動守護程序（自動定時）

    python scripts/tracker_daemon.py --start

    # 查看狀態
    python scripts/tracker_daemon.py --status

    # 停止守護程序
    python scripts/tracker_daemon.py --stop

    # 單次測試（前台）
    python scripts/tracker_daemon.py --run-once

Download Mechanisms
-------------------

| File Type | Kimi Behavior | Agent Strategy |
|-----------|--------------|----------------|
| .zip, .py, .csv | 直接瀏覽器下載 | expect_download() 捕獲 |
| .md, .txt | 預覽面板 → 下載圖標 → 格式選擇 | 直接點擊優先 + 重試 + 預覽面板備用 |

Deduplication & File Handling
-----------------------------

- SHA256 去重，狀態保存於 .config/downloads.json
- 重複檔案移入 .duplicate/，永不刪除
- 唯一文件名機制（_1, _2, _3...）

Sandbox Version Behavior
------------------------

Kimi 不保留歷史版本。同一 sandbox 路徑在不同對話中始終指向最新版本。
「舊檔案覆蓋新檔案」風險在 Kimi → 下載方向不存在。

Daemon Mode
-----------

獨立守護程序，無需外部 cron/launchd。

| 參數 | 說明 |
|------|------|
| --start | 後台啟動 |
| --stop | 停止 |
| --status | 查看狀態 |
| --run-once | 前台單次執行 |
| --interval N | 循環間隔（默認 900 秒） |
| --count N | 每次提取對話數（默認 10） |

Troubleshooting
---------------

| Symptom | Cause | Solution |
|---------|-------|----------|
| Login failed | Session expired | Re-run kimi_login_manager.py |
| No conversations | Sidebar DOM changed | Use --diagnose |
| Download timeout | expect_download missed | Check .logs/ for retry record |
| Daemon already running | PID file exists | Check --status or --stop |

Directory Structure
-------------------

    {baseDir}/
    ├── .logs/
    ├── .config/
    │   ├── downloads.json
    │   └── conversations.json
    ├── downloads/
    ├── .duplicate/
    └── scripts/

Author
------

Kevin Lin (nervlin4444)
