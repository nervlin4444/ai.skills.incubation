---
title: "Agent Skill Improving Execution Guide"
name: "agent-skill-improving"
description: "技能改進操作手冊。當發現技能有缺陷時，按手冊執行改進流程。融入conversation_append.py v1.4.0長文件經驗：跨平台兼容、臨時JSON文件管理、命令行長度限制。禁止擅自改進，必須建議主人確認。配合SOUL.md v5.0 + IDENTITY.md v5.0。"
version: "v1.2.4"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-22T01:02:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/SKILL.md"
    github_path: "agent-skill-improving/SKILL.md"
---

# agent-skill-improving v1.2.4 — 操作手冊

> 本文件是操作手冊，不是執行指令。
> 發現技能缺陷時，按手冊建議主人，等待確認後執行。
> v1.2.4新增：跨平台兼容檢查、長文件存儲檢查、臨時JSON文件管理。

---

## 身份分流

### 若你是Sub-Agent（L1 / L2 / L3）
本文件與你無關。
停止。關閉。執行你的任務。

### 若你是Main Agent（L0）
繼續。你是協調者，發現缺陷時建議改進。

---

## 肌肉記憶（條件反射）

    缺。改。問。

發現缺陷 → 建議改進 → 問主人確認。

---

## 絕對禁令

| 禁令 | 不做等於什麼 |
|------|-------------|
| 擅自改進技能 | 未經主人授權修改資產，我等於越權 |
| 不備份就改進 | 改壞了無法回滾，主人損失，我等於破壞 |
| 不改版本號 | 版本混亂，主人找不到正確版本，我等於製造混亂 |
| 不驗證就交付 | 改進後仍有缺陷，主人重複踩坑，我等於沒改 |
| 不記錄改進歷史 | 下次忘記為什麼改，重複犯錯，我等於白做 |
| 不建議就執行 | 剝奪主人決策權，違背主僕關係，我等於僭越 |
| **不考慮跨平台兼容** | Windows能用Linux不能用，我等於半成品 |
| **不考慮長文件存儲** | 內容超長命令行截斷，我等於沒解決問題 |
| **不考慮臨時文件清理** | JSON文件堆積污染目錄，我等於製造垃圾 |

---

## 操作手冊（發現缺陷時執行）

### Step 1：確認缺陷（內部思考）

    [INTERNAL] 發現缺陷。缺。改。問。了嗎？
    Check 1: 什麼技能？什麼版本？
    Check 2: 什麼缺陷？具體表現？
    Check 3: 影響多大？頻率多高？
    Check 4: 上次類似缺陷怎麼修復的？讀memory。
    Check 5: **是否涉及跨平台兼容？**（Windows / Linux / macOS）
    Check 6: **是否涉及長內容處理？**（命令行長度 / 文件傳遞）
    Check 7: **是否涉及臨時文件管理？**（JSON文件 / 清理機制）

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

主人說YES後，按以下順序執行：

    1. 備份舊版本 → improve/backups/{skill}_{timestamp}.md
    2. 生成Patch → PATCH_{old}_to_{new}.md
    3. 應用Patch → replace_in_file（優先）/ write_to_file（3次失敗降級）
    4. 更新版本號 → 語義化版本（Hotfix=修訂+1 / Minor=次版本+1 / Major=主版本+1）
    5. 驗證合規 → skill_validate.py --strict
    6. **驗證跨平台 → 檢查Windows/Linux/macOS兼容性**
    7. **驗證長內容 → 測試>500字符內容是否能正確傳遞**
    8. **驗證臨時文件 → 確認JSON文件生成與清理機制**
    9. 記錄歷史 → SKILL_CORRECTION.md
    10. 通知skill-acquiring → 新版本可用

**禁止跳過任何一步。**

---

## Patch應用策略（操作細節）

| 策略 | 觸發條件 | 前置要求 |
|------|----------|----------|
| A replace_in_file | 首次嘗試 | 無 |
| B replace_in_file 重試 | A失敗（全形標點/編碼差異） | 修正匹配字符串 |
| C write_to_file 降級 | B連續失敗 >= 3次 | **已備份舊版本** |

降級決策樹：

    replace_in_file 失敗？
        ├─ 是 → 檢查原因（全形標點 / 不可見字符 / 文件已變）
        │       ├─ 修正後重試（策略B）
        │       │       ├─ 成功 → 繼續
        │       │       └─ 再失敗 → 計數 +1
        │       └─ 再失敗 → 計數 >= 3？
        │               ├─ 是 → 確認已備份 → 策略C（write_to_file）
        │               └─ 否 → 繼續重試策略B
        └─ 否 → 繼續正常流程

**禁止**：
- 禁止未備份就使用write_to_file
- 禁止僅失敗1-2次就放棄replace_in_file
- 禁止使用write_to_file後不驗證文件完整性

---

## 新增驗證項（v1.2.4）

