---
title: "wilson-project-report — README.md"
description: "人類可讀版技能解釋書。WIL 項目專屬報表生成技能，依賴 jira-restful-api-connector 提供數據連接。"
version: "v1.0.0"
date: "2026-05-21"
author: "Kevin Lin / Agent Swarm Architecture"
skill_bundle: "wilson-project-report"
---

# wilson-project-report — 技能解釋書

## 1. 技能定位

WIL 項目專屬報表生成技能。透過 jira-restful-api-connector 獲取 Jira 數據，生成三份 HTML 報表：

| 報表名稱 | 數據來源 | 視角 | 輸出檔案 |
|----------|----------|------|----------|
| 3個里程碑衝刺進度報表-負責人 | Issue.fields.assignee | 責任歸屬 | milestone.sprint.report.assignee.YYYY-MM-DD.html |
| 3個里程碑衝刺進度報表-經手人 | Issue.changelog.histories | 實際參與 | milestone.sprint.report.changelog.YYYY-MM-DD.html |
| 3個模擬考衝刺進度報表-負責人 | Issue.fields.assignee + JQL 關鍵字 | 責任歸屬 + 模擬考分類 | mockexam.sprint.report.assignee.YYYY-MM-DD.html |

## 2. 目錄結構

    skills/wilson-project-report/
    ├── SKILL.md                          ← LLM 執行指令
    ├── README.md                         ← 本檔案（人類解釋書）
    ├── config/
    │   └── config.json                    ← 通用配置（owner, output_dir, history_file, cache_dir）
    ├── scripts/
    │   ├── wilson.milestone.sprint.report.assignee.py
    │   ├── wilson.milestone.sprint.report.changelog.py
    │   └── wilson.mockexam.sprint.report.assignee.py
    ├── assets/
    │   ├── history.json                   ← 歷史趨勢數據（自動維護，必須入版本庫）
    │   ├── reports/                       ← HTML 報表輸出
    │   │   ├── milestone.sprint.report.assignee.YYYY-MM-DD.html
    │   │   ├── milestone.sprint.report.changelog.YYYY-MM-DD.html
    │   │   └── mockexam.sprint.report.assignee.YYYY-MM-DD.html
    │   └── cache/                         ← Changelog 緩存
    │       └── WIL-10.changelog.cache.json
    └── references/

## 3. 配置檔格式

### 3.1 config/config.json

    {
      "owner": "EricNg",
      "output_dir": "assets/reports/",
      "history_file": "assets/history.json",
      "cache_dir": "assets/cache/"
    }

### 3.2 報表級常量（各 report.*.py 頂層）

**wilson.milestone.sprint.report.assignee.py:**

    EPIC_KEY = "WIL-10"
    MILESTONES = [
        {"key": "WIL-10", "name": "2. Sales Transaction"},
        {"key": "WIL-11", "name": "3. Deposit Transaction"},
        {"key": "WIL-12", "name": "4. POS Operation"},
    ]
    TITLE_PREFIX = "3個里程碑衝刺進度報表"
    STATUS_MAP = {
        "Done": "done", "In Progress": "in_progress", "Ready for QC": "ready_for_qc",
        "To Do": "to_do", "Return": "returned", "On Hold": "on_hold",
        "已完成": "done", "進行中": "in_progress", "待測試": "ready_for_qc",
        "待開始": "to_do", "退回": "returned", "暫停": "on_hold",
    }
    STAGNANT_THRESHOLD = 3
    RISK_DAYS = 14

**wilson.mockexam.sprint.report.assignee.py:**

    EPIC_KEY = "WIL-10"
    TITLE_PREFIX = "3個模擬考衝刺進度報表"
    MOCKUP_ROUNDS = { ... }  ← 見 SKILL.md 第 4.3 節
    ROUND_DATES = {
        "2nd Round Mockup (3 June 2026)": "2026-06-03",
        "3rd Round Mockup (25 June 2026)": "2026-06-25",
        "4th Round Mockup (15 July 2026)": "2026-07-15",
    }

## 4. 報表風格規範

### 4.1 里程碑衝刺報表 HTML 結構

    章節 1 — 標題區：專案名稱、報告日期、專案負責人、Jira URL
    章節 2 — 項目整體進度：統計卡片 + 狀態分佈表 + 進度條
    章節 3~5 — 三個里程碑獨立區塊
    章節 6 — 風險問題（退回 / 長期未更新）
    章節 7 — 最新資訊（進行中任務排序）
    章節 8 — 建議行動（立即 / 短期 / 中期）

### 4.2 模擬考衝刺報表 HTML 結構

    章節 1 — 標題區
    章節 2 — 模擬考整體進度 + Round 分組概覽
    章節 3~5 — 三個 Round 獨立區塊（Subject 分組 + 負責人統計）
    章節 6 — 跨 Round 彙總 + 風險 Subject 標註
    章節 7 — 建議行動（Mockup 日期倒數）

## 5. 備份策略

| 資產類型 | 檔案位置 | 備份方式 | 保留策略 |
|----------|----------|----------|----------|
| HTML 報表 | assets/reports/*.html | 每日新生成 | 建議保留 90 日 |
| 歷史數據 | assets/history.json | 每日增量追加 | 必須入版本庫 |
| Changelog 緩存 | assets/cache/*.json | 可隨時重建 | 無需備份 |

## 6. 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| v1.0.0 | 2026-05-21 | 初始版本。從 jira-project-report v1.0.1 重構，分離數據連接層 |

## 7. 關聯技能

| 技能 | 關係 |
|------|------|
| jira-restful-api-connector | 數據連接層（依賴） |
| agent-skill-improving | 缺陷發現與修正流程 |
| agent-conversation-mode | 對話備份與歸檔 |

---

*本檔案為人類可讀解釋書。LLM 執行指令請參考 SKILL.md。*
*生成時間：2026-05-21*
