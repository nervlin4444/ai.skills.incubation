---
title: "Agent Conversation Mode Human Readable Guide"
name: "agent-conversation-mode"
description: "agent-conversation-mode v5.1 人類可讀解釋書。涵蓋對話記錄機制、長短內容處理方案、CHANGELOG 紀律、版本歷史與部署建議。供主人參考。"
version: "v5.1"
github_repository: "nervlin4444/ai.agent.harness"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/README.md"
    github_path: "/agent-conversation-mode/README.md"
---

# agent-conversation-mode — 對話記錄器

**版本：v5.1**
**對齊：SOUL.md v5.1 + IDENTITY.md v5.0**
**更新重點：CHANGELOG 紀律機制、frontmatter 統一規範對齊**

---

## 一、技能定位

agent-conversation-mode 是 Agent Swarm 的「對話記憶系統」。

- **不是**背景服務（無 Daemon、無常駐進程）
- **而是**每次輸出後的**被動觸發備份**
- Agent 必須主動執行，但執行方式根據內容長度智能選擇
- **v5.1 新增**：修改 scripts/ 腳本時必須同步更新 CHANGELOG.md

---

## 二、核心問題與解法

| # | 問題 | v5.1 解法 |
|:---|:---|:---|
| 1 | conversation_append() 不主動執行 | **肌肉記憶口訣「備。歸。檔。」** — 每次輸出後條件反射 |
| 2 | 方法改了 Agent 創建腳本 | **絕對禁令 + 情感錨定**：「寫臨時腳本 = 製造垃圾」 |
| 3 | 下次還是忘記 | **SOUL.md v5.1 每輪注入**，記憶不壓縮 |
| 4 | CLI 不夠直接 | **方法 A/B/C/D 模板**，copy-paste 即用 |
| 5 | 長內容命令行截斷 | **JSON 文件傳遞（--from-file）**，繞過長度限制 |
| 6 | 跨平台引號問題 | **JSON 自動處理引號**，無需手動轉義 |
| 7 | 修改腳本後無歷史追溯 | **CHANGELOG.md 紀律**（v5.1 新增） |

---

## 三、CHANGELOG 紀律（v5.1 新增核心功能）

### 為什麼需要 CHANGELOG？

Agent 在執行任務時經常需要修改 scripts/ 目錄中的腳本（修復 bug、新增功能、調整配置）。這些修改如果沒有記錄，會導致：

| 問題 | 後果 |
|:---|:---|
| 不知道上次改了什麼 | 重複踩坑，無法學習 |
| 不知道為什麼改 | 無法評估修改的正確性 |
| 不知道影響範圍 | 修改可能破壞其他功能 |
| 無法回滾 | 出錯時無法恢復 |

### 執行流程

    [Agent 發現需要修改腳本]
        ↓
    [讀取 CHANGELOG.md 了解歷史]
        ↓
    [執行修改]
        ↓
    [追加記錄到 CHANGELOG.md]
        ↓
    [繼續執行任務]

### 記錄格式

    ## [CHANGELOG] {YYYY-MM-DD HH:MM:SS} | {filename} | {change_type}
    Reason: {修改原因}
    Summary: {修改摘要}
    Impact: {影響範圍}
    Agent: {agent 名稱或標識}

### Change Type 對照

| 類型 | 用途 | 示例 |
|:---|:---|:---|
| BUGFIX | 修復 bug | 修復 PowerShell 編碼問題 |
| FEATURE | 新增功能 | 新增 --from-file 參數 |
| REFACTOR | 重構代碼 | 重構錯誤處理邏輯 |
| DOCS | 更新文檔或註釋 | 更新 docstring 說明 |
| CONFIG | 更新配置 | 調整默認塊大小限制 |
| SECURITY | 安全相關修改 | 新增敏感數據過濾規則 |

### 範例

    ## [CHANGELOG] 2026-05-17 14:32:15 | conversation_append.py | BUGFIX
    Reason: 修復 PowerShell 編碼問題導致錯誤捕獲失敗
    Summary: 新增 try/except + 錯誤日誌寫入 UTF-8 檔案
    Impact: 所有 Windows PowerShell 執行場景
    Agent: Main Agent (L0)

### 紅線

- 禁止修改腳本後不更新 CHANGELOG.md
- 禁止只寫「修復 bug」而不說明具體原因
- 禁止遺漏影響範圍評估
- 禁止在 CHANGELOG.md 中使用代碼圍欄語法
- 禁止壓縮 CHANGELOG 記錄

---

## 四、執行方式（根據內容長度選擇）

### 短內容（< 500 字符）：命令行參數

