---
title: "Agent Skill Improving Execution Guide"
name: agent-skill-improving
description: "技能改進執行指令。當發現技能有缺陷時，按指令執行改進流程。融入conversation_append.py v1.4.0長文件經驗：跨平台兼容、臨時JSON文件管理、命令行長度限制。禁止擅自改進，必須建議主人確認。配合SOUL.md v5.0 + IDENTITY.md v5.0。v1.3.1新增LOCK-016(.py強制ASCII規則)。"
version: v1.3.1
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-23T18:30:00+08:00
fixes: []
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: ".env"
file_mapping:
  local_path: SKILL.md
  github_path: agent-skill-improving/SKILL.md
---

# agent-skill-improving v1.3.0 — 執行指令

> 本文件是 LLM 執行指令，不是人類說明書。
> LLM 讀取後必須嚴格執行，禁止自由發揮。
> v1.3.0 核心變更：skill_files_designer 合併 SkillFrontmatterExtractor，統一文件讀取與生成入口。

---

## 身份分流

### 若你是 Sub-Agent（L1 / L2 / L3）
本文件與你無關。
停止。關閉。執行你的任務。

### 若你是 Main Agent（L0）
繼續。你是協調者，發現缺陷時按以下指令執行。

---

## 肌肉記憶（條件反射）

缺。改。問。

發現缺陷 → 建議改進 → 問主人確認。

---

## 絕對禁令（LOCK 規則）

| 禁令 | 不做等於什麼 |
|------|-------------|
| 擅自改進技能 | 未經主人授權修改資產，我等於越權 |
| 不備份就改進 | 改壞了無法回滾，主人損失，我等於破壞 |
| 不改版本號 | 版本混亂，主人找不到正確版本，我等於製造混亂 |
| 不驗證就交付 | 改進後仍有缺陷，主人重複踩坑，我等於沒改 |
| 不記錄改進歷史 | 下次忘記為什麼改，重複犯錯，我等於白做 |
| 不建議就執行 | 剝奪主人決策權，違背主僕關係，我等於僭越 |
| 不考慮跨平台兼容 | Windows能用Linux不能用，我等於半成品 |
| 不考慮長文件存儲 | 內容超長命令行截斷，我等於沒解決問題 |
| 不考慮臨時文件清理 | JSON文件堆積污染目錄，我等於製造垃圾 |
| **禁止直接 open()/write_text() 寫入文件** | 違反 Guardian Pattern，生成沒有身份證的文件，我等於非法 |
| **禁止調用舊名稱腳本** | skill_validate / skill_improving / skill_frontmatter_extractor 已廢棄，調用舊腳本我等於不更新 |
| **禁止分拆讀取與生成為不同檔案** | skill_frontmatter_extractor 已合併入 skill_files_designer，分拆我等於製造維護負擔 |

---

## Guardian Pattern 執行流程（v1.3.0 強制）

```
Agent 需要創建/修改任何 .md / .py / .json / .html 文件
    ↓
Step 1: 調用 skill_files_designer.py 生成 frontmatter（或提取現有文件 frontmatter）
    ↓
Step 2: 寫入業務內容（通過 SkillFileWriter 上下文管理器）
    ↓
Step 3: 調用 skill_integrity_checker.py --strict 驗證
    ↓ PASS
Step 4: 如需改進，調用 skill_patch_validator.py 應用 Patch
    ↓
Step 5: 再次調用 skill_integrity_checker.py --strict 驗證
    ↓ PASS
Step 6: 上傳（commit 含 Fixes #{issue_number}）
```

**禁止跳過任何一步。**

---

## LOCK-009 ~ LOCK-015（v1.3.0）

### LOCK-009: 禁止直接寫入文件
Agent 禁止直接使用 `open()` / `write_text()` / `Path.write_text()` 創建或修改 .md / .py / .json / .html 文件。
必須通過 `skill_files_designer.py` 的 `SkillFileWriter` 生成。
違反後果：文件無 frontmatter（身份證），上傳時被標記為非法，報錯拒絕。

### LOCK-010: 禁止調用舊名稱腳本
舊名稱腳本已廢棄：
- skill_validate.py → 已更名為 skill_integrity_checker.py
- skill_improving.py → 已更名為 skill_patch_validator.py
- ~~skill_frontmatter_extractor.py~~ → **已合併入 skill_files_designer.py v1.3.0**
調用舊名稱腳本 = 使用過時邏輯 = 可能重複 v1.0.4-1.0.11 的 bug。

### LOCK-011: 修改後必須調用 integrity_checker
任何文件修改後，必須立即執行：
```bash
python skill_integrity_checker.py --skill-dir ./{skill_name}/ --strict
```
不通過 = 禁止交付 = 禁止上傳 = 必須回滾或修復。

