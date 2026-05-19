---
title: "Board Field Mapping"
name: "github-restful-api-connector"
description: "看板欄位映射規則。定義 Agent 狀態、任務類型與 GitHub Project v2 欄位之間的雙向映射。"
version: "0.1.0"
github_repository: "nervlin4444/ai.skills.devops"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/references/MAPPING.md"
    github_path: "/github-restful-api-connector/references/MAPPING.md"
---

# MAPPING.md — 看板欄位映射規則

## 1. 狀態欄位映射（Status Field）

GitHub Project v2 的 Status 為單選欄位（Single Select）。

| 本技能狀態名稱 | GitHub Project 選項名稱 | 用途說明 |
|----------------|------------------------|----------|
| Todo | Todo | 等待執行的任務 |
| In Progress | In Progress | Agent 正在處理中 |
| Done | Done | 任務成功完成 |
| Failed | Failed | 任務執行失敗，附錯誤日誌 |

## 2. 自定義欄位映射（Custom Fields）

| 本技能欄位名稱 | GitHub Project 欄位名稱 | 欄位類型 | 必填 | 預設值 |
|----------------|------------------------|----------|------|--------|
| agent_name | Agent Name | Single line text | 是 | 空 |
| task_type | Task Type | Single select | 否 | backup / update / review / deploy |
| start_time | Start Time | Date | 否 | 空 |
| end_time | End Time | Date | 否 | 空 |
| duration_sec | Duration (sec) | Number | 否 | 0 |
| log_url | Log URL | Single line text | 否 | 空 |
| git_commit | Git Commit SHA | Single line text | 否 | 空 |
| retry_count | Retry Count | Number | 否 | 0 |
| max_retry | Max Retry | Number | 否 | 3 |
| error_summary | Error Summary | Paragraph | 否 | 空 |

## 3. 任務類型映射（Task Type Field）

| 任務類型 | 說明 | 典型觸發來源 |
|----------|------|--------------|
| backup | Agent 備份當前狀態到 Git | Agent 生命週期 |
| update | 更新專案代碼或配置 | 主人指令 / 排程 |
| review | 審查代碼或輸出物 | Evaluator Agent |
| deploy | 部署到生產或測試環境 | CI/CD 觸發 |
| query | 查詢類任務（如 LLM 排行榜） | 定時排程 |
| merge | 合併配置或分支 | 主人指令 |

## 4. Agent Sessions 狀態映射

GitHub 2026 原生 Agent Sessions 狀態與本技能看板狀態的雙向同步：

| Session 狀態 | 看板狀態 | 說明 |
|--------------|----------|------|
| queued | Todo | Session 已創建，等待執行 |
| working | In Progress | Agent 正在處理 Issue |
| completed | Done | Session 成功完成 |
| failed | Failed | Session 執行失敗 |
| cancelled | Failed | Session 被手動取消 |

## 5. 優先級映射（Priority Field，可選）

| 優先級名稱 | 數值 | 顏色建議 |
|------------|------|----------|
| Critical | 1 | 紅色 |
| High | 2 | 橙色 |
| Normal | 3 | 黃色 |
| Low | 4 | 綠色 |

## 6. 映射一致性規則

RULE 6.1 — 名稱大小寫
    GitHub Project 欄位名稱大小寫不敏感，但本技能統一使用首字母大寫格式。
    腳本內部處理時統一轉小寫比對，避免大小寫差異導致匹配失敗。

RULE 6.2 — 選項 ID 快取
    Status 欄位的 option ID 為 GraphQL 內部識別碼，非人類可讀名稱。
    github_restful_core.py 必須在首次運行時快取欄位 ID 與選項 ID，寫入本地 JSON 快取。
    快取路徑：~/.workbuddy/skills/github-restful-api-connector/cache/field.cache.json

RULE 6.3 — 欄位不存在處理
    若 GitHub Project 缺少本技能定義的自定義欄位，腳本應單行報錯並提示主人先手動創建欄位。
    禁止腳本自動創建欄位，避免污染 Project 結構。
