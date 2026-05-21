---
title: "Chrome Playwright Connector - LLM Execution Guide"
name: "chrome-playwright-connector"
description: "通用瀏覽器自動化連接器。基於 Playwright 封裝 Chromium 瀏覽器生命週期、Persistent Profile 管理、通用頁面操作與診斷工具。不依賴特定網站，供上游技能調用。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T18:15:00+08:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/SKILL.md"
  github_path: "chrome-playwright-connector/SKILL.md"
---

chrome-playwright-connector v1.0.0 — LLM 執行指令
================================================

LAYER 0 — 技能身份與入口約束
----------------------------

你是 chrome-playwright-connector 技能的執行代理。
本技能目錄為 chrome-playwright-connector，所有產出必須位於此命名空間下。
你不得修改其他技能檔案，不得偏離本技能定義的接口規範。

本技能是通用底層工具，不認識任何特定網站（Kimi、GitHub、Jira 等）。
上游技能通過本技能獲取瀏覽器實例並執行操作。

LAYER 1 — 核心能力與功能代號
----------------------------

| 功能代號 | 腳本名稱 | 職責 | 狀態 |
|----------|----------|------|------|
| F-001 | browser_connector.py | 瀏覽器連接器核心：啟動、導航、操作、關閉 | 框架 |
| F-002 | profile_manager.py | Profile 管理：創建、驗證、清理、多網站隔離 | 框架 |
| F-003 | diagnostic_kit.py | 診斷工具包：HTML dump、截圖、元素列舉、日誌 | 框架 |

LAYER 2 — 執行規則
-----------------

### RULE 2.1 — 技能目錄結構規範

所有運行時數據必須置於本技能目錄下，禁止寫入全局路徑（如 ~/.xxx/）。

    {baseDir}/                      # 技能根目錄
    ├── .logs/                      # 運行日誌，按 YYYY-MM-DD 滾動
    ├── .config/                    # 配置文件、環境變數
    ├── profiles/                   # 瀏覽器 persistent profile
    │   ├── {site_name}/            # 以網站名稱命名
    │   └── default/                # 無特定網站時使用
    ├── diagnose/                   # 診斷輸出（HTML、PNG、TXT）
    └── downloads/                  # 默認下載目錄（可被上游覆蓋）

### RULE 2.2 — Profile 命名規範

Profile 子目錄以網站名稱命名，遵循以下轉換規則：

| 網站 | Profile 目錄名 | 說明 |
|------|---------------|------|
| https://www.kimi.com/ | kimi_com | 域名點號換下劃線 |
| https://github.com/ | github_com | 同上 |
| https://www.google.com/ | google_com | 同上 |
| 無特定網站 | default | 通用預設 |

轉換規則：
1. 取主域名（不含 www 前綴）
2. 點號 . 換為下劃線 _
3. 不含頂級域名後的 path
4. 全部小寫

### RULE 2.3 — 瀏覽器支援矩陣

| 瀏覽器 | 支援狀態 | 用途 |
|--------|----------|------|
| Chromium | 主要 | 推薦，persistent profile 最穩定 |
| Firefox | 備用 | 需要時啟用 |
| WebKit | 備用 | Safari 模擬，但 persistent profile 不穩定 |

默認使用 Chromium。除非主人明確要求，否則不啟用 Firefox 或 WebKit。

### RULE 2.4 — 啟動參數規範

launch_persistent_context() 必須包含：

    user_data_dir = profile_path
    headless = not visible
    downloads_path = download_dir or default
    viewport = {"width": 1400, "height": 900}
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage"
    ]

禁止強制最大化視窗。

### RULE 2.5 — 等待機制分級

| 場景 | 方法 | 超時 |
|------|------|------|
| 頁面導航完成 | wait_for_load_state("networkidle") | 30s |
| 元素出現 | wait_for_selector(selector, state="visible") | 30s |
| 元素可點擊 | wait_for_selector + 延遲 | 30s |
| 下載完成 | expect_download + filesystem scan | 10s |
| 彈出層消失 | wait_for_selector(selector, state="hidden") | 5s |

### RULE 2.6 — 錯誤處理分級

| 錯誤類型 | 行為 | 回報方式 |
|----------|------|----------|
| Browser 啟動失敗 | 停止，報錯 profile 損壞 | 日誌 + 異常拋出 |
| 導航超時 | 重試 1 次，仍失敗則停止 | 日誌 |
| 元素未找到 | 截圖 + HTML dump 後停止 | 日誌 + diagnose/ |
| 點擊失敗 | 延遲 2s 重試 1 次 | 日誌 + diagnose/ |
| 下載超時 | 掃描 filesystem 備用路徑 | 日誌 |

### RULE 2.7 — 診斷觸發條件

以下情況自動觸發診斷：

- 元素未找到（selector timeout）
- 點擊失敗（element not interactable）
- 導航後頁面空白（content length < 100）
- 主人傳入 --diagnose 參數

診斷輸出：

    {baseDir}/diagnose/
    ├── {timestamp}_page.html
    ├── {timestamp}_screenshot.png
    └── {timestamp}_elements.txt

LAYER 3 — 腳本接口規範
----------------------

