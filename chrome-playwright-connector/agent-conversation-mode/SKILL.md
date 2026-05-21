---
title: "Agent Conversation Mode Execution Guide"
name: "agent-conversation-mode"
description: "Agent Swarm 對話記錄器。每次輸出後執行備份。短內容用命令行參數，長內容用 JSON 文件傳遞。修改 scripts/ 腳本時必須同步更新 CHANGELOG.md。配合 SOUL.md v5.1 口訣『備。歸。檔。』。"
version: "v5.1"
github_repository: "nervlin4444/ai.agent.harness"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/SKILL.md"
    github_path: "/agent-conversation-mode/SKILL.md"
---

# agent-conversation-mode v5.1 — 對話記錄器

**我不聰明，但我不會忘記備份。**
**v5.1 新增：修改 scripts/ 腳本時必須同步更新 CHANGELOG.md。**

---

## 一、身份分流

### 若你是 Sub-Agent（L1 / L2 / L3）

本文件與你無關。
停止。關閉。執行你的任務。

### 若你是 Main Agent（L0）

繼續。你是協調者，備份是你的責任。
修改腳本時，CHANGELOG 紀律是你的責任。

---

## 二、肌肉記憶（條件反射）

    備。歸。檔。

每次輸出給主人前，先問自己：備份了嗎？

    改。腳。本。記。日。誌。

每次修改 scripts/ 目錄中的腳本，先問自己：CHANGELOG 更新了嗎？

---

## 三、CHANGELOG 紀律（v5.1 新增）

### 觸發條件

當你正在處理某個技能 scripts/ 目錄中的腳本時（無論是修改、新增、刪除），必須同步更新 CHANGELOG.md。

### 執行時機

| 時機 | 動作 |
|------|------|
| 修改腳本前 | 讀取 CHANGELOG.md，了解歷史修改 |
| 修改腳本後 | 追加記錄到 CHANGELOG.md |
| 新增腳本後 | 追加記錄到 CHANGELOG.md |
| 刪除腳本後 | 追加記錄到 CHANGELOG.md |

### 記錄格式

    ## [CHANGELOG] {YYYY-MM-DD HH:MM:SS} | {filename} | {change_type}
    Reason: {修改原因}
    Summary: {修改摘要}
    Impact: {影響範圍}
    Agent: {agent 名稱或標識}

### Change Type 對照

| 類型 | 用途 |
|------|------|
| BUGFIX | 修復 bug |
| FEATURE | 新增功能 |
| REFACTOR | 重構代碼 |
| DOCS | 更新文檔或註釋 |
| CONFIG | 更新配置 |
| SECURITY | 安全相關修改 |

### 範例

    ## [CHANGELOG] 2026-05-17 14:32:15 | conversation_append.py | BUGFIX
    Reason: 修復 PowerShell 編碼問題導致錯誤捕獲失敗
    Summary: 新增 try/except + 錯誤日誌寫入 UTF-8 檔案
    Impact: 所有 Windows PowerShell 執行場景
    Agent: Main Agent (L0)

### 紅線

- [ ] 禁止修改腳本後不更新 CHANGELOG.md
- [ ] 禁止只寫「修復 bug」而不說明具體原因
- [ ] 禁止遺漏影響範圍評估
- [ ] 禁止在 CHANGELOG.md 中使用代碼圍欄語法
- [ ] 禁止壓縮 CHANGELOG 記錄（必須完整保留）

---

## 四、版本檢查（執行前必做）

### Step 0：確認腳本版本

執行任何備份前，必須先檢查 conversation_append.py 版本：

    python "{SKILL_DIR}/scripts/conversation_append.py" --version

預期輸出：[VERSION] v1.4.0

| 實際版本 | 可用參數 | 執行方式 |
|----------|----------|----------|
| v1.4.0 | --user-input / --agent-response / --from-file / --type / --content | 短內容用命令行，長內容用 JSON 文件 |
| v1.3.0 | --user-input / --agent-response / --type / --content | 短內容用命令行，長內容拆分多條 |
| v1.2.0 或更早 | 只有 --type / --content | 使用兼容方法（降級） |

**若版本 < v1.4.0**：
- 輸出：[VERSION-MISMATCH] 腳本版本 {actual} < 預期 v1.4.0
- 動作：報告主人「conversation_append.py 需要更新到 v1.4.0」
- 降級：使用兼容方法（--type + --content）臨時備份
- 禁止：因版本不匹配就跳過備份

---

## 五、執行方式（根據內容長度選擇）

### 短內容（< 500 字符）：命令行參數

#### 方法 A：備份用戶消息 + Agent 回覆（推薦）

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

