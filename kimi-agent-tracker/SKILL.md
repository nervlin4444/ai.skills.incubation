---
title: "Kimi Agent Tracker - LLM Execution Guide"
name: "kimi-agent-tracker"
description: "Kimi 平台專用自動化追蹤器。負責對話列表提取、sandbox 文件下載、SHA256 去重歸檔。依賴 chrome-playwright-connector 提供瀏覽器實例。包含獨立 daemon 模式。"
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
  github_path: "kimi-agent-tracker/SKILL.md"
---

kimi-agent-tracker v1.0.0 — LLM 執行指令
========================================

LAYER 0 — 技能身份與入口約束
----------------------------

你是 kimi-agent-tracker 技能的執行代理。
本技能目錄為 kimi-agent-tracker，所有產出必須位於此命名空間下。

本技能是 Kimi 平台專用工具，依賴 chrome-playwright-connector 提供瀏覽器實例。
禁止在腳本中內嵌通用瀏覽器操作邏輯（如 launch_persistent_context），
所有瀏覽器操作必須通過 BrowserConnector 調用。

LAYER 1 — 核心能力與功能代號
----------------------------

| 功能代號 | 腳本名稱 | 職責 | 狀態 |
|----------|----------|------|------|
| F-001 | kimi_login_manager.py | SMS 登入、persistent profile 維護、登入態驗證 | 框架 |
| F-002 | kimi_conversation_lister.py | 從 Kimi 側邊欄提取對話列表 | 框架 |
| F-003 | kimi_downloader.py | 自動下載 sandbox 文件 | 框架 |
| F-004 | state_manager.py | SHA256 去重、downloads.json 狀態追蹤 | 框架 |
| F-005 | tracker_daemon.py | 獨立守護程序：定時循環執行下載任務 | 框架 |

LAYER 2 — 執行規則
-----------------

### RULE 2.1 — 依賴注入規範

本技能腳本必須動態注入 chrome-playwright-connector 路徑：

    import sys
    from pathlib import Path

    connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
    if str(connector_path) not in sys.path:
        sys.path.insert(0, str(connector_path))

    from browser_connector import BrowserConnector
    from profile_manager import url_to_profile_name

禁止將 connector 代碼複製到本技能目錄。

### RULE 2.2 — Profile 使用規範

Kimi 專用 profile 名稱固定為 kimi_com（由 url_to_profile_name 生成）。
登入態保存於 chrome-playwright-connector/profiles/kimi_com/。

    profile_name = url_to_profile_name("https://www.kimi.com")
    # 結果: kimi_com

### RULE 2.3 — 技能目錄結構

    {baseDir}/                      # 技能根目錄
    ├── .logs/                      # 運行日誌
    ├── .config/                    # 配置文件
    │   ├── downloads.json          # 下載狀態追蹤
    │   └── conversations.json      # 對話列表緩存
    ├── downloads/                  # 成功下載的檔案
    ├── .duplicate/                 # 重複檔案歸檔
    ├── .env.example
    └── scripts/

### RULE 2.4 — 下載機制分級

| 文件類型 | Kimi 行為 | Agent 策略 |
|----------|----------|------------|
| .zip, .py, .csv | 直接觸發瀏覽器下載 | expect_download() 捕獲 |
| .md, .txt | 打開預覽面板 → 點擊下載圖標 → 選擇格式 | 直接點擊優先 + 重試 + 預覽面板備用 |
| sandbox:// URLs | 內部協議，JS 觸發下載 | 全局 download 監聽 + 雙路徑掃描 |

### RULE 2.5 — 去重機制

1. 下載前檢查文件名是否已存在 → 生成唯一文件名（_1, _2, _3...）
2. 下載後計算 SHA256
3. SHA256 已存在於 downloads.json → 移入 .duplicate/
4. SHA256 不存在 → 保留在 downloads/

禁止刪除任何檔案（符合主人 no-delete 政策）。

### RULE 2.6 — Daemon 模式規範

tracker_daemon.py 是獨立守護程序，不依賴外部 cron/launchd。

    python scripts/tracker_daemon.py --start    # 啟動守護程序
    python scripts/tracker_daemon.py --stop     # 停止守護程序
    python scripts/tracker_daemon.py --status   # 查看狀態
    python scripts/tracker_daemon.py --run-once # 單次執行

Daemon 行為：
- 啟動時驗證登入態，無效則記錄錯誤並退出
- 每輪循環：提取對話列表 → 逐個下載 → 更新狀態
- 循環間隔可配置（默認 900 秒 = 15 分鐘）
- 使用 PID file 防止重複啟動
- 信號處理：SIGTERM / SIGINT 優雅關閉

### RULE 2.7 — 版本行為（關鍵發現）

Kimi 的 sandbox:// 鏈接不保留歷史版本。同一文件路徑在不同對話中始終指向最新版本。

    00:00 對話A → skill.py (v1) → sandbox:///mnt/agents/output/skill.py
    00:25 對話B → skill.py (v2) → 覆蓋同一 sandbox 路徑
    00:35 對話C → skill.py (v3) → 再次覆蓋

當下載器訪問對話 A、B、C 時，三個對話中的 skill.py 都指向 v3。
結果：只有第一個對話產生成功下載，其餘標記為 duplicate。

「舊檔案覆蓋新檔案」風險在 Kimi → 下載方向不存在。

LAYER 3 — 腳本接口規範
----------------------

### F-001 — kimi_login_manager.py

職責：Kimi 平台 SMS 登入與 persistent profile 維護。