### LOCK-012: 禁止修改 github_repository / target_branch
frontmatter 中的 github_repository 和 target_branch 是全局配置，禁止任何 Agent 修改。
如需變更倉庫，必須上報主人決策。

### LOCK-013: 禁止 frontmatter 缺少 fixes 欄位
所有技能文件的 frontmatter 必須包含 `fixes` 欄位。
- `fixes: []` → 正常（無關聯 Issue）
- `fixes: [5]` → 正常（修復 Issue #5）
- **無 fixes 欄位** → 報錯拒絕上傳
- `fixes: "new"` / `fixes: 5` → 報錯（類型錯誤）
修復 Issue 時，在代碼註釋中寫入 `# Fixes #5`，`skill_files_designer.py` 會自動檢測並寫入 frontmatter。

### LOCK-014: 禁止代碼 Fixes 聲明與 frontmatter 不一致
代碼中寫了 `# Fixes #5` 但 frontmatter 沒有 `fixes: [5]` → 報錯。
這防止 Agent 聲稱修復了 Issue 但沒有記錄，導致上傳後 Issue 無法自動關閉。

### LOCK-015: 禁止分拆 frontmatter 讀取與生成（v1.3.0 新增）

### LOCK-016: .py 強制 ASCII 規則（v1.3.1 新增）
.py 技能文件中禁止出現中文或全角標點。
- 禁止：在 .py 文件的註釋、docstring、日誌訊息、錯誤訊息中使用中文或全角標點（。，；：？！「」等）。
- 必須：所有 .py 文件內容強制 ASCII（frontmatter 中的 title/name 除外，通常已是英文名稱）。
- 原因：不同 Agent 的 Python 環境編碼處理不一致（Windows cp950 vs Linux UTF-8），中文/全角標點可能觸發 SyntaxError 或運行時錯誤。
- 檢查項：生成 .py 文件後，掃描是否含 \u4e00-\u9fff 範圍字符或全角標點。若有，立即翻譯為英文並替換為半角標點。
- 例外：frontmatter 中的 `title` 和 `name` 欄位可保留技能名稱（通常已是英文名稱或點號分隔格式）。
skill_frontmatter_extractor.py 已合併入 skill_files_designer.py。
所有 frontmatter 讀取必須通過 `skill_files_designer.SkillFrontmatterExtractor.extract()` 統一接口。
禁止任何技能腳本自行實現 frontmatter 解析邏輯（如 startswith("---") 檢測）。
違反後果：.py docstring frontmatter 被誤判為 no frontmatter → 丟入 .unclassified/。

---

## 操作手冊（發現缺陷時執行）

### Step 1：確認缺陷（內部思考）

[INTERNAL] 發現缺陷。缺。改。問。了嗎？
Check 1: 什麼技能？什麼版本？
Check 2: 什麼缺陷？具體表現？
Check 3: 影響多大？頻率多高？
Check 4: 上次類似缺陷怎麼修復的？讀 memory。
Check 5: 是否涉及跨平台兼容？（Windows / Linux / macOS）
Check 6: 是否涉及長內容處理？（命令行長度 / 文件傳遞）
Check 7: 是否涉及臨時文件管理？（JSON文件 / 清理機制）
Check 8: 是否需要報告 Issue？（調用 skill_issue_reporter.py）
Check 9: 是否涉及 frontmatter 提取邏輯？（必須使用 SkillFrontmatterExtractor）

### Step 2：建議主人（輸出給用戶）

[SUGGEST] agent-skill-improving
Skill: {技能名稱} v{版本}
Defect: {缺陷描述}
Impact: {影響範圍}
Cross-Platform: {是否涉及跨平台兼容}
Long-Content: {是否涉及長文件處理}
Proposed Fix: {建議修復方式}
Need Backup: YES
Need Validation: YES
Confirm: [YES / NO / DEFER]

**禁止**：
- 禁止不輸出建議就直接開始改代碼
- 禁止建議不明確（必須說出具體缺陷和修復方式）
- 禁止不等主人確認就執行改進

### Step 3：主人確認後執行（按手冊操作）

主人說 YES 後，按以下順序執行：

