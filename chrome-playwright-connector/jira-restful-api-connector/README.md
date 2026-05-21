---
title: "jira-restful-api-connector — README.md"
description: "人類可讀版技能解釋書。通用 Jira REST API 數據連接技能，零業務邏輯，可被任何 Jira 相關技能復用。"
version: "v0.1.0"
date: "2026-05-21"
author: "Kevin Lin / Agent Swarm Architecture"
skill_bundle: "jira-restful-api-connector"
---

# jira-restful-api-connector — 技能解釋書

## 1. 技能定位

通用 Jira REST API 數據連接技能。提供 Jira 實例連接、JQL 查詢、Issue 字段解析、日期處理等基礎能力。

**設計原則：零業務邏輯**。不認識 milestone、mockup round、負責人統計等概念。只負責「連接」與「查詢」，返回原始數據。

**分離背景**：本技能從 jira-project-report v1.0.1 的核心庫（jira_report_core.py）分離而來，將通用 API 能力獨立為可復用組件。

## 2. 目錄結構與文件規範

### 2.1 標準目錄結構

    skills/jira-restful-api-connector/
    ├── SKILL.md                          ← LLM 執行指令（此檔案不供人類閱讀）
    ├── README.md                         ← 本檔案（人類解釋書）
    ├── .env                               ← Jira 認證（用戶自建，不入版本庫）
    ├── .env.example                       ← 環境變數模板（供用戶複製填寫）
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

### 2.2 文件命名規範

統一使用 xxx.yyy.zzz.ext 格式，全部以點號（.）作為分隔符，禁止使用中劃線（-）或下劃線（_）。

    正確: jira.restful.core.py, jira.query.basic.py
    錯誤: jira_restful_core.py, jira-query-basic.py

例外: Python import 機制將點號解析為包路徑，因此 .py 腳本實際執行時使用下劃線:
    檔案名: jira.restful.core.py
    import: import jira_restful_core as jira_core

## 3. 模組分工

| 模組檔案 | 類型 | 用途 |
|----------|------|------|
| jira.restful.core.py | 共用庫 | JiraClient 類、load_env()、認證自動判斷、HTTP 錯誤重試 |
| jira.query.basic.py | 共用庫 | 基礎 JQL 查詢封裝（search / get / changelog） |
| jira.query.advanced.py | 共用庫 | 高級查詢（遞歸子孫、批量關鍵字搜索、緩存構建） |
| jira.field.parser.py | 共用庫 | Issue 字段安全解析（assignee、status、duedate 等） |
| jira.datetime.utils.py | 共用庫 | Jira 日期格式處理（+0800 → +08:00、天數計算） |

## 4. 認證方式

### 4.1 .env 環境變數

在技能根目錄創建 .env：

    JIRA_URL=http://your-jira-instance.com:8080
    JIRA_USERNAME=your_username
    JIRA_API_TOKEN=your_api_token

或（向後兼容舊版變數名）：

    JIRA_URL=http://your-jira-instance.com:8080
    JIRA_USER=your_username
    JIRA_PAT=your_api_token

### 4.2 認證自動判斷

JiraClient 自動判斷認證方式：

| 條件 | 認證方式 | 說明 |
|------|----------|------|
| username + token 同時存在 | Basic Auth | Base64 編碼 (username:token) |
| 僅 token 存在 | Bearer Token | 直接使用 token |
| 皆無 | 報錯停止 | 單行報錯 |

### 4.3 安全提醒

.env 檔案必須加入 .gitignore，禁止提交到版本庫。

## 5. 配置檔格式

### 5.1 config/config.json

    {
      "timeout": 60,
      "retry_max": 3,
      "api_version": 2,
      "rate_limit": {
        "backoff_strategy": "exponential",
        "backoff_max": 3
      }
    }

### 5.2 .env.example（模板）

    JIRA_URL=http://your-jira-instance.com:8080
    JIRA_USERNAME=your_username
    JIRA_API_TOKEN=your_api_token

## 6. 錯誤處理

### 6.1 錯誤分級

| 錯誤類型 | HTTP 碼 | 行為 |
|----------|---------|------|
| 認證失敗 | 401 | 停止執行，報錯 PAT/Token 無效 |
| 速率限制 | 403 | 指數退避重試（max 3 次） |
| 資源不存在 | 404 | 停止執行，報錯 Issue/資源不存在 |
| 參數錯誤 | 422 | 停止執行，報錯 JQL 語法錯誤 |
| 伺服器錯誤 | 5xx | 線性退避重試（max 5 次） |

### 6.2 報錯格式

    ERROR: [簡短描述] | [相關參數] | Stop.
    WARN: [簡短描述] | [相關參數] | Continue.

## 7. 與消費者技能的協作

### 7.1 wilson-project-report（報表生成層）

wilson-project-report 作為本技能的第一個消費者，通過以下方式引用：

    import sys
    from pathlib import Path
    SKILL_ROOT = Path(__file__).parent.parent
    sys.path.insert(0, str(SKILL_ROOT / "../jira-restful-api-connector/scripts"))
    import jira_restful_core as jira_core

或通過技能包管理系統（WorkBuddy / OpenClaw skill dependency）聲明依賴。

### 7.2 職責邊界

| 層級 | 職責 | 配置存放 |
|------|------|----------|
| jira-restful-api-connector | 連接 Jira API、執行 JQL、解析字段、管理緩存 | .env + config/config.json |
| wilson-project-report | 報表生成、HTML 渲染、歷史記錄、業務統計 | config/config.json + 各 report.*.py 頂層常量 |

## 8. 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| v0.1.0 | 2026-05-21 | 初始版本。分離自 jira-project-report v1.0.1 核心庫。功能代號 F-001~F-005、路徑剛性規則、錯誤分級處理 |

## 9. 關聯技能

| 技能 | 關係 |
|------|------|
| wilson-project-report | 消費者（報表生成層） |
| agent-skill-improving | 缺陷發現與修正流程 |
| github-restful-api-connector | 參考架構（LAYER 架構、功能代號、錯誤分級） |

---

*本檔案為人類可讀解釋書。LLM 執行指令請參考 SKILL.md。*
*生成時間：2026-05-21*
