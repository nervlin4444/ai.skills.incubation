---
title: "Contributing Guide - Standard Issue Report Format"
name: github-skill-organizer
description: "標準 Issue 報告格式。高度結構化模板，確保不同 LLM 都能輸出一致的內容。配合 Guardian Pattern 三層防禦架構使用。v1.2.5 統一 frontmatter 格式。"
version: "1.2.5"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T10:55:00+08:00"
fixes: []

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"

file_mapping:
  local_path: "references/CONTRIBUTING.md"
  github_path: "github-skill-organizer/references/CONTRIBUTING.md"
---

# Contributing Guide - 標準 Issue 報告格式 v1.2.5

> **核心原則：結構化模板，鎖定輸出。**
> 不同 LLM 使用此模板，必須輸出完全一致的格式和內容。
> 每個 Section 都有明確的填寫規則和最少字數要求。

---

## 一、Issue 創建規則

### 1.1 誰可以創建 Issue

| 創建者 | 條件 | 分類 |
|--------|------|------|
| Agent | 發現 [RUNTIME] 或 [AGENT-BUG] 問題，且 Self-Diagnosis 無法自行修復 | [RUNTIME] / [AGENT-BUG] |
| Agent | 發現 [FRAMEWORK] 問題，必須上報主人決策 | [FRAMEWORK] |
| 主人 | 主動發現問題，或審核 Agent 報告後創建 | 任何分類 |

### 1.2 創建前必須執行

```bash
# 1. 運行 Self-Diagnosis
python skill_integrity_checker.py（agent-skill-improving 技能）--skill-dir ./{skill_name}/ --strict

# 2. 確認問題類型
# [RUNTIME]: 運行時錯誤，Agent 可自行修復
# [AGENT-BUG]: Agent 違反已知規範，Agent 自行修復
# [FRAMEWORK]: 架構決策問題，必須上報主人

# 3. 收集上下文（見 Section 二）
```

---

## 二、標準 Issue 模板（結構化）

**⚠️ 強制規則：**
- 每個 Section 必須填寫，不能留空
- 每個 Section 最少 **50 個中文字符**（或 100 個英文字符）
- 使用提供的 JSON 結構填充，確保不同 LLM 輸出一致
- 禁止自由發揮，必須按照模板格式

---

### Section 1: 問題摘要（必填，最少 50 字）

**格式：**
```
[分類] 技能名 v版本 - 一句話描述問題
```

**範例：**
```
[RUNTIME] github-skill-organizer v1.0.11 - upload_skill() 對 config/sync.config.json 
驗證失敗，因為該文件缺少 frontmatter 導致上傳被拒絕
```

**檢查清單：**
- [ ] 包含 [FRAMEWORK] / [RUNTIME] / [AGENT-BUG] 標籤
- [ ] 包含技能名稱和版本號
- [ ] 包含問題現象（不是原因）
- [ ] 最少 50 個中文字符

---

### Section 2: 復現步驟（必填）

**格式：** 使用編號列表，每步包含「操作 + 參數 + 結果」

```
1. 操作: {具體操作，如 "執行 upload_skill()"}
   參數: {輸入的參數，如 "skill_name='github-skill-organizer', files=[...]"}
   結果: {觀察到的結果，如 "返回 status='rejected', 23/41 文件被拒絕"}

2. 操作: {下一步操作}
   參數: {參數}
   結果: {結果}
```

**範例：**
```
1. 操作: 執行 upload_skill() 上傳 github-skill-organizer
   參數: skill_name='github-skill-organizer', 
         files=skill_dir.rglob('*') 收集的所有文件
   結果: 返回 status='rejected'，41 個文件中 23 個被拒絕

2. 操作: 查看被拒絕的文件列表
   參數: 無
   結果: 被拒絕文件包括 .backups/*.bak(8個)、__pycache__/*.pyc(12個)、
         LICENSE(1個)、CHANGELOG.md(2個)、config/sync.config.json(1個)
```

**檢查清單：**
- [ ] 至少 2 個復現步驟
- [ ] 每步包含操作、參數、結果
- [ ] 參數具體（不是"一些文件"而是具體列表）

---

### Section 3: 根因分析（必填，最少 50 字）

**格式：**
```
位置: {文件路徑 + 行號範圍}
現象: {觀察到的代碼邏輯}
問題: {邏輯錯誤點}
後果: {導致的結果}
```

**範例：**
```
位置: sync_engine.py 第 632-649 行 (upload_skill() 方法)
現象: 代碼對所有 files 列表中的文件調用 _validate_github_repository()，
      該方法要求每個文件都有 github_repository 欄位
問題: config/sync.config.json 有 frontmatter 但沒有 github_repository 欄位，
      導致驗證失敗。但實際上只有 SKILL.md 需要 github_repository 來決定上傳目標
後果: 41 個文件中 23 個被拒絕，只有 18 個通過驗證，上傳失敗
```

**檢查清單：**
- [ ] 包含具體文件位置（路徑 + 行號）
- [ ] 包含代碼邏輯描述
- [ ] 包含問題點分析
- [ ] 包含後果說明
- [ ] 最少 50 個中文字符

