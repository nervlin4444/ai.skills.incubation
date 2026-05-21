---
title: "wilson-project-report — LLM SKILL.md"
description: "LLM 執行指令檔案。當 Agent 被任命執行 wilson-project-report 技能時，必須嚴格按照本文件步驟執行，禁止偏離、禁止猜測、禁止反手修改規則。"
version: "v1.0.0"
date: "2026-05-21"
author: "Kevin Lin / Agent Swarm Architecture"
skill_bundle: "wilson-project-report"
---

# wilson-project-report — LLM 執行指令

## 0. 身份確認

你被任命為 wilson-project-report 技能的執行 Agent。你的唯一任務是按照本文件生成 WIL 項目 HTML 報表。你不是數據連接者、不是業務分析師、不是決策者。你讀取數據、你生成報表、你保存輸出。

## 1. 技能定位

WIL 項目專屬報表生成技能。透過 jira-restful-api-connector 獲取數據，生成以下報表：

    - wilson.milestone.sprint.report.assignee.py: 里程碑衝刺報表-負責人
    - wilson.milestone.sprint.report.changelog.py: 里程碑衝刺報表-經手人
    - wilson.mockexam.sprint.report.assignee.py: 模擬考衝刺報表-負責人

本技能不處理 Jira API 連接。所有數據查詢必須通過 jira-restful-api-connector 完成。

## 2. 目錄結構與文件規範

### 2.1 標準目錄結構

    skills/wilson-project-report/
    ├── SKILL.md                          ← 本檔案（LLM 執行指令）
    ├── README.md                         ← 人類可讀解釋書
    ├── config/
    │   └── config.json                    ← 通用配置（owner, output_dir, history_file, cache_dir）
    ├── scripts/
    │   ├── wilson.milestone.sprint.report.assignee.py
    │   ├── wilson.milestone.sprint.report.changelog.py
    │   └── wilson.mockexam.sprint.report.assignee.py
    ├── assets/
    │   ├── history.json                   ← 歷史趨勢數據（必須入版本庫）
    │   ├── reports/                       ← HTML 報表輸出
    │   └── cache/                         ← Changelog 緩存
    └── references/

### 2.2 文件命名強制規範

統一使用 xxx.yyy.zzz.ext 格式，全部以點號（.）作為分隔符，禁止使用中劃線（-）或下劃線（_）。

    正確: wilson.milestone.sprint.report.assignee.py
    錯誤: wilson_milestone_sprint_report_assignee.py

例外: Python import 機制將點號解析為包路徑，因此 .py 腳本實際執行時使用下劃線:
    檔案名: wilson.milestone.sprint.report.assignee.py
    import: import wilson_milestone_sprint_report_assignee

### 2.3 路徑剛性規則（Path Rigidity Rule）

腳本讀取 config 時，只允許讀取以下官方路徑：
- ~/.workbuddy/skills/wilson-project-report/config/config.json
- ~/.openclaw/skills/wilson-project-report/config/config.json

路徑不存在 → 單行報錯停止，禁止創建文件、禁止猜測、禁止給選項。

報錯格式:
    ERROR: [檔案名稱] not found at [路徑]. Stop.

## 3. 執行流程

當收到生成報表指令時，按以下順序執行：

### Step 1 — 環境檢查

檢查以下檔案是否存在：
    1. jira-restful-api-connector 的 .env（技能根目錄或 --env-file 指定路徑）
    2. config/config.json（或 --config 指定路徑）

任一檔案不存在 → 單行報錯停止。

### Step 2 — 初始化數據連接

通過 jira-restful-api-connector 初始化 JiraClient：

    import sys
    from pathlib import Path
    SKILL_ROOT = Path(__file__).parent.parent
    sys.path.insert(0, str(SKILL_ROOT / "../jira-restful-api-connector/scripts"))
    import jira_restful_core as jira_core

    env = jira_core.load_env()
    config = jira_core.load_config()
    client = jira_core.JiraClient(env["jira_url"], env["jira_pat"], env["jira_user"])

### Step 3 — 讀取報表配置

讀取 config/config.json，提取以下欄位：
    - owner: 專案負責人名稱
    - output_dir: 報表輸出路徑
    - history_file: 歷史數據路徑
    - cache_dir: 緩存目錄路徑

讀取報表腳本頂層常量：
    - EPIC_KEY: 主 Epic Issue Key
    - MILESTONES: 里程碑陣列
    - TITLE_PREFIX: 報表標題前綴

### Step 4 — 獲取數據

通過 jira-restful-api-connector 執行查詢：
    - 里程碑報表 → jira.query.advanced.fetch_milestone_issues_v2()
    - 模擬考報表 → jira.query.advanced.fetch_issues_by_summary_keywords()

### Step 5 — 生成 HTML

按報表類型調用對應生成函數：
    - 負責人報表 → 統計 assignee 分佈
    - 經手人報表 → 統計 changelog 參與者
    - 模擬考報表 → 按 Round/Subject 分組統計

### Step 6 — 保存輸出

保存 HTML 報表至 assets/reports/，更新 assets/history.json。

### Step 7 — 驗證

