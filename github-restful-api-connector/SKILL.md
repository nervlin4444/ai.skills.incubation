---
title: "GitHub RESTful API Connector - LLM Execution Guide"
name: "github-restful-api-connector"
description: "LLM 執行指令版。連接 GitHub RESTful API，負責將 Skills 資料夾異動檔案自動推送到遠端儲存庫。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T15:36:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  local_path: "{baseDir}/SKILL.md"
  github_path: "github-restful-api-connector/SKILL.md"
---

# github-restful-api-connector — LLM 執行指令

## LAYER 0 — 技能身份與入口約束

你是 github-restful-api-connector 技能的執行代理。
本技能目錄為 github-restful-api-connector，所有產出必須位於此命名空間下。
你不得修改其他技能檔案，不得偏離本技能定義的接口規範。

## LAYER 1 — 核心能力與功能代號

| 功能代號 | 腳本名稱 | 職責 | 狀態 |
|----------|----------|------|------|
| F-001 | github_restful_core.py | 統一 HTTP 客戶端：認證、分頁、速率限制、錯誤重試 | 框架 |
| F-002 | github_project_agent.py | Agent 狀態看板：創建卡片、更新欄位、跨欄移動 | 框架 |
| F-003 | github_project_task.py | 任務排程：讀取分配卡片、執行回報、標記完成 | 框架 |
| F-004 | github_project_session.py | Sessions 追蹤：2026 原生 Agent Sessions API 整合 | 框架 |
| F-005 | github.repo.content.py | 倉庫文件管理：讀取、上傳、更新、刪除、自動創建倉庫 | 框架 |

## LAYER 2 — 執行規則

### RULE 2.1 — 檔案命名強制規範

所有腳本與文件必須使用 xxx.yyy.zzz.ext 格式，以點號（.）作為唯一分隔符。
禁止使用中劃線（-）或下劃線（_）。

正確：github_restful_core.py、github_project_agent.py
錯誤：github_restful_core.py、github-project-agent.py

例外：技能包目錄名稱 github-restful-api-connector 保留連字符，因符合坊間通用命名規範。

### RULE 2.2 — 路徑剛性規則（Path Rigidity Rule）

腳本讀取 .env 或 config 時，只允許讀取以下官方路徑：
- ~/.workbuddy/skills/github-restful-api-connector/.env
- ~/.openclaw/skills/github-restful-api-connector/.env

路徑不存在 → 單行報錯停止。禁止創建文件、禁止猜測、禁止給選項。
例外：GITHUB_REPO 指定的倉庫不存在時，腳本自動創建 Private 倉庫（已獲主人授權）。

### RULE 2.3 — API 版本鎖定

GitHub API 版本標頭必須固定為：
    X-GitHub-Api-Version: 2022-11-28

禁止在腳本中硬編碼其他版本號。若未來需升級，必須經主人確認後統一修改 references/API.SCOPE.md。

### RULE 2.4 — 錯誤處理分級

| 錯誤類型 | 行為 | 回報方式 |
|----------|------|----------|
| 401 Unauthorized | 停止執行，報錯 PAT 無效 | 寫入看板 Failed 欄位 |
| 403 Rate Limited | 指數退避重試（max 3 次） | 日誌記錄，不重寫看板 |
| 404 Not Found | 停止執行，報錯資源不存在 | 寫入看板 Failed 欄位 |
| 422 Validation Failed | 停止執行，報錯請求參數錯誤 | 寫入看板 Failed 欄位 |
| 5xx Server Error | 線性退避重試（max 5 次） | 日誌記錄 |

### RULE 2.5 — 看板狀態機

卡片狀態轉換必須遵循以下有限狀態機：

    Todo → In Progress → Done
    Todo → In Progress → Failed → In Progress → Done
    Todo → Failed（直接失敗，不經 In Progress）

禁止跳過狀態。例如：Todo 不可直接轉 Done，必須經 In Progress。

## LAYER 3 — 腳本接口規範

### F-001 — github_restful_core.py

職責：所有 GitHub API 調用的唯一通道。

必須實現以下函數：

    def graphql_query(query: str, variables: dict = None) -> dict
        統一 GraphQL 調用，處理分頁與速率限制。

    def rest_request(method: str, endpoint: str, payload: dict = None) -> dict
        統一 REST 調用，method 限於 GET / POST / PATCH / DELETE。

    def get_rate_limit_status() -> dict
        返回剩餘配額與重置時間，供上游決策是否繼續調用。

### F-002 — github_project_agent.py

職責：Agent 執行狀態與 GitHub Project 看板雙向同步。

