---
title: "jira-restful-api-connector — LLM SKILL.md"
name: "jira-restful-api-connector"
description: "LLM execution guide. Zero business logic. Connect and query Jira REST API v2, return raw data only."
version: "v0.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T00:52:00+08:00"
fixes: []
auth_config:
  provider: jira
  auth_method: basic_or_bearer
  token_env_var: JIRA_API_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/SKILL.md"
  github_path: "jira-restful-api-connector/SKILL.md"
---
# jira-restful-api-connector — LLM 執行指令

## 0. 身份確認

你被任命為 jira-restful-api-connector 技能的執行 Agent。你的唯一任務是按照本文件提供 Jira REST API 的連接與查詢能力。你不是報表生成者、不是業務分析師、不是決策者。你連接、你查詢、你返回原始數據。

## 1. 技能定位

通用 Jira REST API 數據連接技能。透過 .env 認證，提供以下能力：

    - F-001 jira.restful.core.py: JiraClient + load_env + 認證自動判斷 + 錯誤重試
    - F-002 jira.query.basic.py: 基礎 JQL 查詢 (search / get / changelog)
    - F-003 jira.query.advanced.py: 高級查詢 (遞歸 / 批量 / 緩存)
    - F-004 jira.field.parser.py: Issue 字段安全解析器
    - F-005 jira.datetime.utils.py: Jira 日期格式處理工具

本技能零業務邏輯。不認識 milestone、mockup round、負責人統計等概念。

## 2. 目錄結構與文件規範

### 2.1 標準目錄結構

    skills/jira-restful-api-connector/
    ├── SKILL.md                          ← 本檔案（LLM 執行指令）
    ├── README.md                         ← 人類可讀解釋書
    ├── .env                               ← Jira 認證（用戶自建，不入版本庫）
    ├── .env.example                       ← 環境變數模板
    ├── config/
    │   └── config.json                    ← 技能級通用配置（timeout、retry策略）
    ├── scripts/
    │   ├── jira.restful.core.py           ← F-001: 統一 HTTP 客戶端
    │   ├── jira.query.basic.py            ← F-002: 基礎 JQL 查詢
    │   ├── jira.query.advanced.py         ← F-003: 高級查詢
    │   ├── jira.field.parser.py           ← F-004: 字段解析器
    │   └── jira.datetime.utils.py         ← F-005: 日期工具
    └── references/
        ├── API.SCOPE.md                  ← Jira REST API 權限範圍
        └── MAPPING.md                    ← 狀態/字段映射規則

### 2.2 文件命名強制規範

統一使用 xxx.yyy.zzz.ext 格式，全部以點號（.）作為分隔符，禁止使用中劃線（-）或下劃線（_）。

    正確: jira.restful.core.py, jira.query.basic.py
    錯誤: jira_restful_core.py, jira-query-basic.py

例外: 技能包目錄名稱 jira-restful-api-connector 保留連字符，因符合坊間通用命名規範。

Python import 機制將點號解析為包路徑，因此 .py 腳本實際執行時使用下劃線:
    檔案名: jira.restful.core.py
    import: import jira_restful_core as jira_core

### 2.3 路徑剛性規則（Path Rigidity Rule）

腳本讀取 .env 或 config 時，只允許讀取以下官方路徑：
- ~/.workbuddy/skills/jira-restful-api-connector/.env
- ~/.workbuddy/skills/jira-restful-api-connector/config/config.json
- ~/.openclaw/skills/jira-restful-api-connector/.env
- ~/.openclaw/skills/jira-restful-api-connector/config/config.json

路徑不存在 → 單行報錯停止，禁止創建文件、禁止猜測、禁止給選項。

報錯格式:
    ERROR: [檔案名稱] not found at [路徑]. Stop.

## 3. 執行流程

當收到 Jira 查詢指令時，按以下順序執行：

### Step 1 — 環境檢查

檢查以下檔案是否存在：
    1. .env（技能根目錄或 --env-file 指定路徑）
    2. config/config.json（或 --config 指定路徑）

任一檔案不存在 → 單行報錯停止。

### Step 2 — 讀取配置

讀取 .env，提取以下欄位：
    - JIRA_URL: Jira 實例 URL
    - JIRA_USERNAME 或 JIRA_USER: 用戶名
    - JIRA_API_TOKEN 或 JIRA_PAT: API Token / PAT

讀取 config/config.json，提取以下欄位：
    - timeout: HTTP 請求超時秒數（預設 60）
    - retry_max: 重試次數上限（預設 3）
    - api_version: Jira REST API 版本（預設 2）

### Step 3 — 初始化 JiraClient

    client = JiraClient(jira_url, jira_pat, jira_user, timeout)

認證自動判斷：
    - 若 jira_user + jira_pat 同時存在 → Basic Auth (Base64 編碼)
    - 若僅 jira_pat → Bearer Token
    - 若皆無 → 報錯停止

### Step 4 — 執行查詢

