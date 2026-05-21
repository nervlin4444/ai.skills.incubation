---
title: "Chrome Playwright Connector - CLI Usage Reference"
name: "chrome-playwright-connector"
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
  github_path: "chrome-playwright-connector/scripts/USAGE.md"
---

# chrome-playwright-connector — CLI 用法教程

版本：v1.0.0
更新時間：2026-05-21 17:25:00

## 快速開始

### 1. 安裝依賴

    pip3 install playwright
    python3 -m playwright install chromium

### 2. 基本使用

    from browser_connector import BrowserConnector

    driver = BrowserConnector(profile_name="kimi_com", visible=True)
    driver.launch()
    page = driver.navigate("https://www.kimi.com")
    driver.screenshot("homepage.png")
    driver.close()

## 完整命令參考

### browser_connector.py（F-001）

    # 基本啟動
    python scripts/browser_connector.py

    # 輸出：Page title: Example Domain

### profile_manager.py（F-002）

    # 列出所有 profile
    python scripts/profile_manager.py

    # 輸出示例：
    # Profiles: ['kimi_com', 'github_com', 'default']
    # kimi_com valid: {'valid': True, 'size_mb': 12.5, 'files_count': 45, 'last_used': '2026-05-21 16:30:00'}
    # url_to_profile: kimi_com

### diagnostic_kit.py（F-003）

    # 此腳本為庫函數，需配合 Playwright page 對象使用
    # 在 browser_connector.py 中自動觸發診斷時調用

## BrowserConnector 參數對照

| 參數 | 類型 | 默認值 | 說明 |
|------|------|--------|------|
| profile_name | str | "default" | Profile 子目錄名稱 |
| headless | bool | True | 無頭模式 |
| download_dir | str | None | 覆蓋默認下載路徑 |
| visible | bool | False | 顯示瀏覽器視窗 |
| timeout | int | 30000 | 全局超時（毫秒） |

## Profile 命名規則

| 網站 | Profile 目錄名 |
|------|---------------|
| https://www.kimi.com/ | kimi_com |
| https://github.com/ | github_com |
| https://www.google.com/ | google_com |
| 無特定網站 | default |

轉換規則：主域名（不含 www），點號換下劃線，全部小寫。

## 常見問題

### Q1: Browser 啟動失敗？

1. 確認 Playwright 已安裝：`pip3 install playwright`
2. 確認 Chromium 已下載：`python3 -m playwright install chromium`
3. 檢查 profile 目錄權限：`ls -la profiles/`

### Q2: 元素未找到？

使用診斷模式導出 HTML 分析：

    driver.dump_html("debug.html")
    driver.screenshot("debug.png")

### Q3: 多個技能如何共用 connector？

確保所有技能與 connector 處於同級目錄：

    skills/
    ├── chrome-playwright-connector/
    ├── kimi-agent-tracker/
    └── github-restful-api-connector/

各技能腳本自動動態注入 connector 路徑。