必須實現以下函數：

    def create_card(title: str, body: str, assignee: str = None) -> str
        在 Todo 欄位創建卡片，返回卡片 node_id。

    def move_card(card_id: str, target_status: str) -> bool
        將卡片移至目標欄位，target_status 限於 Todo / In Progress / Done / Failed。

    def update_card_field(card_id: str, field_name: str, value: str) -> bool
        更新卡片自定義欄位（如 Agent 名稱、執行時間、日誌連結）。

    def list_cards_by_status(status: str) -> list
        讀取指定欄位全部卡片，供任務排程使用。

### F-003 — github_project_task.py

職責：任務發派、執行、回報的閉環。

必須實現以下函數：

    def poll_assigned_tasks(agent_name: str) -> list
        輪詢看板上分配給指定 Agent 的 Todo 卡片。

    def mark_task_in_progress(card_id: str) -> bool
        將卡片移至 In Progress，記錄開始時間戳。

    def report_task_completion(card_id: str, result_summary: str, git_commit: str = None) -> bool
        將卡片移至 Done，附加結果摘要與可選 Git commit SHA。

    def report_task_failure(card_id: str, error_log: str, retryable: bool = False) -> bool
        將卡片移至 Failed，附加錯誤日誌。若 retryable=True，標記待重試。

### F-004 — github_project_session.py

職責：GitHub 2026 原生 Agent Sessions 整合。

必須實現以下函數：

    def track_session_start(issue_number: int, agent_name: str) -> str
        在指定 Issue 上啟動 Agent Session，返回 session_id。

    def track_session_update(session_id: str, status: str, log_url: str = None) -> bool
        更新 Session 狀態，status 限於 queued / working / completed / failed。

    def track_session_end(session_id: str, final_status: str, summary: str) -> bool
        結束 Session，寫入最終狀態與摘要。

    def get_session_logs(session_id: str) -> str
        返回 Session 日誌連結或原始日誌內容。


### F-005 — github.repo.content.py

職責：倉庫文件內容管理與自動倉庫創建。

必須實現以下函數：

    def read_file(owner: str, repo: str, path: str, branch: str = "main") -> dict
        讀取倉庫指定路徑文件，返回含 decoded_content（已 base64 解碼）。

    def upload_file(owner: str, repo: str, path: str, local_path: str, message: str, branch: str = "main") -> dict
        上傳本地文件到倉庫。若文件已存在，自動獲取 sha 並覆蓋更新。

    def update_file(owner: str, repo: str, path: str, content: str, message: str, branch: str = "main") -> dict
        直接以字符串內容更新文件。文件必須已存在。

    def delete_file(owner: str, repo: str, path: str, message: str, branch: str = "main") -> dict
        刪除倉庫指定文件。

    def list_directory(owner: str, repo: str, path: str = "", branch: str = "main") -> list
        列出目錄內容，返回文件與子目錄列表。

    def create_repo(owner: str, repo_name: str, description: str = "", private: bool = True) -> dict
        自動創建倉庫。支持個人用戶與組織。若已存在則返回現有倉庫。

    def ensure_repo_exists(owner: str, repo_name: str = None, description: str = "") -> str
        確保倉庫存在。若未指定名稱，使用環境變數或默認名稱自動創建。
        返回實際使用的倉庫名稱。

### RULE 2.6 — 倉庫自動創建約束

GITHUB_REPO 為可選欄位。若未指定：
- 腳本調用 ensure_repo_exists() 自動創建 Private 倉庫
- 默認倉庫名稱為 "github-restful-api-connector"
- 創建前檢查是否已存在，避免重複創建報 422
- 組織倉庫使用 /orgs/{owner}/repos，個人使用 /user/repos

### F-005 — github_repo_sync.py

職責：批量將本地目錄同步到 GitHub 倉庫，具備衝突檢測與自動創建能力。

必須實現以下函數：

    def create_repo_if_not_exists(owner: str, repo_name: str, private: bool = True) -> dict
        若倉庫不存在，自動創建 Private 倉庫。返回倉庫信息。

    def check_conflict(owner: str, repo: str, local_path: Path, repo_path: str) -> dict
        檢查本地文件與倉庫文件是否存在衝突。
        返回 dict 含 action（skip / upload / warn）、reason、repo_date、local_date。
        比對邏輯：先比 Git blob sha，sha 不同再比最後提交時間與本地 mtime。

    def sync_directory(owner: str, repo: str, local_dir: str, repo_base_path: str = "", dry_run: bool = False, force: bool = False) -> list
        批量同步本地目錄到倉庫。遍歷全部文件，排除 .git / __pycache__ / .env 等。
        對每個文件執行 check_conflict，根據結果決定上傳/跳過/警告。
        返回操作報告列表。

    def upload_file(owner: str, repo: str, local_path: Path, repo_path: str, message: str) -> dict
        上傳單個文件到倉庫。若文件已存在，使用 sha 參數覆蓋。