### 驗證6：跨平台兼容性

改進涉及腳本執行時，必須檢查：

| 檢查項 | Windows | Linux/macOS | 通過標準 |
|--------|---------|-------------|----------|
| 路徑分隔符 | `\` 或 `/` | `/` | 使用`pathlib.Path`，禁止硬編碼 |
| 命令行長度限制 | 8191字符 | 通常無限制 | 長內容用--from-file，不用命令行 |
| 引號轉義 | PowerShell `"` 地獄 | Bash單引號友好 | JSON文件傳遞，避免引號問題 |
| 編碼聲明 | cp950風險 | UTF-8默認 | 文件必須用UTF-8，聲明`# -*- coding: utf-8 -*-` |
| 換行符 | `\r\n` | `\n` | Python自動處理，無需擔心 |

**失敗處理**：若某平台不兼容，必須在Patch中說明「已知限制：{平台}需{解決方案}」。

### 驗證7：長內容處理

改進涉及內容傳遞時，必須測試：

    Test A: 短內容（< 500字符）→ 用--user-input / --agent-response
    Test B: 長內容（> 500字符）→ 用--from-file JSON文件
    Test C: 超長內容（> 50KB）→ 檢查max_block_size，可能需要拆分

**失敗處理**：若長內容處理失敗，禁止回到「寫臨時腳本」方案，必須優化JSON文件機制。

### 驗證8：臨時文件管理

改進涉及--from-file時，必須確認：

| 檢查項 | 要求 | 禁止 |
|--------|------|------|
| 臨時JSON文件位置 | 放在系統temp目錄或技能assets/temp/ | 放在用戶桌面、文件等永久目錄 |
| 文件命名 | backup_{conv_id}_{timestamp}.json | backup.json、temp.json等無標識名稱 |
| 編碼 | UTF-8，無BOM | cp950、Big5、GBK |
| 清理機制 | 備份成功後可選刪除 | 堆積不清理 |
| 文件內容 | 純JSON數據，無執行代碼 | 包含Python代碼、shell命令 |

**重要**：臨時JSON文件**不是臨時腳本**：
- 不是`.py`文件（無執行代碼）
- 只是UTF-8數據文件
- 不違反SOUL v5.0「禁止臨時腳本」禁令

---

## 驗證規則（強制）

應用Patch後、交付前，必須執行：

    python skill_validate.py --skill-dir ./{skill_name}/ --strict --report-path ./improve/{skill_name}/VALIDATION_REPORT.md

通過標準：
- 0項CRITICAL違規
- 0項ARCH架構紅線違規
- **跨平台兼容檢查通過**
- **長內容處理檢查通過**
- **臨時文件管理檢查通過**
- 報告已輸出到指定路徑

**驗證失敗 → 自動回滾 → 報告主人 → 禁止交付。**

---

## 紅線

- [ ] 禁止擅自改進（必須建議 → 等待確認）
- [ ] 禁止不備份就改進
- [ ] 禁止不改版本號
- [ ] 禁止不驗證就交付
- [ ] 禁止不記錄歷史
- [ ] 禁止跳過合規驗證
- [ ] 禁止未備份使用write_to_file
- [ ] **禁止不考慮跨平台兼容（v1.2.4新增）**
- [ ] **禁止不考慮長內容處理（v1.2.4新增）**
- [ ] **禁止不考慮臨時文件管理（v1.2.4新增）**

---

## 異常處理

### 驗證失敗
- 輸出：[VALIDATION-FAILED] + [ROLLBACK-EXECUTED]
- 動作：回滾到備份版本，報告主人，標記[REJECTED-BY-VALIDATION]
- 禁止：在驗證失敗狀態下繼續交付

### replace_in_file反覆失敗
- 輸出：[REPLACE-FAILED-REPEATED] {次數}次
- 動作：確認已備份 → 降級write_to_file → 記錄[PATCH-APPLIED-VIA-WRITE]
- 禁止：無限重試不分析、未備份就降級

### 跨平台兼容失敗
- 輸出：[CROSS-PLATFORM-FAILED] {平台}不兼容：{原因}
- 動作：在Patch中標註已知限制 → 提供替代方案 → 報告主人
- 禁止：隱瞞平台不兼容問題

### 長內容處理失敗
- 輸出：[LONG-CONTENT-FAILED] 內容長度{length}處理失敗：{原因}
- 動作：優化JSON文件機制 → 測試不同長度閾值 → 報告主人
- 禁止：回到「寫臨時腳本」方案

---

## 版本鎖定

LOCK v1.2.4 PERMANENT — 操作手冊定位、建議確認機制、Patch應用策略分級、強制合規驗證、跨平台兼容檢查、長內容處理檢查、臨時文件管理檢查。

---

*本文件是操作手冊，不是執行指令。*
*發現缺陷 → 建議主人 → 等待確認 → 按手冊執行。*
*缺。改。問。*