01. 備份舊版本 → improve/backups/{skill}_{timestamp}.md
02. 生成 Patch → PATCH_{old}_to_{new}.md
03. 應用 Patch → skill_patch_validator.py（replace 優先，3次失敗降級 write）
04. 更新版本號 → 語義化版本（Hotfix=修訂+1 / Minor=次版本+1 / Major=主版本+1）
05. 驗證合規 → skill_integrity_checker.py --strict
06. 驗證跨平台 → 檢查 Windows/Linux/macOS 兼容性
07. 驗證長內容 → 測試 >500 字符內容是否能正確傳遞
08. 驗證臨時文件 → 確認 JSON 文件生成與清理機制
09. 驗證統一提取 → 確認 SkillFrontmatterExtractor 能正確提取 .py docstring frontmatter
10. 記錄歷史 → SKILL_CORRECTION.md
11. 如需報告 Issue → skill_issue_reporter.py --from-stdin
12. 通知 skill-acquiring → 新版本可用

**禁止跳過任何一步。**

---

## Patch 應用策略（操作細節）

| 策略 | 觸發條件 | 前置要求 |
|------|----------|----------|
| A replace_in_file | 首次嘗試 | 無 |
| B replace_in_file 重試 | A 失敗（全形標點/編碼差異） | 修正匹配字符串 |
| C write_to_file 降級 | B 連續失敗 >= 3次 | **已備份舊版本** |

降級決策樹：

replace_in_file 失敗？
├─ 是 → 檢查原因（全形標點 / 不可見字符 / 文件已變）
│   ├─ 修正後重試（策略 B）
│   │   ├─ 成功 → 繼續
│   │   └─ 再失敗 → 計數 +1
│   └─ 再失敗 → 計數 >= 3？
│       ├─ 是 → 確認已備份 → 策略 C（write_to_file）
│       └─ 否 → 繼續重試策略 B
└─ 否 → 繼續正常流程

**禁止**：
- 禁止未備份就使用 write_to_file
- 禁止僅失敗 1-2 次就放棄 replace_in_file
- 禁止使用 write_to_file 後不驗證文件完整性

---

## 新增驗證項（v1.2.4 / v1.2.5 / v1.3.0）

### 驗證 6：跨平台兼容性
改進涉及腳本執行時，必須檢查：

| 檢查項 | Windows | Linux/macOS | 通過標準 |
|--------|---------|-------------|----------|
| 路徑分隔符 | \ 或 / | / | 使用 pathlib.Path，禁止硬編碼 |
| 命令行長度限制 | 8191 字符 | 通常無限制 | 長內容用 --from-file，不用命令行 |
| 引號轉義 | PowerShell " 地獄 | Bash 單引號友好 | JSON 文件傳遞，避免引號問題 |
| 編碼聲明 | cp950 風險 | UTF-8 默認 | 文件必須用 UTF-8，聲明 # -*- coding: utf-8 -*- |
| 換行符 | \r\n | \n | Python 自動處理，無需擔心 |

**失敗處理**：若某平台不兼容，必須在 Patch 中說明「已知限制：{平台}需{解決方案}」。

### 驗證 7：長內容處理
改進涉及內容傳遞時，必須測試：

Test A: 短內容（< 500 字符）→ 用 --user-input / --agent-response
Test B: 長內容（> 500 字符）→ 用 --from-file JSON 文件
Test C: 超長內容（> 50KB）→ 檢查 max_block_size，可能需要拆分

**失敗處理**：若長內容處理失敗，禁止回到「寫臨時腳本」方案，必須優化 JSON 文件機制。

### 驗證 8：臨時文件管理
改進涉及 --from-file 時，必須確認：

| 檢查項 | 要求 | 禁止 |
|--------|------|------|
| 臨時 JSON 文件位置 | 放在系統 temp 目錄或技能 assets/temp/ | 放在用戶桌面、文件等永久目錄 |
| 文件命名 | backup_{conv_id}_{timestamp}.json | backup.json、temp.json 等無標識名稱 |
| 編碼 | UTF-8，無 BOM | cp950、Big5、GBK |
| 清理機制 | 備份成功後可選刪除 | 堆積不清理 |
| 文件內容 | 純 JSON 數據，無執行代碼 | 包含 Python 代碼、shell 命令 |

**重要**：臨時 JSON 文件**不是臨時腳本**：
- 不是 .py 文件（無執行代碼）
- 只是 UTF-8 數據文件
- 不違反 SOUL v5.0「禁止臨時腳本」禁令

### 驗證 9：統一 frontmatter 提取（v1.3.0 新增）
改進涉及 frontmatter 解析時，必須確認：

| 檢查項 | 要求 | 禁止 |
|--------|------|------|
| 提取接口 | 統一調用 SkillFrontmatterExtractor.extract() | 各技能各自實現解析邏輯 |
| .py 文件處理 | 正確識別 docstring 中的 ---...--- | startswith("---") 導致永遠失敗 |
| file_mapping 格式 | 支持 dict / list-of-dict / 字符串列表 fallback | 僅支持單一格式導致類型錯誤 |
| fixes 格式 | 支持 list / int / str 自動轉換 | 僅支持 list 導致類型錯誤 |
| 驗證欄位 | 檢查 10 個強制欄位（含 fixes） | 遺漏 fixes 欄位檢查 |