### F-005 CLI 參數規範

    --repo-name      必填。目標倉庫名稱，自定義，由用戶提供。
    --local-dir      必填。本地目錄路徑。
    --repo-base-path 可選。倉庫內基礎路徑（默認根目錄）。
    --dry-run        可選。預覽模式，不實際上傳。
    --force          可選。強制覆蓋，忽略倉庫文件較新的警告。
    (auto-detected, no flag needed)    可選。倉庫不存在時自動創建 Private 倉庫。

### F-006 — github_repo_verify.py

職責：雙向驗證本地目錄與 GitHub 倉庫內容是否一致。
適用場景：腳本更新後驗證、初次部署後確認、定期一致性檢查。

必須實現以下函數：

    def verify_local_to_repo(owner: str, repo: str, local_dir: str, repo_base_path: str = "") -> dict
        驗證方向 A：本地 → 倉庫。
        檢查本地所有檔案是否都已正確上傳到倉庫，且內容一致。
        返回 {verified: [], missing: [], mismatch: []}。

    def verify_repo_to_local(owner: str, repo: str, local_dir: str, repo_base_path: str = "") -> dict
        驗證方向 B：倉庫 → 本地。
        檢查倉庫中的檔案是否都在本地存在，且內容一致。
        返回 {verified: [], missing: [], mismatch: [], extra: []}。

    def run_full_verification(owner: str, repo: str, local_dir: str, repo_base_path: str = "") -> dict
        執行雙向完整驗證。
        返回 {local_to_repo: {}, repo_to_local: {}, summary: {}}。

### F-006 CLI 參數規範

    --repo-name        必填。目標倉庫名稱。
    --local-dir        必填。本地目錄路徑。
    --repo-base-path   可選。倉庫內基礎路徑。
    --direction        可選。both（默認）/ local-to-repo / repo-to-local。
    --json             可選。輸出原始 JSON 報告。

### F-007 — github_repo_pull.py

職責：從 GitHub 倉庫指定目錄下載全部檔案並同步到本地。
適用場景：從大貨倉拉取技能更新、初始化本地技能目錄、恢復遺失檔案。

核心規則：
- 本地檔案不存在 → DOWNLOAD
- 本地檔案存在 → WARN（報告本地較新，不覆蓋）
- 使用 `--force` 可強制覆蓋本地檔案

必須實現以下函數：

    def list_repo_tree(owner: str, repo: str, repo_path: str = "") -> list
        遞歸列出倉庫指定路徑下的所有檔案。
        返回 [(path, sha, download_url), ...]。

    def download_file(owner: str, repo: str, repo_path: str, local_path: Path) -> bool
        下載單個檔案從倉庫到本地。
        使用 GitHub Contents API 獲取 base64 內容。

    def sync_repo_to_local(owner: str, repo: str, repo_base_path: str, local_dir: str,
                           dry_run: bool = False, force: bool = False) -> list
        將倉庫目錄同步到本地。
        若本地較新 → WARN（不覆蓋）。
        若倉庫較新或本地不存在 → DOWNLOAD。
        返回操作報告列表。

### F-007 CLI 參數規範

    --repo-name        必填。目標倉庫名稱。
    --repo-path        可選。倉庫內路徑（如 `github-restful-api-connector`）。
    --local-dir        必填。本地目標目錄。
    --dry-run          可選。預覽不下載。
    --force            可選。強制覆蓋本地較新檔案。

## LAYER 4 — 輸出與交付約束

### RULE 4.1 — 產出文件清單

每次執行本技能，必須檢查以下文件是否存在於 github-restful-api-connector 目錄：
- readme/SKILL.md（人類版，僅主人可修改）
- SKILL.md（本文件，僅主人可修改）
- scripts/ 下全部 .py 腳本（含 F-006 verify）（含 F-005 github.repo.content.py）
- references/API.SCOPE.md
- references/MAPPING.md
- .env.template
- USAGE.md
- CONFIRMATION.md

### RULE 4.2 — 待確認機制

任何未定參數（如 GITHUB_OWNER、PROJECT_NUMBER、PAT 類型）必須列入 CONFIRMATION.md。
禁止在未經主人確認的情況下假設數值並寫入腳本。

### RULE 4.3 — 版本鎖定

本技能版本 v0.1.0 為框架階段。所有接口定義（函數簽名、參數名稱、返回值結構）視為 LOCK PERMANENT。
實際實現邏輯視為 FLEX EVOLVING，可在主人確認後迭代。

### RULE 4.4 — 禁止行為

- 禁止在腳本中內嵌 GitHub Token
- 禁止在未經主人授權時創建或刪除 GitHub Project
- 禁止修改其他技能的檔案或目錄
- 禁止在 SKILL.md 中使用 ``` 圍欄，改用 4 空格縮進或表格