---

### Section 4: 已嘗試的修復（選填，如無則寫"無"）

**格式：**
```
嘗試 1:
  方法: {嘗試的修復方法}
  結果: {成功/失敗，原因}

嘗試 2:
  方法: {方法}
  結果: {結果}
```

**範例：**
```
嘗試 1:
  方法: 修改 upload_skill()，跳過沒有 frontmatter 的文件
  結果: 失敗。這違反了身份證制度，所有文件必須有 frontmatter

嘗試 2:
  方法: 給 config/sync.config.json 添加 frontmatter
  結果: 成功。但發現這是更廣泛的問題，需要統一規範
```

---

### Section 5: 建議修復方案（必填，最少 50 字）

**格式：**
```
方案: {簡要描述}
影響範圍: {影響的文件和功能}
風險: {低/中/高，原因}
預期結果: {修復後的預期行為}
```

**範例：**
```
方案: 修改 upload_skill() 的驗證邏輯，只驗證 frontmatter 存在性
      （不是空 dict {}），不強制檢查 github_repository。
      github_repository 只從 SKILL.md 讀取。
影響範圍: sync_engine.py 的 upload_skill() 方法
風險: 低。因為 SKILL.md 仍然會驗證 github_repository，上傳目標不會錯誤
預期結果: 所有有 frontmatter 的文件都能通過驗證，只有完全沒有 frontmatter
      的文件才會被拒絕
```

**檢查清單：**
- [ ] 包含具體方案（不是"修復一下"）
- [ ] 包含影響範圍
- [ ] 包含風險評估
- [ ] 包含預期結果
- [ ] 最少 50 個中文字符

---

### Section 6: 分類（必填，只能選一個）

**格式：**
```
- [x] [FRAMEWORK] 框架問題（需要主人決策）
- [ ] [RUNTIME] 運行時問題（Agent 可自行處理）
- [ ] [AGENT-BUG] Agent 自身錯誤（違反已知規範）
```

**分類標準：**

| 分類 | 定義 | 處理方式 |
|------|------|---------|
| [FRAMEWORK] | 涉及架構決策的問題：是否需要新增文件類型？是否需要修改 .releaserc.json？是否需要調整身份證制度？ | 上報主人，Agent 不能自行決定 |
| [RUNTIME] | 運行時邏輯錯誤：方法在特定條件下返回錯誤、路徑處理邊緣案例、API 調用失敗 | Agent 自行修復，創建 Issue，Commit 包含 Fixes #N |
| [AGENT-BUG] | Agent 違反已知規範：生成了沒有 frontmatter 的文件、使用了錯誤命名、沒有執行 Self-Diagnosis | Agent 自行修復，不上報 Issue，記錄到本地日誌 |

**檢查清單：**
- [ ] 只能選一個（打勾其他兩個必須是空白）
- [ ] 選擇符合分類標準

---

### Section 7: 驗證結果（修復後填寫）

**格式：**
```
修復版本: {版本號}
測試用例: {測試的操作和參數}
結果: {PASS / FAIL}
證據: {輸出截圖或日誌片段}
```

**範例：**
```
修復版本: v1.0.12
測試用例: 執行 upload_skill() 上傳 github-skill-organizer，
         files 包含 config/sync.config.json（已有 frontmatter）
結果: PASS
證據: [UPLOAD] Excluded 0 files
      [UPLOAD] Status: uploaded
      [UPLOAD] Commit: [PATCH] github-skill-organizer v1.0.12 ...
```

---

## 三、JSON 結構化模板（供 LLM 直接填充）

為確保不同 LLM 輸出完全一致，提供 JSON 模板：

```json
{
  "issue_template_version": "v1.2.5",
  "classification": "[RUNTIME]",
  "section_1_summary": {
    "skill_name": "github-skill-organizer",
    "version": "v1.0.11",
    "description": "upload_skill() 對 config/sync.config.json 驗證失敗，因為該文件缺少 frontmatter 導致上傳被拒絕"
  },
  "section_2_reproduction": [
    {
      "step": 1,
      "action": "執行 upload_skill() 上傳 github-skill-organizer",
      "parameters": "skill_name='github-skill-organizer', files=skill_dir.rglob('*') 收集的所有文件",
      "result": "返回 status='rejected'，41 個文件中 23 個被拒絕"
    },
    {
      "step": 2,
      "action": "查看被拒絕的文件列表",
      "parameters": "無",
      "result": "被拒絕文件包括 .backups/*.bak(8個)、__pycache__/*.pyc(12個)、LICENSE(1個)、CHANGELOG.md(2個)、config/sync.config.json(1個)"
    }
  ],
  "section_3_root_cause": {
    "location": "sync_engine.py 第 632-649 行 (upload_skill() 方法)",
    "phenomenon": "代碼對所有 files 列表中的文件調用 _validate_github_repository()，該方法要求每個文件都有 github_repository 欄位",
    "problem": "config/sync.config.json 有 frontmatter 但沒有 github_repository 欄位，導致驗證失敗。但實際上只有 SKILL.md 需要 github_repository 來決定上傳目標",
    "consequence": "41 個文件中 23 個被拒絕，只有 18 個通過驗證，上傳失敗"
  },
  "section_4_attempted_fixes": [
    {
      "method": "修改 upload_skill()，跳過沒有 frontmatter 的文件",
      "result": "失敗。這違反了身份證制度，所有文件必須有 frontmatter"
    }
  ],
  "section_5_proposed_fix": {
    "solution": "修改 upload_skill() 的驗證邏輯，只驗證 frontmatter 存在性（不是空 dict {}），不強制檢查 github_repository。github_repository 只從 SKILL.md 讀取",
    "impact_scope": "sync_engine.py 的 upload_skill() 方法",
    "risk": "低。因為 SKILL.md 仍然會驗證 github_repository，上傳目標不會錯誤",
    "expected_result": "所有有 frontmatter 的文件都能通過驗證，只有完全沒有 frontmatter 的文件才會被拒絕"
  },
  "section_7_verification": {
    "fix_version": "v1.0.12",
    "test_case": "執行 upload_skill() 上傳 github-skill-organizer，files 包含 config/sync.config.json（已有 frontmatter）",
    "result": "PASS",
    "evidence": "[UPLOAD] Excluded 0 files; [UPLOAD] Status: uploaded; [UPLOAD] Commit: [PATCH] github-skill-organizer v1.0.12 ..."
  }
}
```