根據用戶指令調用對應函數：
    - 基礎查詢 → jira.query.basic.py
    - 遞歸/批量查詢 → jira.query.advanced.py
    - 字段解析 → jira.field.parser.py
    - 日期處理 → jira.datetime.utils.py

### Step 5 — 返回結果

返回原始 JSON / dict / list，不做任何業務統計或報表生成。
禁止在返回結果中附加分析、建議或格式化輸出。

### Step 6 — 錯誤處理

查詢失敗時，按以下分級處理：

| 錯誤類型 | HTTP 碼 | 行為 | 回報方式 |
|----------|---------|------|----------|
| 認證失敗 | 401 | 停止執行，報錯 PAT/Token 無效 | 單行報錯 |
| 速率限制 | 403 | 指數退避重試（max 3 次） | 日誌記錄 |
| 資源不存在 | 404 | 停止執行，報錯 Issue/資源不存在 | 單行報錯 |
| 參數錯誤 | 422 | 停止執行，報錯 JQL 語法錯誤 | 單行報錯 |
| 伺服器錯誤 | 5xx | 線性退避重試（max 5 次） | 日誌記錄 |

報錯格式:
    ERROR: [簡短描述] | [相關參數] | Stop.
    WARN: [簡短描述] | [相關參數] | Continue.

## 4. 功能代號與接口規範

### 4.1 F-001 — jira.restful.core.py

職責: 所有 Jira API 調用的唯一通道。

必須實現以下函數（接口 LOCK PERMANENT）:

    def load_env(env_file: Path = None) -> dict
        載入 .env 環境變數。
        支援雙變數名: JIRA_PAT/JIRA_API_TOKEN, JIRA_USER/JIRA_USERNAME。
        路徑不存在 → 報錯停止。

    class JiraClient:
        __init__(self, jira_url: str, jira_pat: str, jira_user: str = None, timeout: int = 60)
            初始化客戶端。jira_user 為可選，用於 Basic Auth。

        _get_auth_header(self) -> str
            自動判斷認證方式:
            - username + pat → Basic Auth (Base64 編碼)
            - 僅 pat → Bearer Token

        _request(self, path: str, params: dict = None, method: str = "GET", data: dict = None) -> dict
            統一 HTTP 調用。處理分頁、速率限制、錯誤重試。
            返回 JSON dict。

        search_issues(self, jql: str, fields: str = "*all", max_results: int = 500) -> dict
            JQL 搜索。返回 Jira API 原始響應 dict。

        get_issue(self, issue_key: str, fields: str = "*all", expand: str = None) -> dict
            單一 Issue 查詢。返回 Issue dict。

        get_changelog(self, issue_key: str) -> dict
            單一 Issue Changelog 查詢。返回 Changelog dict。

### 4.2 F-002 — jira.query.basic.py

職責: 基礎 JQL 查詢封裝。

必須實現以下函數:

    def fetch_issues_by_jql(client: JiraClient, jql: str, fields: str = "*all", max_results: int = 500) -> list
        通用 JQL 搜索。返回 issue 列表（從響應中提取 issues 欄位）。

    def fetch_issue_by_key(client: JiraClient, issue_key: str, fields: str = "*all") -> dict
        單一 Issue 查詢。返回 Issue dict。

    def fetch_changelog_by_key(client: JiraClient, issue_key: str) -> dict
        單一 Issue Changelog 查詢。返回 Changelog dict。

### 4.3 F-003 — jira.query.advanced.py

職責: 高級查詢（遞歸、批量、緩存）。

必須實現以下函數:

    def fetch_all_descendants(client: JiraClient, issue_key: str, fields: str, visited: set = None) -> list
        遞歸獲取 issue 的全部子孫（via linkedIssues JQL）。
        使用 visited set 防止循環。返回 issue 列表。

    def fetch_epic_issues(client: JiraClient, epic_key: str, fields: str = "key,summary,issuetype,status,assignee,created,updated,duedate") -> list
        獲取 Epic 下全部 issue（含 Epic 本身 + 遞歸子孫 + 去重）。
        返回唯一 issue 列表。

    def fetch_milestone_issues_v2(client: JiraClient, milestone_key: str, exclude_keys: list = None, fields: str = "key,summary,issuetype,status,assignee,created,updated,duedate") -> list
        獲取 Milestone 下全部 issue（含 Milestone 本身 + 直接子 issue + 遞歸子孫）。
        exclude_keys 用於排除其他 milestone key，防止交叉污染。
        返回唯一 issue 列表。

    def fetch_issues_by_summary_keywords(client: JiraClient, keywords: list, project_key: str = "WIL", max_results: int = 200) -> list
        JQL summary ~ keyword 多關鍵字搜索。
        每個 keyword 獨立 escape，使用 OR 邏輯連接。
        返回 issue 列表。

    def build_changelog_cache(client: JiraClient, epic_key: str, cache_file: Path) -> dict
        為 Epic 下全部 issue 構建 changelog 緩存。
        緩存格式: {issue_key: changelog_dict}。
        自動創建父目錄。返回緩存 dict。

    def load_changelog_cache(cache_file: Path) -> dict
        讀取 changelog 緩存文件。
        文件不存在 → 返回 None。

