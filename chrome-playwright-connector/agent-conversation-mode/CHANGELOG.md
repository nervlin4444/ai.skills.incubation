---
title: "Agent Conversation Mode Change Log"
name: "agent-conversation-mode"
description: "Record of all script modifications in the agent-conversation-mode skill. Each entry documents the reason, summary, and impact of changes to scripts in the scripts/ directory."
version: "v5.1"
github_repository: "nervlin4444/ai.agent.harness"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/CHANGELOG.md"
    github_path: "/agent-conversation-mode/CHANGELOG.md"
---

# CHANGELOG.md — agent-conversation-mode

**本文件記錄 agent-conversation-mode 技能 scripts/ 目錄中所有腳本的修改歷史。**
**每次修改腳本時，Agent 必須同步追加記錄到此文件。**
**禁止壓縮。禁止摘要。禁止遺漏因果鏈。**

---

## 格式規範

    ## [CHANGELOG] {YYYY-MM-DD HH:MM:SS} | {filename} | {change_type}
    Reason: {修改原因}
    Summary: {修改摘要}
    Impact: {影響範圍}
    Agent: {agent 名稱或標識}

### Change Type 對照

| 類型 | 說明 |
|------|------|
| BUGFIX | 修復 bug |
| FEATURE | 新增功能 |
| REFACTOR | 重構代碼 |
| DOCS | 更新文檔或註釋 |
| CONFIG | 更新配置 |
| SECURITY | 安全相關修改 |

---

## 修改記錄

## [CHANGELOG] 2026-05-17 16:00:00 | SKILL.md | FEATURE
Reason: 統一 frontmatter 規範並新增 CHANGELOG 紀律機制
Summary: 全面更新 frontmatter 為統一規範 v1.0.0，新增 CHANGELOG 紀律章節，新增口訣「改。腳。本。記。日。誌。」
Impact: 所有 agent-conversation-mode 技能檔案
Agent: Main Agent (L0)

## [CHANGELOG] 2026-05-17 16:00:00 | README.md | FEATURE
Reason: 統一 frontmatter 規範並新增 CHANGELOG 紀律說明
Summary: 更新為統一 frontmatter，新增 CHANGELOG 專章，記錄 v3.3.7 到 v5.1 的演進
Impact: 人類可讀解釋書
Agent: Main Agent (L0)

## [CHANGELOG] 2026-05-17 16:00:00 | USAGE.md | FEATURE
Reason: 更新使用手冊以匹配 conversation_append.py v1.4.0
Summary: 新增 --from-file 長內容方案、--user-input/--agent-response 短內容方案、CHANGELOG 整合章節
Impact: scripts/ 目錄使用教程
Agent: Main Agent (L0)

## [CHANGELOG] 2026-05-17 16:00:00 | conversation_append.py | CONFIG
Reason: 加入 docstring YAML frontmatter 以符合技能包統一規範
Summary: 在模組頂部加入 --- 包裹的 YAML frontmatter 塊，包含 title/name/description/version/github_repository 等強制欄位
Impact: 腳本元數據標準化，便於 Agent 自動推送
Agent: Main Agent (L0)

---

*本文件由 Agent 自動維護。*
*禁止手動刪除或修改歷史記錄。*
*如需拆分，按月份創建 CHANGELOG.YYYY-MM.md。*