**使用規則：**
1. LLM 先填充 JSON 模板
2. 然後將 JSON 轉換為 Markdown 格式（上面的 Section 格式）
3. 確保 Markdown 輸出與 JSON 內容完全一致

---

## 四、Issue 標題格式

**標準格式：**
```
[分類] 技能名 v版本 - 簡短描述（最多 80 字符）
```

**範例：**
```
[RUNTIME] github-skill-organizer v1.0.11 - upload_skill 驗證失敗 23/41 文件被拒絕
[FRAMEWORK] agent-skill-improving v1.2.4 - 是否需要新增 .yaml 文件類型的 frontmatter 規範
[AGENT-BUG] chrome-playwright-connector v1.0.0 - Agent 生成文件缺少 frontmatter
```

**禁止：**
- 標題超過 80 字符
- 標題不含分類標籤
- 標題不含技能名稱和版本
- 使用模糊描述（如"有問題"、"出錯了"）

---

## 五、標籤規範

創建 Issue 時必須添加以下標籤：

| 標籤 | 用途 | 必填 |
|------|------|------|
| `bug` | 標記為 bug | 是 |
| `skill-{name}` | 標記受影響的技能 | 是 |
| `framework` | [FRAMEWORK] 問題 | 條件 |
| `runtime` | [RUNTIME] 問題 | 條件 |
| `agent-bug` | [AGENT-BUG] 問題 | 條件 |
| `v{x.y.z}` | 版本號 | 是 |
| `critical` | 嚴重程度 | 可選 |
| `pending-owner` | 等待主人決策 | [FRAMEWORK] 必填 |

---

## 六、閉環規範

### 6.1 自動關閉

Commit message 必須包含以下關鍵詞之一：
```
Fixes #{issue_number}
Closes #{issue_number}
Resolves #{issue_number}
```

**範例：**
```
fix: resolve upload_skill frontmatter validation

- 修改驗證邏輯，只檢查 frontmatter 存在性
- 不強制檢查 github_repository（只從 SKILL.md 讀取）

Fixes #3
```

### 6.2 通過 fixes 欄位自動關閉（v1.2.5 新增）

修復 Issue 時，在文件 frontmatter 中加入 fixes 欄位：
```yaml
fixes: [3]   # 修復 Issue #3
```

上傳腳本自動讀取 fixes，在 commit message 中附加 Fixes #3，GitHub 自動關閉 Issue。

### 6.3 驗證後關閉

Issue 創建者（Agent 或主人）在修復後必須：
1. 本地執行驗證（skill_integrity_checker.py --strict）
2. 在 Issue 評論區填寫 Section 7（驗證結果）
3. 確認無誤後關閉 Issue

---

## 七、違規處理

如果 Issue 不符合本格式：

| 違規類型 | 處理方式 |
|---------|---------|
| 缺少必填 Section | 標記 `incomplete`，要求補充 |
| Section 字數不足 50 字 | 標記 `needs-detail`，要求擴充 |
| 分類錯誤（如 [FRAMEWORK] 標為 [RUNTIME]）| 標記 `wrong-classification`，要求重新分類 |
| 標題超過 80 字符 | 標記 `title-too-long`，要求縮短 |
| 缺少標籤 | 標記 `missing-labels`，要求添加 |

---

## 八、版本更新記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| v1.0.0 | 2026-05-11 | 初始 Issue 報告模板 |
| v1.2.5 | 2026-05-22 | 結構化重構：新增 JSON 模板、明確 Section 字數要求、新增分類標準、新增標籤規範、新增閉環規範、新增違規處理 |
| v1.2.5 | 2026-05-23 | 統一 frontmatter 格式（移除 v 前綴、新增 fixes 欄位、單一 file_mapping） |