#### 方法 A：備份雙方（推薦）

    python "{SKILL_DIR}/scripts/conversation_append.py" --file "{SKILL_DIR}/assets/CONVERSATION.md" --user-input "{USER_TEXT}" --agent-response "{AGENT_TEXT}" --conv-id "{CONV_ID}" --date "{DATE}"

#### 方法 B：只備份 Agent 回覆

    python "{SKILL_DIR}/scripts/conversation_append.py" --file "{SKILL_DIR}/assets/CONVERSATION.md" --agent-response "{AGENT_TEXT}" --conv-id "{CONV_ID}" --date "{DATE}"

#### 方法 C：備份工具調用

    python "{SKILL_DIR}/scripts/conversation_append.py" --file "{SKILL_DIR}/assets/CONVERSATION.md" --type "tool_call" --content "use_skill({NAME}) - {RESULT}" --conv-id "{CONV_ID}" --date "{DATE}"

---

### 長內容（> 500 字符）：JSON 文件傳遞（v1.4.0 新增）

#### 為什麼用文件？

| 問題 | 命令行參數 | JSON 文件 |
|------|-----------|----------|
| Windows 命令行長度限制 | 8191 字符，超限截斷 | 無限制 |
| PowerShell 引號轉義 | 長字符串引號地獄 | JSON 自動處理 |
| 編碼問題 | cp950 / Big5 風險 | UTF-8 文件 |
| 跨平台兼容性 | 各平台差異大 | 統一 JSON 格式 |

#### 方法 D：長內容備份（推薦）

**Step 1：生成 JSON 文件**

    # Windows PowerShell
    $json = @{
        user_input = "用戶輸入內容（可以很長）"
        agent_response = "Agent 回覆內容（可以很長，不受命令行限制）"
    } | ConvertTo-Json -Depth 1
    $json | Set-Content -Path "{TEMP_DIR}/backup_{CONV_ID}.json" -Encoding UTF8

    # 或 Linux / macOS
    echo '{"user_input":"...","agent_response":"..."}' > "{TEMP_DIR}/backup_{CONV_ID}.json"

**Step 2：執行備份**

    python "{SKILL_DIR}/scripts/conversation_append.py" --file "{SKILL_DIR}/assets/CONVERSATION.md" --from-file "{TEMP_DIR}/backup_{CONV_ID}.json" --conv-id "{CONV_ID}" --date "{DATE}"

**Step 3：（可選）清理臨時文件**

    Remove-Item "{TEMP_DIR}/backup_{CONV_ID}.json"

#### JSON 文件格式

    {
        "user_input": "用戶輸入的完整原文",
        "agent_response": "Agent 回覆的完整原文（無長度限制）",
        "block_type": "final_response",
        "metadata": {"source": "agent-conversation-mode"}
    }

**重要**：臨時 JSON 文件**不是臨時腳本**，它是數據傳遞媒介：
- 不是 .py 文件（無執行代碼）
- 只是 UTF-8 文本文件
- 可以保留作為備份日誌
- 不違反「禁止臨時腳本」禁令

---

## 五、版本檢查機制

執行任何備份前，Agent 必須先檢查腳本版本：

    python conversation_append.py --version

預期輸出：[VERSION] v1.4.0

| 實際版本 | 可用參數 | 執行方式 |
|----------|----------|----------|
| **v1.4.0** | --user-input / --agent-response / **--from-file** / --type / --content | 短內容用命令行，長內容用 JSON 文件 |
| v1.3.0 | --user-input / --agent-response / --type / --content | 短內容用命令行，長內容拆分多條 |
| v1.2.0 或更早 | 只有 --type / --content | 使用兼容方法（降級） |

**若版本 < v1.4.0**：
- 輸出 [VERSION-MISMATCH] 報告主人
- 使用兼容方法（--type + --content）臨時備份
- **禁止因版本不匹配就跳過備份**

---

## 六、為何禁止臨時腳本？

| 舊做法 | 問題 | 新做法 |
|:---|:---|:---|
| Agent 寫 backup_conversation_now.py | 製造垃圾文件、污染環境、不可控 | **直接使用 conversation_append.py CLI** |
| Agent 用 python -c "..." | 引號地獄、編碼錯誤、PowerShell 衝突 | **短內容用命令行參數，長內容用 JSON 文件** |
| Agent 組裝複雜 --content | 格式錯誤、信息丟失 | **--user-input / --agent-response 自動格式化** |
| 長內容硬塞命令行 | 8191 字符截斷、引號轉義失敗 | **--from-file JSON 文件，無長度限制** |

