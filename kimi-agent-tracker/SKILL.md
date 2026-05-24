---
title: "Kimi Agent Tracker - LLM Execution Guide"
name: "kimi-agent-tracker"
description: "Kimi 平台專用自動化追蹤器。所有可調參數從單一 config.json 讀取，不使用 .env，禁止硬編碼。"
version: "1.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T02:15:00+08:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{baseDir}/SKILL.md"
  github_path: "kimi-agent-tracker/SKILL.md"
---

# kimi-agent-tracker v1.1.0 — LLM 執行指令

## LAYER 0 — 技能身份與入口約束

你是 kimi-agent-tracker 技能的執行代理。
本技能目錄為 kimi-agent-tracker，所有產出必須位於此命名空間下。
本技能是 Kimi 平台專用工具，依賴 chrome-playwright-connector 提供瀏覽器實例。
禁止在腳本中內嵌通用瀏覽器操作邏輯，所有瀏覽器操作必須通過 BrowserConnector 調用。

## LAYER 1 — 核心能力與功能代號

| 功能代號 | 腳本名稱 | 職責 | 狀態 |
|----------|----------|------|------|
| F-001 | kimi_login_manager.py | SMS 登入、persistent profile 維護、登入態驗證 | 已實現 |
| F-002 | kimi_conversation_lister.py | 從 Kimi 側邊欄提取對話列表 | 已實現 |
| F-003 | kimi_downloader.py | 自動下載 sandbox 文件 | 已實現 |
| F-004 | state_manager.py | SHA256 去重、狀態追蹤 | 已實現 |
| F-005 | tracker_daemon.py | 獨立守護程序，定時循環 | 已實現 |

## LAYER 2 — 執行規則

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

Kimi 專用 profile 名稱固定為 kimi_com。
登入態保存於 chrome-playwright-connector/profiles/kimi_com/。

### RULE 2.3 — 技能目錄結構

    {baseDir}/
    ├── .logs/
    │   └── diagnose/
    ├── .config/
    │   ├── kimi_tracker_config.json    # 唯一配置中心（Single Source of Truth）
    │   ├── downloads.json              # 運行時狀態（SHA256 哈希表）
    │   └── conversations.json          # 運行時狀態（對話列表緩存）
    ├── downloads/                      # 成功下載的檔案
    ├── .duplicate/                     # 重複檔案（SHA256 匹配後移入）
    ├── references/
    │   └── KIMI_TRACKER_USAGE_PLAN.md  # 完整執行計劃與問題排查
    ├── scripts/
    ├── USAGE.md
    ├── README.md
    └── SKILL.md

### RULE 2.4 — 單一配置規範（v1.1 核心變更）

本技能只使用單一配置檔案：`.config/kimi_tracker_config.json`。
不使用 .env，不使用多個 .json 分散配置。
所有可調參數必須從 config 讀取，禁止在 .py 中硬編碼。

| 參數類別 | config 路徑 | 默認值 |
|----------|------------|--------|
| 平台 URL | platform.base_url | https://www.kimi.com |
| 登入等待時間 | login.max_login_wait_sec | 600 |
| 登入檢測間隔 | login.login_check_interval_sec | 3 |
| 驗證超時 | login.validate_timeout_ms | 5000 |
| 強制重新認證 | login.force_reauth | false |
| daemon 循環間隔 | daemon.interval_sec | 900 |
| 每次提取對話數 | daemon.conversation_count | 10 |
| 下載超時 | download.download_timeout_ms | 10000 |
| 唯一文件名 | download.unique_filename | true |
| SHA256 去重 | download.deduplicate | true |
| 日誌級別 | logging.level | INFO |
| 登入判定 selector | selectors.login_indicators | [".chat-info-item", ".user-avatar", ".user-name"] |

發現 selector 不匹配時，更新 config 而非修改腳本。
發現超時不足時，更新 config 而非修改腳本。
發現 daemon 間隔不合適時，更新 config 而非修改腳本。

### RULE 2.5 — 下載機制分級

| 文件類型 | Kimi 行為 | Agent 策略 |
|----------|----------|-----------|
| .zip, .py, .csv, .json, .env | 直接觸發瀏覽器下載 | expect_download() 捕獲 |
| .md, .txt | 打開預覽面板 → 點擊下載圖標 | 直接點擊優先 + 重試 + 預覽面板備用 |
| sandbox:// URLs | 內部協議，JS 觸發下載 | 全局 download 監聽 + 雙路徑掃描 |

### RULE 2.6 — 去重機制

下載前檢查文件名是否已存在 → 生成唯一文件名（_1, _2, _3...）
下載後計算 SHA256
SHA256 已存在於 downloads.json → 移入 .duplicate/
SHA256 不存在 → 保留在 downloads/
禁止刪除任何檔案。