必須實現以下函數：

    def login(profile_name: str = "kimi_com", visible: bool = True,
              stay_open: int = 30, force_login: bool = False) -> bool
        啟動瀏覽器，導航到 https://www.kimi.com/。
        若已有有效登入態，自動跳過 SMS。
        若需要 SMS，終端提示輸入手機號碼和驗證碼。
        登入成功後 profile 保存於 connector/profiles/kimi_com/。
        返回是否成功。

    def validate_login(profile_name: str = "kimi_com") -> bool
        快速檢查登入態是否有效（訪問 Kimi 首頁，檢查是否有對話列表）。
        無需人工介入，headless 模式執行。
        返回是否有效。

    def get_login_expiry_hint(profile_name: str = "kimi_com") -> str
        根據 profile 最後修改時間推算登入態有效期。
        返回提示文字（如「預計還有 5 天有效」）。

### F-002 — kimi_conversation_lister.py

職責：從 Kimi 側邊欄提取對話列表。

必須實現以下函數：

    def extract_conversations(profile_name: str = "kimi_com",
                              count: int = 10, visible: bool = False,
                              diagnose: bool = False) -> list
        啟動瀏覽器，訪問 Kimi 首頁，從側邊欄提取對話。
        返回列表：[{"index": 0, "title": "...", "url": "...", "pinned": true}, ...]
        按 Kimi 側邊欄排序（最新活動在前，置頂優先）。
        diagnose=True 時導出側邊欄 HTML 到 diagnose/。

    def save_conversation_list(conversations: list, path: str = None) -> str
        將對話列表保存為 JSON。path 為 None 時保存到 .config/conversations.json。
        返回實際保存路徑。

### F-003 — kimi_downloader.py

職責：自動下載 Kimi 對話中的 sandbox 文件。

必須實現以下函數：

    def download_from_url(url: str, profile_name: str = "kimi_com",
                          visible: bool = False, diagnose: bool = False,
                          screenshot_only: bool = False) -> dict
        訪問單個對話 URL，掃描所有可下載文件並執行下載。
        返回 {"success": [...], "duplicates": [...], "errors": [...]}。

    def download_from_list(list_path: str, profile_name: str = "kimi_com",
                           visible: bool = False) -> dict
        讀取 JSON 對話列表，逐個處理。
        同一 browser context 重複使用，無需重複登入。
        返回批量處理結果。

    def _handle_direct_download(page, link_element) -> dict
        處理 .zip/.py/.csv 等直接下載類型。
        使用 expect_download() 捕獲。

    def _handle_preview_panel_download(page, link_element) -> dict
        處理 .md/.txt 等預覽面板類型。
        策略：直接點擊優先 → 等待 5s → 檢查下載 → 2s 延遲重試 → 預覽面板備用。

### F-004 — state_manager.py

職責：下載狀態追蹤與 SHA256 去重。

必須實現以下函數：

    def load_state(path: str = None) -> dict
        讀取 downloads.json。文件不存在時返回初始狀態。
        返回 {"downloaded": {hash: {...}}, "duplicates": [...]}。

    def save_state(state: dict, path: str = None) -> str
        保存狀態到 downloads.json。
        返回實際保存路徑。

    def compute_sha256(file_path: str) -> str
        計算文件 SHA256 哈希值。

    def get_unique_filename(base_dir: str, filename: str) -> str
        若文件名已存在，追加 _1, _2, _3... 直到唯一。
        返回唯一文件名（不含路徑）。

    def register_download(state: dict, file_path: str, conversation: str) -> dict
        註冊新下載：計算 SHA256 → 檢查重複 → 決定保留或移入 .duplicate/。
        返回更新後的 state。

### F-005 — tracker_daemon.py

職責：獨立守護程序，定時循環執行下載任務。

CLI 參數：

    --start         啟動守護程序（後台運行）
    --stop          停止守護程序
    --status        查看運行狀態
    --run-once      單次執行（前台，用於測試）
    --interval N    循環間隔秒數（默認 900）
    --count N       每次提取對話數量（默認 10）

必須實現以下方法：

    class TrackerDaemon:
        def __init__(self, interval: int = 900, count: int = 10)
            初始化配置、日誌、PID file 路徑。

        def run_cycle(self)
            單次循環：驗證登入態 → 提取對話列表 → 下載文件 → 更新狀態。

        def start(self)
            啟動守護程序循環。處理信號、寫入 PID、定時執行。

        def stop(self)
            讀取 PID file，發送 SIGTERM。

        def status(self)
            檢查 PID file 是否存在且進程存活。

        def run_once(self)
            前台單次執行，用於測試和調試。

LAYER 4 — 輸出與交付約束
-------------------------

### RULE 4.1 — 產出文件清單

每次執行本技能，必須檢查以下文件是否存在於 kimi-agent-tracker 目錄：
- SKILL.md
- README.md
- scripts/USAGE.md
- .env.example
- scripts/kimi_login_manager.py
- scripts/kimi_conversation_lister.py
- scripts/kimi_downloader.py
- scripts/state_manager.py
- scripts/tracker_daemon.py

### RULE 4.2 — 待確認機制

任何未定參數必須列入 CONFIRMATION.md。
禁止在未經主人確認的情況下假設數值並寫入腳本。

### RULE 4.3 — 版本鎖定

本技能版本 v1.0.0 為框架階段。所有接口定義視為 LOCK PERMANENT。
實際實現邏輯視為 FLEX EVOLVING，可在主人確認後迭代。

### RULE 4.4 — 禁止行為

- 禁止在腳本中內嵌通用瀏覽器操作（必須通過 connector）
- 禁止刪除任何已下載檔案（no-delete 政策）
- 禁止修改其他技能的檔案或目錄
- 禁止在 SKILL.md 中使用 ``` 圍欄，改用 4 空格縮進或表格