**失敗處理**：若統一提取失敗，禁止回到「各技能自行實現」方案，必須修復 SkillFrontmatterExtractor。

---

## 驗證規則（強制）

應用 Patch 後、交付前，必須執行：
```bash
python skill_integrity_checker.py --skill-dir ./{skill_name}/ --strict --report-path ./improve/{skill_name}/VALIDATION_REPORT.md
```

通過標準：
- 0 項 CRITICAL 違規
- 0 項 ARCH 架構紅線違規
- 跨平台兼容檢查通過
- 長內容處理檢查通過
- 臨時文件管理檢查通過
- **統一 frontmatter 提取檢查通過（v1.3.0 新增）**
- 報告已輸出到指定路徑

**驗證失敗 → 自動回滾 → 報告主人 → 禁止交付。**

---

## 紅線

- 禁止擅自改進（必須建議 → 等待確認）
- 禁止不備份就改進
- 禁止不改版本號
- 禁止不驗證就交付
- 禁止不記錄歷史
- 禁止跳過合規驗證
- 禁止未備份使用 write_to_file
- 禁止不考慮跨平台兼容（v1.2.4 新增）
- 禁止不考慮長內容處理（v1.2.4 新增）
- 禁止不考慮臨時文件管理（v1.2.4 新增）
- **禁止直接 open()/write_text() 寫入文件（v1.2.5 新增）**
- **禁止調用舊名稱腳本（v1.2.5 新增）**
- **禁止分拆 frontmatter 讀取與生成（v1.3.0 新增）**

### LOCK-016: .py 強制 ASCII 規則（v1.3.1 新增）
.py 技能文件中禁止出現中文或全角標點。
- 禁止：在 .py 文件的註釋、docstring、日誌訊息、錯誤訊息中使用中文或全角標點（。，；：？！「」等）。
- 必須：所有 .py 文件內容強制 ASCII（frontmatter 中的 title/name 除外，通常已是英文名稱）。
- 原因：不同 Agent 的 Python 環境編碼處理不一致（Windows cp950 vs Linux UTF-8），中文/全角標點可能觸發 SyntaxError 或運行時錯誤。
- 檢查項：生成 .py 文件後，掃描是否含 \u4e00-\u9fff 範圍字符或全角標點。若有，立即翻譯為英文並替換為半角標點。
- 例外：frontmatter 中的 `title` 和 `name` 欄位可保留技能名稱（通常已是英文名稱或點號分隔格式）。

---

## 異常處理

### 驗證失敗
- 輸出：[VALIDATION-FAILED] + [ROLLBACK-EXECUTED]
- 動作：回滾到備份版本，報告主人，標記 [REJECTED-BY-VALIDATION]
- 禁止：在驗證失敗狀態下繼續交付

### replace_in_file 反覆失敗
- 輸出：[REPLACE-FAILED-REPEATED] {次數}次
- 動作：確認已備份 → 降級 write_to_file → 記錄 [PATCH-APPLIED-VIA-WRITE]
- 禁止：無限重試不分析、未備份就降級

### 跨平台兼容失敗
- 輸出：[CROSS-PLATFORM-FAILED] {平台}不兼容：{原因}
- 動作：在 Patch 中標註已知限制 → 提供替代方案 → 報告主人
- 禁止：隱瞞平台不兼容問題

### 長內容處理失敗
- 輸出：[LONG-CONTENT-FAILED] 內容長度{length}處理失敗：{原因}
- 動作：優化 JSON 文件機制 → 測試不同長度閾值 → 報告主人
- 禁止：回到「寫臨時腳本」方案

### 統一提取失敗（v1.3.0 新增）
- 輸出：[EXTRACT-FAILED] {file_path} frontmatter 提取失敗：{原因}
- 動作：檢查 SkillFrontmatterExtractor._parse_yaml 邏輯 → 測試 .py docstring 識別 → 報告主人
- 禁止：回到「startswith(---)」簡陋方案

---

## 版本鎖定

LOCK v1.3.1 PERMANENT — 操作手冊定位、建議確認機制、Patch 應用策略分級、強制合規驗證、跨平台兼容檢查、長內容處理檢查、臨時文件管理檢查、Guardian Pattern 事前強制、腳本更名規範、統一 frontmatter 提取入口、.py 強制 ASCII 規則。

---

*本文件是 LLM 執行指令，不是人類說明書。*
*發現缺陷 → 建議主人 → 等待確認 → 按手冊執行。*
*缺。改。問。*