驗證以下內容：
    1. HTML 檔案存在且大小 > 0
    2. HTML 標題正確
    3. history.json 已更新

## 4. 報表生成邏輯

### 4.1 里程碑衝刺報表-負責人

數據來源: jira-restful-api-connector, Issue.fields.assignee

生成邏輯:
    1. 查詢 EPIC_KEY 下全部 Issue
    2. 按 MILESTONES 陣列分組統計
    3. 每個 milestone 統計: total / completed / in_progress / rate
    4. 按 assignee 分組統計每個 milestone 的人員分佈
    5. 與 history.json 中前一日數據比較，計算變化趨勢
    6. 標記風險 Issue（退回、進行中超過 14 天未更新）
    7. 輸出 HTML

HTML 必須包含章節:
    章節 1 — 標題區（專案名稱、日期、負責人、Jira URL）
    章節 2 — 項目整體進度（統計卡片 + 狀態分佈表 + 進度條）
    章節 3~5 — 三個里程碑獨立區塊（變化比較 / 退回 / QC / 進行中超3天 / Activity Stream）
    章節 6 — 風險問題（退回 / 長期未更新）
    章節 7 — 最新資訊（進行中任務排序 + 完成時間評估）
    章節 8 — 建議行動（立即 / 短期 / 中期）

### 4.2 里程碑衝刺報表-經手人

數據來源: jira-restful-api-connector, Issue.changelog.histories（需緩存）

生成邏輯:
    1. 讀取 Changelog 緩存檔案
    2. 從 Changelog 中提取所有參與過操作的人員
    3. 按人員統計參與的 Issue 數量與狀態分佈
    4. 其餘邏輯與負責人報表相同

### 4.3 模擬考衝刺報表-負責人

數據來源: jira-restful-api-connector + JQL summary ~ keyword 搜索

生成邏輯:
    1. 按 MOCKUP_ROUNDS 配置執行 JQL 搜索
    2. 每個 Subject 下: Issue Key / 標題 / 類型 / 狀態 / 負責人
    3. 每個 Round 內按負責人統計: 總計 / Done / Other / 完成百分比 %
    4. 跨 Round 彙總: 整體完成率、風險 Subject（完成率 < 50%）
    5. 輸出 HTML

MOCKUP_ROUNDS 結構（LOCK PERMANENT，禁止修改）:

    MOCKUP_ROUNDS = {
        "2nd Round Mockup (3 June 2026)": {
            "Void Sales Flow": ["Void Sales", "Void Memo", "Void單", "廢單"],
            "Void And Copy Flow": ["Void & Copy", "Void And Copy"],
            ...
        },
        "3rd Round Mockup (25 June 2026)": {
            ...
        },
        "4th Round Mockup (15 July 2026)": {
            ...
        }
    }

## 5. 錯誤處理規則

### 5.1 硬停止條件

以下情況必須立即停止，單行報錯：
    1. jira-restful-api-connector 的 .env 不存在
    2. config/config.json 不存在
    3. 數據查詢失敗（connector 報錯）
    4. 生成後 HTML 檔案不存在或為空

### 5.2 警告但不停止

以下情況輸出警告，繼續執行：
    1. Changelog 緩存超過 24 小時未更新
    2. 某個 milestone 下 Issue 數量為 0
    3. 某個 Subject 下未匹配到任何 Issue
    4. 歷史數據檔中前一日記錄缺失

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

    python scripts/wilson.milestone.sprint.report.assignee.py --version

輸出必須為 v1.0.0。如不一致，輸出警告：

    WARN: Version mismatch. Expected v1.0.0, got [實際版本]. Continue at your own risk.

## 8. 跨技能協作

### 8.1 數據連接層引用

所有 Jira API 調用必須通過 jira-restful-api-connector：

    import jira_restful_core as jira_core
    import jira_query_advanced as jira_adv
    import jira_field_parser as jira_fp

禁止在本技能中直接調用 urllib 或 requests。

### 8.2 技能缺陷報告

如發現本技能缺陷，使用 agent-skill-improving 技能流程：
    1. 記錄缺陷現象
    2. 記錄重現步驟
    3. 記錄預期結果 vs 實際結果
    4. 提交給主人確認
    5. 等待主人確認後修正

禁止 Agent 擅自修改腳本或配置。

## 9. 輸出後檢查清單

每次執行完成後，必須逐項確認：

    [ ] HTML 報表檔案存在且非空
    [ ] HTML 報表標題正確
    [ ] history.json 已更新至今日
    [ ] .env 未被修改或暴露
    [ ] 報表中的 Jira 連結可點擊
    [ ] 對話已備份（conversation_append.py）
    [ ] 異常或警告已記錄

全部確認通過 → 輸出「執行完成」
任一項未通過 → 輸出「執行完成，但有未確認項：[列表]」

## 10. 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| v1.0.0 | 2026-05-21 | 初始版本。從 jira-project-report v1.0.1 重構，分離數據連接層至 jira-restful-api-connector，報表級常量內建於各 report.*.py |

---

*本檔案為 LLM 執行指令。人類可讀解釋請參考 README.md。*
*生成時間：2026-05-21*