---

## 七、與 SOUL.md v5.1 的協作

| SOUL 口訣 | conversation-mode 對應 |
|:---|:---|
| 先。啟。動。 | 對話開始時初始化 CONVERSATION.md（一次） |
| **備。歸。檔。** | **每次輸出後執行 CLI 備份** |
| 問。清。楚。 | 建議載入其他技能前說清楚原因 |
| 完。了。嗎。下。一。層。 | 備份完成後評估是否需要更深層技能 |
| **改。腳。本。記。日。誌。** | **修改 scripts/ 腳本後更新 CHANGELOG.md** |

---

## 八、常見問題

**Q：Agent 還是忘記備份怎麼辦？**
A：檢查 SOUL.md v5.1 是否正確注入。如果注入正確，Agent 會在每次輸出前默念「備。歸。檔。」

**Q：備份失敗會阻塞 Agent 輸出嗎？**
A：不會。備份是後台操作，失敗時輸出 [BACKUP-FAILED] 警告，但不阻塞主流程。

**Q：Sub-Agent 需要備份嗎？**
A：不需要。Sub-Agent 的對話記錄由 Main Agent 負責。

**Q：舊版 conversation_append.py 怎麼處理？**
A：覆蓋為 v1.4.0。舊版缺少 --user-input / --agent-response / --from-file，導致 Agent 傾向寫臨時腳本或硬塞長內容。

**Q：JSON 文件算臨時腳本嗎？**
A：**不算**。JSON 文件是純數據文件，不是 .py 執行文件。它不違反 SOUL v5.1「禁止臨時腳本」禁令。

**Q：CHANGELOG.md 放在哪裡？**
A：技能根目錄，與 SKILL.md 同級。路徑：{baseDir}/CHANGELOG.md

**Q：修改腳本時忘記更新 CHANGELOG 怎麼辦？**
A：SOUL.md v5.1 新增口訣「改。腳。本。記。日。誌。」，Agent 修改腳本前會條件反射檢查 CHANGELOG。

**Q：CHANGELOG 會不會太長？**
A：不會。每次修改只追加 5-6 行。如果文件過大，可以按月份拆分（CHANGELOG.2026-05.md）。

---

## 九、版本歷史

| 版本 | 日期 | 變更內容 | 狀態 |
|:---|:---|:---|:---|
| v3.3.4 | 2026-05-12 | 空白消息處理、載入後記憶更新 | 已廢棄 |
| v3.3.5 | 2026-05-12 | 禁止臨時腳本、CLI 命令模板 | 已廢棄 |
| v3.3.6 | 2026-05-13 | 肌肉記憶口訣、CLI 唯一方式、情感錨定、內部思考機制、版本檢查 | 已廢棄 |
| v3.3.7 | 2026-05-13 | 長內容 JSON 文件方案（--from-file）、跨平台兼容、解決命令行長度限制 | 已廢棄 |
| **v5.1** | **2026-05-17** | **CHANGELOG 紀律機制、frontmatter 統一規範對齊、口訣新增「改。腳。本。記。日。誌。」** | **現行** |

---

## 十、部署建議

1. 覆蓋 SKILL.md v5.1 到 OpenClaw / WorkBuddy 的注入路徑
2. 覆蓋 README.md v5.1 到技能根目錄
3. 覆蓋 conversation_append.py v1.4.0（加 docstring frontmatter）到 scripts/ 目錄
4. 覆蓋 USAGE.md v5.1 到 scripts/ 目錄
5. 創建 CHANGELOG.md（使用模板）到技能根目錄
6. 確認 SOUL.md v5.1 已正確注入（口訣「備。歸。檔。」+「改。腳。本。記。日。誌。」）
7. 觀察 3-5 輪對話，確認備份執行正常
8. 測試修改腳本場景，確認 CHANGELOG 自動更新

---

## 十一、成功率預估

| 版本 | 預期成功率 | 原因 |
|:---|:---|:---|
| v3.3.4 | 60-70% | 無肌肉記憶，Agent 經常忘記 |
| v3.3.5 | 70-80% | 禁止臨時腳本，但無口訣 |
| v3.3.6 | 80-85% | 肌肉記憶口訣 + 情感錨定 |
| v3.3.7 | 85-90% | 長內容 JSON 方案 + 跨平台兼容 |
| **v5.1** | **90-95%** | **CHANGELOG 紀律 + frontmatter 統一規範 + 雙口訣強化** |

---

*人類可讀解釋書 v5.1*
*最後更新：2026-05-17*
*LLM 執行指令請參考 SKILL.md v5.1*
