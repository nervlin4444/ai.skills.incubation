---
title: "Kimi Agent Tracker - CLI Usage Reference"
name: "kimi-agent-tracker"
description: "腳本 CLI 用法教程。供人類和 Agent 參考的命令範例與常見問題。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T17:25:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/scripts/USAGE.md"
  github_path: "kimi-agent-tracker/scripts/USAGE.md"
---

# kimi-agent-tracker — CLI 用法教程

版本：v1.0.0
更新時間：2026-05-21 17:25:00

## 快速開始

### 1. 安裝依賴

    pip3 install playwright
    python3 -m playwright install chromium

### 2. 確保 connector 已部署

    ls ../chrome-playwright-connector/scripts/browser_connector.py

### 3. 登入（一次性）

    python scripts/kimi_login_manager.py --visible --stay-open 30

### 4. 提取對話列表

    python scripts/kimi_conversation_lister.py --count 4 --visible

### 5. 批量下載

    python scripts/kimi_downloader.py --from-list .config/conversations.json --visible

### 6. 啟動守護程序

    python scripts/tracker_daemon.py --start

## 完整命令參考

### kimi_login_manager.py（F-001）

    # 登入（可見模式，30秒後關閉）
    python scripts/kimi_login_manager.py --visible --stay-open 30

    # 強制重新登入
    python scripts/kimi_login_manager.py --visible --force-login

    # 驗證登入態
    python scripts/kimi_login_manager.py --validate

### kimi_conversation_lister.py（F-002）

    # 提取前 10 個對話
    python scripts/kimi_conversation_lister.py --count 10

    # 提取前 4 個對話（可見模式）
    python scripts/kimi_conversation_lister.py --count 4 --visible

    # 診斷模式（提取失敗時導出 HTML）
    python scripts/kimi_conversation_lister.py --count 4 --diagnose

    # 指定輸出路徑
    python scripts/kimi_conversation_lister.py --count 4 --output /tmp/my_conversations.json

### kimi_downloader.py（F-003）

    # 單個對話下載
    python scripts/kimi_downloader.py --url "https://www.kimi.com/chat/XXXX" --visible

    # 從列表批量下載
    python scripts/kimi_downloader.py --from-list .config/conversations.json --visible

    # 僅截圖（不下載）
    python scripts/kimi_downloader.py --url "https://www.kimi.com/chat/XXXX" --screenshot-only

    # 診斷模式
    python scripts/kimi_downloader.py --url "https://www.kimi.com/chat/XXXX" --diagnose

### state_manager.py（F-004）

    # 查看當前狀態
    python scripts/state_manager.py

    # 輸出示例：
    # Downloaded: 27
    # Duplicates: 8

### tracker_daemon.py（F-005）

    # 啟動守護程序（後台）
    python scripts/tracker_daemon.py --start

    # 停止守護程序
    python scripts/tracker_daemon.py --stop

    # 查看狀態
    python scripts/tracker_daemon.py --status

    # 單次執行（前台測試）
    python scripts/tracker_daemon.py --run-once

    # 自定義間隔（每 5 分鐘）
    python scripts/tracker_daemon.py --start --interval 300

    # 自定義提取數量（每次 20 個對話）
    python scripts/tracker_daemon.py --start --count 20

## 參數對照表

| 腳本 | 參數 | 類型 | 默認 | 說明 |
|------|------|------|------|------|
| kimi_login_manager | --visible | flag | False | 顯示瀏覽器視窗 |
| kimi_login_manager | --stay-open N | int | 30 | 登入後保持秒數 |
| kimi_login_manager | --force-login | flag | False | 強制重新 SMS 驗證 |
| kimi_login_manager | --validate | flag | False | 僅驗證登入態 |
| kimi_conversation_lister | --count N | int | 10 | 提取對話數量 |
| kimi_conversation_lister | --visible | flag | False | 顯示瀏覽器視窗 |
| kimi_conversation_lister | --diagnose | flag | False | 導出 HTML 診斷 |
| kimi_conversation_lister | --output PATH | str | None | 輸出文件路徑 |
| kimi_downloader | --url URL | str | None | 單個對話 URL |
| kimi_downloader | --from-list PATH | str | None | 對話列表 JSON |
| kimi_downloader | --visible | flag | False | 顯示瀏覽器視窗 |
| kimi_downloader | --diagnose | flag | False | 導出 HTML 診斷 |
| kimi_downloader | --screenshot-only | flag | False | 僅截圖不下載 |
| tracker_daemon | --start | flag | False | 啟動守護程序 |
| tracker_daemon | --stop | flag | False | 停止守護程序 |
| tracker_daemon | --status | flag | False | 查看狀態 |
| tracker_daemon | --run-once | flag | False | 單次執行 |
| tracker_daemon | --interval N | int | 900 | 循環間隔秒數 |
| tracker_daemon | --count N | int | 10 | 每次提取對話數 |

## 常見問題

### Q1: 登入失敗？

1. 確認已安裝 Playwright：`pip3 install playwright`
2. 確認 profile 存在：`ls ../chrome-playwright-connector/profiles/kimi_com/`
3. 強制重新登入：`python scripts/kimi_login_manager.py --force-login`

### Q2: 提取不到對話？

1. 確認登入態有效：`python scripts/kimi_login_manager.py --validate`
2. 使用診斷模式：`python scripts/kimi_conversation_lister.py --diagnose`
3. 檢查 diagnose/ 目錄下的 HTML dump

### Q3: 下載超時？

1. 使用可見模式觀察：`--visible`
2. 檢查 .logs/tracker_daemon.log
3. 確認網絡連接穩定

### Q4: Daemon 無法啟動？

1. 檢查是否已有實例運行：`python scripts/tracker_daemon.py --status`
2. 停止舊實例：`python scripts/tracker_daemon.py --stop`
3. 檢查 .config/tracker_daemon.pid

### Q5: 重複檔案太多？

這是正常行為。Kimi 不保留歷史版本，同一文件在不同對話中指向相同內容。
重複檔案自動移入 .duplicate/，永不刪除。
