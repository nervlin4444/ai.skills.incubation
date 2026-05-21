---
title: "Skill Improvement Operations Manual"
name: "agent-skill-improving"
description: "技能改進操作手冊的人類可讀說明書。涵蓋操作手冊定位、建議確認機制、Patch應用策略分級、強制合規驗證、跨平台兼容檢查、長內容處理檢查、臨時文件管理檢查。融入conversation_append.py v1.4.0長文件經驗。"
version: "v1.2.4"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T15:28:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/README.md"
    github_path: "agent-skill-improving/README.md"
---

# agent-skill-improving — 技能改進操作手冊

> 版本：v1.2.4
> 對齊：SKILL.md v1.2.4 + SOUL.md v5.0 + IDENTITY.md v5.0
> 更新重點：**跨平台兼容檢查、長內容處理檢查、臨時JSON文件管理**

---

## 一、技能定位（核心改變）

agent-skill-improving **不是執行指令，是操作手冊**。

| 舊理解 | 新理解 |
|:---|:---|
| 「發現缺陷就改」 | **「發現缺陷 → 建議主人 → 等待確認 → 按手冊執行」** |
| Agent 擅自改進 | Agent 只負責「建議」，改進權在主人 |
| 直接修改原始檔案 | 必須以 Patch 形式，備份後應用 |
| **只驗證功能正確（舊）** | **還要驗證跨平台兼容、長內容處理、臨時文件管理（v1.2.4 新增）** |

**為何改為操作手冊？**
- 技能是主人的資產，Agent 不應擅自修改
- 改進有風險，必須經主人知情/確認
- 操作手冊確保「每次改進都按同一套標準執行」

---

## 二、核心工作流：三步操作

### Step 1：發現缺陷（內部思考）

Agent 內部默念口訣：

    缺。改。問。

- 缺：什麼技能？什麼版本？什麼缺陷？
- 改：建議怎麼修復？影響多大？
- **新增（v1.2.4）：是否涉及跨平台？是否涉及長內容？是否涉及臨時文件？**
- 問：建議主人，等待確認

### Step 2：建議主人（輸出給用戶）

    [SUGGEST] agent-skill-improving
    Skill: {技能名稱} v{版本}
    Defect: {缺陷描述}
    Impact: {影響範圍}
    Cross-Platform: {是否涉及跨平台兼容}
    Long-Content: {是否涉及長文件處理}
    Proposed Fix: {建議修復方式}
    Confirm: [YES / NO / DEFER]

**禁止**：
- 禁止不輸出建議就直接改代碼
- 禁止建議不明確
- 禁止不等確認就執行

### Step 3：按手冊執行（主人確認後）

主人說 YES 後，嚴格按順序：

    1. 備份舊版本
    2. 生成 Patch
    3. 應用 Patch（replace_in_file → 重試 → write_to_file 降級）
    4. 更新版本號
    5. 驗證合規（skill_validate.py --strict）
    6. **驗證跨平台（v1.2.4 新增）**
    7. **驗證長內容（v1.2.4 新增）**
    8. **驗證臨時文件（v1.2.4 新增）**
    9. 記錄歷史
    10. 通知 skill-acquiring

**禁止跳過任何一步。**

---

## 三、新增驗證項（v1.2.4）

### 驗證 6：跨平台兼容性

改進涉及腳本執行時，必須檢查：

| 檢查項 | Windows | Linux/macOS | 通過標準 |
|--------|---------|-------------|----------|
| 路徑分隔符 | `\` 或 `/` | `/` | 使用 `pathlib.Path`，禁止硬編碼 |
| 命令行長度限制 | 8191 字符 | 通常無限制 | 長內容用 `--from-file`，不用命令行 |
| 引號轉義 | PowerShell `"` 地獄 | Bash 單引號友好 | JSON 文件傳遞，避免引號問題 |
| 編碼聲明 | cp950 風險 | UTF-8 默認 | 文件必須用 UTF-8，聲明 `# -*- coding: utf-8 -*-` |
| 換行符 | `\r\n` | `\n` | Python 自動處理，無需擔心 |

**為何需要？**
0513 實戰教訓：Agent 在 Windows 用 PowerShell 生成 JSON 文件，但沒考慮 Linux/macOS 的 `echo` 語法差異，導致跨平台部署失敗。

**失敗處理**：若某平台不兼容，必須在 Patch 中說明「已知限制：{平台} 需 {解決方案}」。

### 驗證 7：長內容處理

改進涉及內容傳遞時，必須測試：

    Test A: 短內容（< 500 字符）→ 用 --user-input / --agent-response
    Test B: 長內容（> 500 字符）→ 用 --from-file JSON 文件
    Test C: 超長內容（> 50KB）→ 檢查 max_block_size，可能需要拆分

**為何需要？**
0513 實戰教訓：Agent 輸出長回覆後，用 `--user-input` 硬塞命令行，結果被 Windows 8191 字符限制截斷，備份不完整。

**失敗處理**：若長內容處理失敗，禁止回到「寫臨時腳本」方案，必須優化 JSON 文件機制。

### 驗證 8：臨時文件管理