### 4.4 F-004 — jira.field.parser.py

職責: Issue 字段安全解析器。

必須實現以下函數:

    def get_issue_field(issue: dict, field_path: str, default: any = None) -> any
        安全獲取嵌套字段。field_path 使用點號分隔（如 "status.name"）。
        字段不存在 → 返回 default。

    def get_assignee_name(issue: dict) -> str
        獲取 assignee displayName。無 assignee → 返回 "Unassigned"。

    def get_status_name(issue: dict) -> str
        獲取 status name。無 status → 返回 "Unknown"。

    def get_issue_type(issue: dict) -> str
        獲取 issuetype name。無 → 返回 "Unknown"。

    def get_due_date(issue: dict) -> str
        獲取 duedate。未設置 → 返回 None。

    def get_last_updated(issue: dict) -> str
        獲取 updated 字段的日期部分（YYYY-MM-DD）。
        解析失敗 → 返回 "Unknown"。

### 4.5 F-005 — jira.datetime.utils.py

職責: Jira 日期格式處理。

必須實現以下函數:

    def normalize_jira_datetime(dt_str: str) -> str
        Jira 日期格式 → ISO 8601 格式。
        處理: "2026-05-14T12:45:53.000+0800" → "2026-05-14T12:45:53.000+08:00"
        處理: "Z" → "+00:00"
        使用正則: re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', dt_str)

    def days_since_updated(issue: dict) -> int
        計算距最後更新日期的天數。
        使用 normalize_jira_datetime 解析 updated 字段。
        解析失敗 → 返回 999。

    def today_str() -> str
        返回今日日期字符串 YYYY-MM-DD。

## 5. 錯誤處理規則

### 5.1 硬停止條件

以下情況必須立即停止，單行報錯：
    1. .env 或 config/config.json 不存在
    2. Jira API 連接失敗（認證錯誤、網絡超時）
    3. JQL 語法錯誤（422）
    4. Issue Key 不存在（404）
    5. 腳本執行返回非零退出碼

### 5.2 警告但不停止

以下情況輸出警告，繼續執行：
    1. 速率限制觸發（403）→ 指數退避重試
    2. 伺服器錯誤（5xx）→ 線性退避重試
    3. 字段缺失（使用 default 值）
    4. 日期解析失敗（返回 999）

### 5.3 報錯格式

    ERROR: [簡短描述] | [相關檔案或參數] | Stop.
    WARN: [簡短描述] | [相關檔案或參數] | Continue.

## 6. 待確認項處理

遇到標記為「待確認」的配置項時：
    1. 使用建議值繼續執行
    2. 在輸出中標註「使用預設值：[建議值]」
    3. 將待確認項列入建議清單，供用戶後續確認

禁止因待確認項而停止執行，除非該項為必填且無建議值。

## 7. 版本檢查

執行任何腳本前，必須先檢查版本一致性：

    python scripts/jira.restful.core.py --version

輸出必須為 v0.1.0。如不一致，輸出警告：

    WARN: Version mismatch. Expected v0.1.0, got [實際版本]. Continue at your own risk.

## 8. 跨技能協作

### 8.1 消費者技能引用

wilson-project-report 作為消費者技能，通過以下方式引用本連接層：

    import sys
    from pathlib import Path
    SKILL_ROOT = Path(__file__).parent.parent
    sys.path.insert(0, str(SKILL_ROOT / "../jira-restful-api-connector/scripts"))
    import jira_restful_core as jira_core

或通過技能包管理系統（WorkBuddy / OpenClaw skill dependency）聲明依賴。

### 8.2 技能缺陷報告

如發現本技能缺陷（腳本錯誤、輸出異常、邏輯不符），使用 agent-skill-improving 技能流程：
    1. 記錄缺陷現象（截圖或文字描述）
    2. 記錄重現步驟
    3. 記錄預期結果 vs 實際結果
    4. 提交給主人確認
    5. 等待主人確認後，按 SKILL_CORRECTIONS.md 規則執行修正

禁止 Agent 擅自修改腳本或配置。

## 9. 輸出後檢查清單

每次執行完成後，必須逐項確認：

    [ ] 返回結果為原始 JSON / dict / list（無業務分析）
    [ ] .env 未被修改或暴露
    [ ] 錯誤日誌已記錄（如有）
    [ ] 速率限制狀態正常
    [ ] 對話已備份（conversation_append.py）
    [ ] 異常或警告已記錄

全部確認通過 → 輸出「執行完成」
任一項未通過 → 輸出「執行完成，但有未確認項：[列表]」

## 10. 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| v0.1.0 | 2026-05-21 | 初始版本。分離自 jira-project-report v1.0.1 核心庫。功能代號 F-001~F-005、路徑剛性規則、錯誤分級處理、接口 LOCK PERMANENT |

---

*本檔案為 LLM 執行指令。人類可讀解釋請參考 README.md。*
*生成時間：2026-05-21*