### RULE 2.7 — 診斷觸發

以下情況觸發診斷：
對話列表提取失敗（側邊欄 DOM 變更）
下載超時（expect_download 未觸發）
預覽面板下載圖標未找到
主人傳入 --diagnose 參數

### RULE 2.8 — 版本行為

Kimi 的 sandbox:// 鏈接不保留歷史版本。同一文件路徑在不同對話中始終指向最新版本。

## LAYER 3 — 腳本接口規範

### F-001 — kimi_login_manager.py

職責：Kimi 平台 SMS 登入與 persistent profile 維護。
所有參數從 `.config/kimi_tracker_config.json` 讀取。

    def validate_login(profile_name: str = None) -> bool
        組合判斷：.chat-info-item OR .user-avatar OR .user-name 任一命中即 True。
        headless 模式執行，無需人工介入。

    def login(profile_name: str = None, visible: bool = None,
              stay_open: int = None, force_login: bool = False) -> bool
        啟動瀏覽器，導航到 platform.base_url。
        循環檢測登入態完成（每 login_check_interval_sec 秒檢查一次）。
        超時 max_login_wait_sec 後關閉。
        若 login.force_reauth 為 true，每次啟動都強制重新登入。

    def diagnose_login_page(profile_name: str = None) -> dict
        導出登入頁面 HTML + 截圖 + 元素統計。

CLI 參數：

    --profile          覆蓋 config 中的 login.profile_name
    --visible          覆蓋 config 中的 login.visible_default
    --stay-open N      覆蓋 config 中的 login.stay_open_default
    --force-login      繞過 validate_login() 直接進入 SMS 流程
    --validate         僅驗證登入態
    --diagnose         診斷模式

### F-002 — kimi_conversation_lister.py

    def extract_conversations(profile_name: str = None,
                              count: int = None, visible: bool = False,
                              diagnose: bool = False) -> list
        從側邊欄提取對話，返回 [{"index", "title", "url", "pinned"}, ...]。
        count 默認使用 config daemon.conversation_count。

    def save_conversation_list(conversations: list, path: str = None) -> str
        保存到 config state.conversations_file。

### F-003 — kimi_downloader.py

    def download_from_url(url: str, profile_name: str = None,
                          visible: bool = False, diagnose: bool = False) -> dict
        訪問單個對話 URL，掃描並下載所有可下載文件。
        下載超時使用 config download.download_timeout_ms。

    def download_from_list(list_path: str = None, profile_name: str = None,
                           visible: bool = False) -> dict
        讀取對話列表（默認 config state.conversations_file），批量處理。

### F-004 — state_manager.py

    def load_state(path: str = None) -> dict
        讀取 downloads.json（默認 config state.state_file）。

    def save_state(state: dict, path: str = None) -> str
        保存狀態到 downloads.json。

    def compute_sha256(file_path: str) -> str
        計算文件 SHA256 哈希值。

    def register_download(state: dict, file_path: str, conversation: str) -> dict
        註冊新下載，檢查重複，決定保留或移入 .duplicate/。
        受 config download.deduplicate 控制。

### F-005 — tracker_daemon.py

    --start              啟動 daemon（後台運行）
    --stop               停止 daemon
    --status             查看 daemon 狀態
    --run-once           單次執行（前台測試）
    --interval N         覆蓋 config daemon.interval_sec

循環流程：

    validate_login() → extract_conversations() → download_from_list() → save_state()

循環間隔由 config daemon.interval_sec 控制（默認 900 秒 = 15 分鐘）。

## LAYER 4 — 輸出與交付約束

### RULE 4.1 — 產出文件清單

必須存在：
SKILL.md, README.md, USAGE.md,
scripts/ 下全部 .py,
.config/kimi_tracker_config.json,
.config/downloads.json（運行時生成）,
.config/conversations.json（運行時生成）,
references/KIMI_TRACKER_USAGE_PLAN.md

不需要：.env, .env.example（本技能不使用環境變數檔案）

### RULE 4.2 — 待確認機制

任何未定參數必須列入 CONFIRMATION.md。
禁止在未經主人確認的情況下假設數值並寫入腳本或 config。

### RULE 4.3 — 版本鎖定

v1.1.0。接口定義視為 LOCK PERMANENT。實現邏輯視為 FLEX EVOLVING。

### RULE 4.4 — 禁止行為

禁止在腳本中內嵌通用瀏覽器操作（必須通過 connector）
禁止在腳本中硬編碼任何可調參數（必須從 config 讀取）
禁止引入 .env 或第二個 .json 配置檔案（單一 config 原則）
禁止刪除任何已下載檔案
禁止修改其他技能的檔案或目錄
禁止在 SKILL.md 中使用 ``` 圍欄，改用 4 空格縮進或表格
