---
title: "Kimi Agent Tracker - CLI Usage Guide"
name: "kimi-agent-tracker"
description: "CLI 用法教程。所有參數調整通過單一 config.json，禁止編輯腳本，不使用 .env。"
version: "4.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-26T06:53:23.027+00:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{baseDir}/scripts/USAGE.md"
  github_path: "kimi-agent-tracker/scripts/USAGE.md"
---

# Kimi Agent Tracker — CLI 用法教程

版本：v4.0.0 | 更新時間：2026-05-25

## 核心原則

所有參數調整通過 `.config/kimi_tracker_config.json`，禁止編輯 `.py` 腳本。
本技能不使用 `.env`，所有配置集中於單一 JSON 檔案。

## 快速開始

### Step 0: 環境檢查

    python3 -m pip list | grep playwright
    python3 -m playwright install chromium

### Step 1: 確認配置檔案

檢查 `.config/kimi_tracker_config.json` 是否存在：

    ls .config/kimi_tracker_config.json

如需調整參數，直接編輯此檔案。例如修改 daemon 循環間隔：

    # 編輯 .config/kimi_tracker_config.json
    "daemon": {
      "interval_sec": 1800    # 改為 30 分鐘
    }

### Step 2: 首次登入

    python3 scripts/kimi_login_manager.py --visible --stay-open 300

在瀏覽器中完成 SMS 登入，腳本自動檢測並保存 session。

### Step 3: 驗證登入態

    python3 scripts/kimi_login_manager.py --validate

預期輸出：`[VALIDATE] Login valid: True`

### Step 4: 提取對話列表

    python3 scripts/kimi_conversation_lister.py --count 10

### Step 5: 批量下載

    python3 scripts/kimi_downloader.py --from-list .config/conversations.json

### Step 6: 啟動 Daemon

    python3 scripts/tracker_daemon.py --start

## 常用命令速查

### F-001 登入管理

| 命令 | 用途 |
|------|------|
| `--validate` | 驗證現有 session |
| `--force-login --visible --stay-open 300` | 強制重新登入 |
| `--diagnose` | 診斷登入頁面結構 |

### F-002 對話列表

| 命令 | 用途 |
|------|------|
| `--count N` | 提取 N 個對話 |
| `--diagnose` | 診斷側邊欄結構 |

### F-003 下載

| 命令 | 用途 |
|------|------|
| `--url URL` | 從單個對話下載 |
| `--from-list PATH` | 從列表批量下載 |
| `--screenshot-only` | 僅截圖不下載 |

### F-005 Daemon

| 命令 | 用途 |
|------|------|
| `--start` | 啟動守護程序 |
| `--stop` | 停止守護程序 |
| `--status` | 查看運行狀態 |
| `--run-once` | 單次執行（測試） |
| `--interval N` | 覆蓋循環間隔（秒） |

## 配置調整速查

編輯 `.config/kimi_tracker_config.json`：

| 需求 | 修改路徑 | 默認值 |
|------|---------|--------|
| 平台 URL | platform.base_url | https://www.kimi.com |
| 登入等待更久 | login.max_login_wait_sec | 600 |
| 檢測更頻密 | login.login_check_interval_sec | 3 |
| 強制每次重新認證 | login.force_reauth | false |
| daemon 更頻密 | daemon.interval_sec | 900 |
| 每次下載更多對話 | daemon.conversation_count | 10 |
| 下載超時更長 | download.download_timeout_ms | 10000 |
| 關閉唯一文件名 | download.unique_filename | true |
| 關閉 SHA256 去重 | download.deduplicate | true |
| 日誌級別 | logging.level | INFO |
| 登入判定不準 | selectors.login_indicators | 見預設值 |

## 故障排查

| 症狀 | 排查步驟 |
|------|---------|
| validate False | 執行 `--force-login --visible` 重新登入 |
| 提取 0 個對話 | 先 `--validate`，再 `--diagnose` |
| 下載超時 | 增加 `download.download_timeout_ms` |
| daemon 不啟動 | `tracker_daemon.py --status` 檢查 PID |
| selector 不匹配 | 更新 config，禁止改腳本 |

## 目錄結構

    {baseDir}/
    ├── .config/
    │   ├── kimi_tracker_config.json    # 唯一配置中心（Single Source of Truth）
    │   ├── downloads.json              # 運行時狀態
    │   └── conversations.json          # 運行時狀態
    ├── .logs/
    │   └── diagnose/                   # 診斷輸出
    ├── downloads/                      # 成功下載
    ├── .duplicate/                     # 重複歸檔
    ├── references/
    │   └── KIMI_TRACKER_USAGE_PLAN.md  # 完整計劃書
    └── scripts/                        # 全部腳本

## 注意

本技能不使用 `.env` 或 `.env.example`。
所有環境相關參數（如 `KIMI_BASE_URL`、`LOG_LEVEL`）已併入 `kimi_tracker_config.json`。
Agent 執行時只讀取 `.config/kimi_tracker_config.json`，不讀取任何其他配置檔案。
