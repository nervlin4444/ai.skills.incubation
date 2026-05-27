---
title: "Kimi Agent Tracker - Complete Usage Plan"
name: "kimi-agent-tracker"
description: "LLM Agent 執行計劃書。覆蓋 F001~F005 全部場景 + 預留擴展。Agent 必須按此計劃執行，禁止擅自修改代碼。"
version: "4.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-26T06:53:23.027+00:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/references/KIMI_TRACKER_USAGE_PLAN.md"
  github_path: "kimi-agent-tracker/references/KIMI_TRACKER_USAGE_PLAN.md"
---

# Kimi Agent Tracker v1.1.0 — 完整執行計劃書

## 核心原則

| 原則 | 說明 |
|------|------|
| 禁止改代碼 | 所有參數調整通過 `.config/kimi_tracker_config.json`，禁止編輯 `.py` |
| 禁止改 selector | selector 統一在 config 中管理，發現不匹配時更新 config 而非腳本 |
| 分層測試 | 每個 Phase 獨立驗證，失敗即停，不跳過 |
| 診斷優先 | 遇到問題先執行 `--diagnose`，分析 HTML 後再決定下一步 |

---

## PHASE 0 — 環境檢查（每次執行前必做）

### Step 0.1: 檢查 playwright 安裝

    python3 -m pip list | grep playwright

通過標準: 顯示 `playwright x.x.x`
失敗排查: 執行 `python3 -m pip install playwright --user`

### Step 0.2: 檢查 Chromium 瀏覽器

    python3 -m playwright install chromium

通過標準: Exit Code 0
失敗排查: 檢查網絡連接，或手動下載 Chromium

### Step 0.3: 檢查目錄結構

    ls {baseDir}/
    ls {baseDir}/scripts/
    ls {baseDir}/.config/
    ls {baseDir}/.logs/

通過標準: 以下目錄全部存在
- scripts/ (含 kimi_login_manager.py, kimi_conversation_lister.py, kimi_downloader.py, state_manager.py, tracker_daemon.py)
- .config/ (含 kimi_tracker_config.json)
- .logs/ (含 diagnose/)
- downloads/
- .duplicate/

---

## PHASE 1 — F001 登入管理（kimi_login_manager.py）

### 場景 1.1: 首次登入（無 profile）

執行命令:

    python3 scripts/kimi_login_manager.py --visible --stay-open 300

預期流程:
1. 瀏覽器打開，顯示 Kimi 登入頁
2. 用戶輸入手機號碼 → 獲取 SMS → 輸入驗證碼
3. 腳本每 3 秒檢測一次登入態（config: login_check_interval_sec）
4. 登入成功後自動關閉瀏覽器，session 保存到 profile

通過標準: 輸出 `[LOGIN] Login detected after Xs. Session saved.`
失敗排查:
- 瀏覽器過早關閉 → 檢查 config `max_login_wait_sec` 是否足夠
- 檢測不到登入 → 執行 `--diagnose`，查看 selector 是否匹配
- 超時 → 檢查網絡，或增加 `max_login_wait_sec`

### 場景 1.2: 驗證現有 session

執行命令:

    python3 scripts/kimi_login_manager.py --validate

預期輸出:

    [VALIDATE] Login valid: True

通過標準: 返回 True
失敗排查:
- 返回 False → session 過期，執行場景 1.1 重新登入
- 報錯 → 執行 `--diagnose` 分析

### 場景 1.3: 強制重新登入

執行命令:

    python3 scripts/kimi_login_manager.py --force-login --visible --stay-open 300

用途: session 過期或需要切換帳號時使用

### 場景 1.4: 診斷登入頁面

執行命令:

    python3 scripts/kimi_login_manager.py --diagnose

輸出內容:
- Login detected: True/False
- 各 selector 命中數量
- HTML 保存路徑
- Screenshot 保存路徑

用途: 當 validate/login 異常時，分析實際頁面結構

---

## PHASE 2 — F002 對話列表提取（kimi_conversation_lister.py）

### 場景 2.1: 提取對話列表

執行命令:

    python3 scripts/kimi_conversation_lister.py --count 10

預期輸出:

    [EXTRACT] Found 10 conversations
    Saved 10 conversations to {baseDir}/.config/conversations.json

通過標準: conversations.json 存在且含對話數據
失敗排查:
- 0 個對話 → 先執行 F001 確認登入態
- selector 不匹配 → 更新 config `selectors.conversation_items`
- 執行 `--diagnose` 導出側邊欄 HTML 分析

### 場景 2.2: 診斷對話列表提取

執行命令:

    python3 scripts/kimi_conversation_lister.py --diagnose

用途: 當提取數量異常時分析側邊欄 DOM 結構

---

## PHASE 3 — F003 自動下載（kimi_downloader.py）

### 場景 3.1: 從單個對話下載

執行命令:

    python3 scripts/kimi_downloader.py --url "https://www.kimi.com/chat/XXXX"

預期輸出:

    [DOWNLOAD] Success: [file1.zip, file2.md]
    [DOWNLOAD] Duplicates: []
    [DOWNLOAD] Errors: []