改進涉及 `--from-file` 時，必須確認：

| 檢查項 | 要求 | 禁止 |
|--------|------|------|
| 臨時 JSON 文件位置 | 放在系統 temp 目錄或技能 assets/temp/ | 放在用戶桌面、文件等永久目錄 |
| 文件命名 | backup_{conv_id}_{timestamp}.json | backup.json、temp.json 等無標識名稱 |
| 編碼 | UTF-8，無 BOM | cp950、Big5、GBK |
| 清理機制 | 備份成功後可選刪除 | 堆積不清理 |
| 文件內容 | 純 JSON 數據，無執行代碼 | 包含 Python 代碼、shell 命令 |

**重要**：臨時 JSON 文件 **不是臨時腳本**：
- 不是 `.py` 文件（無執行代碼）
- 只是 UTF-8 數據文件
- 不違反 SOUL v5.0「禁止臨時腳本」禁令

---

## 四、Patch 應用策略分級

| 策略 | 條件 | 操作 | 前置要求 |
|:---|:---|:---|:---|
| A replace_in_file | 首次嘗試 | 精確字符串替換 | 無 |
| B 重試 | A 失敗（全形標點/編碼差異） | 修正匹配條件 | 記錄失敗原因 |
| C write_to_file 降級 | B 連續失敗 >= 3 次 | 重寫整個文件 | **已備份舊版本** |

**為何需要分級？**

0512 實戰教訓：Agent 反覆嘗試 replace_in_file 失敗，陷入「分析為什麼失敗」的無限循環，花了幾十分鐘才靠 write_to_file 解決。

v1.2.4 的解決方案：
- 最多分析 3 次失敗原因
- 第 4 次直接降級 write_to_file
- 禁止無限糾結

---

## 五、強制合規驗證

應用 Patch 後、交付前，必須執行：

    python skill_validate.py --skill-dir ./{skill_name}/ --strict --report-path ./improve/{skill_name}/VALIDATION_REPORT.md

通過標準：
- 0 項 CRITICAL 違規
- 0 項 ARCH 架構紅線違規
- **跨平台兼容檢查通過（v1.2.4 新增）**
- **長內容處理檢查通過（v1.2.4 新增）**
- **臨時文件管理檢查通過（v1.2.4 新增）**
- 報告已輸出

**驗證失敗 → 自動回滾 → 報告主人 → 禁止交付。**

---

## 六、與 SOUL.md v5.0 的協作

| SOUL 口訣 | skill-improving 對應 |
|:---|:---|
| 先。啟。動。 | 對話開始時讀取記憶，回顧歷史缺陷 |
| 備。歸。檔。 | 改進前備份舊版本 |
| 問。清。楚。 | 建議改進前說清楚缺陷和修復方式 |
| 完。了。嗎。下。一。層。 | 改進完成後建議是否需要 skill-acquiring |

---

## 七、常見問題

**Q：為什麼 Agent 不能擅自改進？**
A：技能是主人的資產。Agent 是僕，不是主。擅自改進 = 越權。

**Q：主人說 NO 怎麼辦？**
A：記錄到 SKILL_CORRECTION.md：「建議被拒絕，原因：{主人理由}」。長期累積後，Agent 會學習主人的偏好。

**Q：驗證失敗但改進內容邏輯正確怎麼辦？**
A：違規項通常涉及架構紅線（檔案命名、frontmatter 格式）。先修復違規項，重新驗證通過後方可交付。禁止繞過驗證。

**Q：replace_in_file 反覆失敗怎麼辦？**
A：3 次失敗後直接降級 write_to_file，禁止無限分析。但必須先備份。

**Q：跨平台兼容失敗怎麼辦？**
A：在 Patch 中標註「已知限制：{平台} 需 {解決方案}」。例如「Linux 用戶需手動將 `\` 改為 `/`」。

**Q：長內容處理失敗怎麼辦？**
A：禁止回到「寫臨時腳本」方案。優化 JSON 文件機制：檢查文件編碼、確認 JSON 格式正確、測試不同長度閾值。

**Q：臨時 JSON 文件算臨時腳本嗎？**
A：**不算**。JSON 文件是純數據文件，不是 `.py` 執行文件。它不違反 SOUL v5.0「禁止臨時腳本」禁令。

---

## 八、版本歷史

| 版本 | 日期 | 變更內容 |
|:---|:---|:---|
| v1.2.0 | 2026-05-11 | 初始版本：趨勢分析、Patch 生成、回滾保護 |
| v1.2.1 | 2026-05-11 | 新增強制合規驗證（skill_validate.py） |
| v1.2.2 | 2026-05-12 | 新增 Patch 應用策略分級（replace_in_file → write_to_file 降級） |
| v1.2.3 | 2026-05-13 | 改為操作手冊定位、建議確認機制、漸進式披露、內部思考後建議 |
| **v1.2.4** | **2026-05-13** | **新增跨平台兼容檢查、長內容處理檢查、臨時文件管理檢查** |

---

*人類可讀解釋書 v1.2.4*
*本文件是操作手冊，不是執行指令。*
*發現缺陷 → 建議主人 → 等待確認 → 按手冊執行。*
