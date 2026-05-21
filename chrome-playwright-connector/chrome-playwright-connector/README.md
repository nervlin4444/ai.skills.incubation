---
title: "Chrome Playwright Connector - Usage Guide"
name: "chrome-playwright-connector"
description: "通用瀏覽器自動化連接器的人類可讀說明書。基於 Playwright 封裝 Chromium 瀏覽器生命週期、Persistent Profile 管理、通用頁面操作與診斷工具。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T16:39:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/README.md"
  github_path: "chrome-playwright-connector/README.md"
---

Chrome Playwright Connector
===========================

通用瀏覽器自動化連接器，基於 Playwright。

Version: 1.0.0 | Updated: 2026-05-21

Table of Contents
-----------------

1.  Background & Motivation
2.  Technical Decision
3.  Architecture Overview
4.  File Inventory
5.  Installation
6.  Usage Guide
7.  BrowserConnector API Reference
8.  Profile Management
9.  Diagnostic Tools
10. Troubleshooting
11. Known Limitations
12. Directory Structure
13. Author

Background & Motivation
-----------------------

當多個技能都需要瀏覽器自動化時，每個技能各自安裝 Playwright、管理 profile、處理下載邏輯會造成大量重複代碼。本連接器將通用的瀏覽器能力抽離為獨立技能，供上游技能調用。

Technical Decision
------------------

| Criteria | WebBridge | Playwright |
|----------|-----------|------------|
| Browser Support | Chrome/Edge only | Chromium, Firefox, WebKit |
| Wait Mechanism | sleep-based | wait_for_selector, networkidle |
| Local Execution | MCP Server required | Local headless |
| Cookie Persistence | No mechanism | Persistent profile |

Architecture Overview
---------------------

    +-------------------+        +-------------------------+
    | kimi-agent-tracker|  -->   | chrome-playwright-      |
    | (上游技能)         |        | connector               |
    +-------------------+        | (通用瀏覽器能力)         |
                                 +-------------------------+
                                          |
                                          v
                                 +-------------------------+
                                 | {baseDir}/            |
                                 | ├── profiles/           |
                                 | ├── .logs/              |
                                 | ├── .config/            |
                                 | ├── diagnose/           |
                                 | └── downloads/          |
                                 +-------------------------+

File Inventory
--------------

| File | Purpose |
|------|---------|
| browser_connector.py | 核心瀏覽器連接器類（BrowserConnector） |
| profile_manager.py | Profile 管理工具 |
| diagnostic_kit.py | 診斷與調試工具 |

Installation
------------

    pip3 install playwright
    python3 -m playwright install chromium

Usage Guide
-----------

### 基本使用

    from browser_connector import BrowserConnector

    driver = BrowserConnector(profile_name="kimi_com", visible=True)
    driver.launch()
    page = driver.navigate("https://www.kimi.com")
    driver.screenshot("homepage.png")
    driver.close()

### Profile 管理

    from profile_manager import list_profiles, validate_profile

    print(list_profiles())
    print(validate_profile("kimi_com"))

BrowserConnector API Reference
------------------------------

### 初始化

    BrowserConnector(profile_name="default", headless=True,
                     download_dir=None, visible=False, timeout=30000)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| profile_name | str | "default" | Profile 子目錄名稱（網站域名格式） |
| headless | bool | True | 無頭模式 |
| download_dir | str | None | 覆蓋默認下載路徑 |
| visible | bool | False | 顯示瀏覽器視窗 |
| timeout | int | 30000 | 全局超時（毫秒） |

### 方法清單

| # | 方法 | 用途 |
|---|------|------|
| 1 | launch() | 啟動瀏覽器 |
| 2 | navigate(url) | 導航到網址 |
| 3 | click(selector) | 點擊元素 |
| 4 | fill(selector, text) | 填寫輸入框 |
| 5 | wait_for_selector(selector) | 等待元素出現 |
| 6 | screenshot(path) | 截圖 |
| 7 | dump_html(path) | 導出 HTML |
| 8 | dump_elements(selector) | 列舉元素 |
| 9 | get_download(timeout) | 等待下載 |
| 10 | evaluate(js_code) | 執行 JavaScript |
| 11 | close() | 關閉瀏覽器 |

Profile Management
------------------

    {baseDir}/profiles/
    ├── kimi_com/
    ├── github_com/
    └── default/

Profile 命名規則：網站主域名，點號換下劃線，全部小寫。

Diagnostic Tools
----------------

自動觸發條件：元素未找到、點擊失敗、頁面空白、--diagnose 參數。

輸出位置：{baseDir}/diagnose/

Troubleshooting
---------------

| Symptom | Cause | Solution |
|---------|-------|----------|
| Browser 啟動失敗 | Profile 損壞 | 刪除 profile 目錄重新創建 |
| 元素未找到 | Selector 過期 | 使用 --diagnose 導出 HTML 分析 |
| 點擊無效 | 元素被覆蓋 | 使用 force=True 或調整視窗大小 |

Known Limitations
-----------------

1. WebKit persistent profile 在 macOS 上不穩定
2. 多個進程不能同時使用同一個 profile
3. 視窗大小影響彈出層位置

Directory Structure
-------------------

    {baseDir}/
    ├── .logs/
    ├── .config/
    ├── profiles/
    ├── diagnose/
    └── downloads/

Author
------

Kevin Lin (nervlin4444)