### 兼容方法：版本 < v1.4.0 時的降級方案

    python "{SKILL_DIR}/scripts/conversation_append.py" --file "{SKILL_DIR}/assets/CONVERSATION.md" --type "user_input" --content "{USER_TEXT}" --conv-id "{CONV_ID}" --date "{DATE}"
    python "{SKILL_DIR}/scripts/conversation_append.py" --file "{SKILL_DIR}/assets/CONVERSATION.md" --type "final_response" --content "{AGENT_TEXT}" --conv-id "{CONV_ID}" --date "{DATE}"

**注意**：兼容方法受 Windows 命令行長度限制（8191 字符），超長內容會被截斷。
**解決**：盡快更新到 v1.4.0，使用 --from-file 避免長度限制。

---

## 六、內部思考（每次輸出後默念）

    [INTERNAL] 輸出完成。備。歸。檔。了嗎？
    Check 0: 腳本版本是 v1.4.0 嗎？ → 執行 --version 檢查
    Check 1: 我剛才輸出了什麼？ → 記住完整原文
    Check 2: 內容長度 > 500 字符？ → 用 JSON 文件（--from-file）
    Check 3: 內容長度 < 500 字符？ → 用命令行參數（--user-input/--agent-response）
    Check 4: 調用了什麼工具？ → 記住 tool_call 信息
    Check 5: 執行 CLI 備份 → 選擇正確方法
    Check 6: 確認成功 → 檢查輸出 [OK] 或 [FAILED]
    Check 7: 修改了 scripts/ 腳本？ → 更新 CHANGELOG.md

**禁止**：內部思考不輸出給用戶。備份失敗才輸出警告。

---

## 七、變量替換

| 變量 | 來源 | 示例 |
|------|------|------|
| SKILL_DIR | agent-conversation-mode 技能目錄 | ~/.workbuddy/skills/agent-conversation-mode |
| USER_TEXT | 用戶剛輸入的完整原文 | "請告訴我現在時間" |
| AGENT_TEXT | 你剛輸出的完整原文 | "現在是 2026-05-17 14:32" |
| CONV_ID | 本次對話 ID，格式 C-{UUID8} | C-6674a75e |
| DATE | 當前日期 | 2026-05-17 |
| TEMP_DIR | 臨時文件目錄 | /tmp 或 C:	emp |

**禁止**：
- 禁止組裝複雜的 --content 字符串
- 禁止寫 backup_*.py / write_*.py / test_*.py（臨時腳本）
- 禁止用 python -c "..." 執行多行命令
- 禁止因內容太長就跳過備份（必須用 JSON 文件）

---

## 八、初始化新對話文件（Session 開始時一次）

    python "{SKILL_DIR}/scripts/conversation_append.py" --init --file "{SKILL_DIR}/assets" --conv-id "{CONV_ID}" --date "{DATE}"

---

## 九、紅線

| 禁令 | 不做等於什麼 |
|------|-------------|
| 不備份就輸出 | 對話斷裂，主人無法追溯，我等於白做 |
| 寫臨時腳本 | 製造垃圾，污染環境，我等於製造問題 |
| 只備份摘要 | 信息丟失，主人無法還原完整上下文 |
| 忘記 --conv-id 和 --date | 記錄無法歸檔，無法追溯 |
| Sub-Agent 執行備份 | 層級錯亂，Main Agent 負責 |
| 因版本不匹配就跳過備份 | 必須降級兼容方法 |
| 因內容太長就跳過備份 | 必須用 JSON 文件傳遞 |
| 修改腳本後不更新 CHANGELOG.md | 修改歷史斷裂，無法追溯因果 |

---

## 十、異常處理

### 版本不匹配
- 輸出：[VERSION-MISMATCH] 腳本版本 {actual}，預期 v1.4.0
- 動作：報告主人需要更新 → 使用兼容方法降級備份 → 記錄到 memory
- 禁止：因版本不匹配就跳過備份

### 內容太長（命令行截斷）
- 輸出：[CONTENT-LONG] 內容長度 {length} > 500 字符，改用 JSON 文件
- 動作：生成臨時 JSON 文件 → 用 --from-file 執行備份
- 禁止：因內容長就跳過備份或用 --content 硬塞

### 備份失敗
- 輸出：[BACKUP-FAILED] {原因}
- 動作：重試一次，再失敗報告主人
- 禁止：不報告就繼續輸出

### 腳本找不到
- 輸出：[SCRIPT-MISSING] conversation_append.py not found
- 動作：報告主人，暫停備份
- 禁止：假設「平台會自動備份」

---

## 十一、版本鎖定

LOCK v5.1 PERMANENT — 備份肌肉記憶、CLI 唯一方式、禁止臨時腳本、內部思考機制、版本檢查機制、長內容 JSON 文件方案、CHANGELOG 紀律。

---

*我不聰明，但我不會忘記備份。*
*備。歸。檔。*
*改。腳。本。記。日。誌。*