通過標準: 檔案出現在 downloads/ 目錄
失敗排查:
- 下載超時 → 增加 config `download.download_timeout_ms`
- 預覽面板下載失敗 → 檢查 config `download.preview_extensions`
- 直接下載失敗 → 檢查 config `download.direct_extensions`

### 場景 3.2: 從列表批量下載

執行命令:

    python3 scripts/kimi_downloader.py --from-list {baseDir}/.config/conversations.json

預期: 逐個處理對話，同一 browser context 重複使用

### 場景 3.3: 僅截圖不下載

執行命令:

    python3 scripts/kimi_downloader.py --url "..." --screenshot-only

用途: 調試下載流程，確認頁面結構

---

## PHASE 4 — F004 狀態管理（state_manager.py）

### 場景 4.1: 檢查下載狀態

執行命令:

    python3 scripts/state_manager.py --status

預期: 顯示已下載檔案數、重複檔案數、最後更新時間

### 場景 4.2: 手動標記重複

執行命令:

    python3 scripts/state_manager.py --mark-duplicate {file_path}

用途: 誤判為新檔案時手動修正

---

## PHASE 5 — F005 Daemon 守護程序（tracker_daemon.py）

### 場景 5.1: 啟動 Daemon

執行命令:

    python3 scripts/tracker_daemon.py --start

預期: PID file 創建，開始循環執行
循環間隔: config `daemon.interval_sec`（默認 900 秒 = 15 分鐘）

### 場景 5.2: 單次執行（測試用）

執行命令:

    python3 scripts/tracker_daemon.py --run-once

預期: 執行一次完整流程（登入驗證 → 提取對話 → 下載 → 狀態更新）

### 場景 5.3: 停止 Daemon

執行命令:

    python3 scripts/tracker_daemon.py --stop

### 場景 5.4: 查看 Daemon 狀態

執行命令:

    python3 scripts/tracker_daemon.py --status

---

## 預留擴展場景（將來實現）

### 場景 6.1: 新增對話 ID 輸入

計劃: 支持從外部輸入對話 ID 列表，而非僅從側邊欄提取
配置項: 待加入 config `input.conversation_ids`

### 場景 6.2: 自動發送問題

計劃: 對指定對話自動輸入問題並等待回覆
配置項: 待加入 config `input.auto_questions`

### 場景 6.3: 定時任務排程

計劃: 支持 cron 表達式，替代固定 interval_sec
配置項: 待加入 config `daemon.cron_expression`

---

## 問題排查矩陣

| 症狀 | 可能原因 | 排查步驟 | 解決方案 |
|------|---------|---------|---------|
| validate 返回 False | session 過期 | 執行 `--diagnose` 確認 | 重新登入 `--force-login` |
| validate 返回 True 但未登入 | selector 誤判 | 查看 diagnose HTML | 更新 config `selectors.login_indicators` |
| 瀏覽器打開後秒關 | 誤判登入成功 | 檢查 diagnose 輸出 | 修正 selector 或增加 `login_check_interval_sec` |
| 提取 0 個對話 | 未登入 / DOM 變更 | 先 `--validate`，再 `--diagnose` | 確認登入或更新 selector |
| 下載超時 | 網絡慢 / selector 過期 | 檢查 `.logs/` 日誌 | 增加 `download_timeout_ms` |
| daemon 不啟動 | PID 文件已存在 | `tracker_daemon.py --status` | `--stop` 後再 `--start` |
| headless 模式崩潰 | Chromium 啟動失敗 | 檢查 `.logs/diagnose/` | 參考 chrome-playwright-connector 診斷 |

---

## 配置調整速查

| 需求 | 修改 config 路徑 | 默認值 |
|------|------------------|--------|
| 登入等待時間 | `login.max_login_wait_sec` | 600 |
| 登入檢測間隔 | `login.login_check_interval_sec` | 3 |
| 驗證超時 | `login.validate_timeout_ms` | 5000 |
| daemon 循環間隔 | `daemon.interval_sec` | 900 |
| 每次提取對話數 | `daemon.conversation_count` | 10 |
| 下載超時 | `download.download_timeout_ms` | 10000 |
| 直接下載副檔名 | `download.direct_extensions` | [".zip", ".py", ".csv"] |
| 預覽面板副檔名 | `download.preview_extensions` | [".md", ".txt"] |
| 登入判定 selector | `selectors.login_indicators` | [".chat-info-item", ".user-avatar", ".user-name"] |

---

## 禁止行為（LOCK）

| 編號 | 禁止行為 | 後果 |
|------|---------|------|
| L001 | 直接編輯 `.py` 腳本修改參數 | 下次更新覆蓋，配置漂移 |
| L002 | 在腳本中硬編碼 selector | Kimi UI 更新後全面失效 |
| L003 | 擅自刪除 profile 目錄 | 登入態丟失，需重新 SMS |
| L004 | 跳過 Phase 0 環境檢查 | 未知環境問題難以排查 |
| L005 | daemon 崩潰後不自動重啟 | 長期運行中斷 |