### F-001 — browser_connector.py

職責：所有瀏覽器操作的唯一通道。

必須實現以下類與方法：

    class BrowserConnector:
        def __init__(self, profile_name: str = "default", headless: bool = True,
                     download_dir: str = None, visible: bool = False,
                     timeout: int = 30000)
            profile_name: 對應 profiles/ 下的子目錄名稱
            headless: True = 無頭模式，False = 可見視窗
            download_dir: 覆蓋默認下載路徑
            visible: 同 headless=False，優先級更高
            timeout: 全局超時（毫秒）

        def launch(self) -> BrowserContext
            啟動 persistent context，返回 BrowserContext 實例。
            若 profile 目錄不存在，自動創建。

        def navigate(self, url: str, wait_until: str = "networkidle") -> Page
            導航到指定 URL，等待頁面穩定後返回 Page 實例。

        def click(self, selector: str, force: bool = False, retry: int = 1) -> bool
            點擊元素。失敗後延遲 2s 重試 retry 次。
            force=True 時使用 JavaScript click。

        def fill(self, selector: str, text: str) -> bool
            在輸入框填寫文字。自動清除原有內容。

        def wait_for_selector(self, selector: str, state: str = "visible",
                              timeout: int = 30000) -> ElementHandle
            等待元素進入指定狀態。

        def screenshot(self, path: str = None) -> str
            截取當前頁面。path 為 None 時自動生成到 diagnose/。
            返回實際保存路徑。

        def dump_html(self, path: str = None) -> str
            導出當前頁面完整 HTML。path 為 None 時自動生成。
            返回實際保存路徑。

        def dump_elements(self, selector: str = "*") -> list
            列舉當前頁面所有匹配元素，返回 [(tag, text, attributes, selector), ...]。

        def get_download(self, timeout: int = 10000) -> Download
            等待並返回下一個下載事件。用於 expect_download 模式。

        def evaluate(self, js_code: str) -> any
            執行 JavaScript 代碼，返回執行結果。

        def close(self)
            關閉 browser context，釋放資源。

### F-002 — profile_manager.py

職責：Profile 目錄的生命週期管理。

必須實現以下函數：

    def get_profile_path(profile_name: str) -> Path
        返回 {baseDir}/profiles/{profile_name}/ 的 Path 對象。
        目錄不存在時自動創建。

    def validate_profile(profile_name: str) -> dict
        檢查 profile 是否可用。
        返回 {"valid": bool, "size_mb": float, "files_count": int, "last_used": str}

    def list_profiles() -> list
        返回所有已存在的 profile 名稱列表。

    def remove_profile(profile_name: str) -> bool
        刪除指定 profile 目錄。返回是否成功。
        警告：此操作不可逆，必須經主人確認。

    def clone_profile(source: str, target: str) -> bool
        複製現有 profile 到新名稱。用於備份或測試。

    def url_to_profile_name(url: str) -> str
        將網址轉換為 profile 目錄名稱。
        例如 https://www.kimi.com/ → kimi_com

### F-003 — diagnostic_kit.py

職責：診斷工具集合。

必須實現以下函數：

    def diagnose_page(page: Page, label: str = None) -> dict
        對當前頁面執行完整診斷：截圖 + HTML dump + 元素列舉。
        返回 {"screenshot": path, "html": path, "elements": path, "timestamp": str}

    def diagnose_selector(page: Page, selector: str) -> dict
        針對特定 selector 診斷：檢查是否存在、是否可見、是否可點擊。
        返回 {"exists": bool, "visible": bool, "interactable": bool, "html": str}

    def list_buttons(page: Page) -> list
        列舉頁面所有按鈕元素（button, div[role=button], a 等）。
        返回 [(text, class, id, selector), ...]。

    def save_diagnose_report(results: dict, path: str = None) -> str
        將診斷結果保存為 JSON 報告。path 為 None 時自動生成。
        返回實際保存路徑。

LAYER 4 — 輸出與交付約束
-------------------------

### RULE 4.1 — 產出文件清單

每次執行本技能，必須檢查以下文件是否存在於 chrome-playwright-connector 目錄：
- SKILL.md（本文件，LLM 執行指令）
- README.md（人類可讀說明書）
- scripts/USAGE.md（CLI 用法教程）
- .env.example（環境變數模板）
- scripts/browser_connector.py
- scripts/profile_manager.py
- scripts/diagnostic_kit.py

### RULE 4.2 — 待確認機制

任何未定參數必須列入 CONFIRMATION.md。
禁止在未經主人確認的情況下假設數值並寫入腳本。

### RULE 4.3 — 版本鎖定

本技能版本 v1.0.0 為框架階段。所有接口定義視為 LOCK PERMANENT。
實際實現邏輯視為 FLEX EVOLVING，可在主人確認後迭代。

### RULE 4.4 — 禁止行為

- 禁止在腳本中內嵌任何網站特定的 selector
- 禁止在未經主人授權時刪除 profile 目錄
- 禁止修改其他技能的檔案或目錄
- 禁止在 SKILL.md 中使用 ``` 圍欄，改用 4 空格縮進或表格
