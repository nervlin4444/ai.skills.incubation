---
title: Skill Profile Scripts Usage Guide
name: agent-skill-acquiring
description: Usage documentation for skill_profile_search.py, skill_profile_extract.py, and skill_profile_book.py.
version: v2.0.1
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T16:10:00+08:00
fixes: [37, 39]
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/scripts/USAGE.md"
  github_path: "agent-skill-acquiring/scripts/USAGE.md"
---

# USAGE.md — Skill Profile Scripts 使用說明

> 版本：v2.0.1（對齊 agent-skill-acquiring v2.0.1）
> 位置：`scripts/USAGE.md`

---

## 版本對齊表

| 文件 | 版本 | 用途 |
|------|------|------|
| skill_profile_search.py | v2.0.1 | 多關鍵字搜索 |
| skill_profile_extract.py | v2.0.1 | 目錄掃描 + 提取 + 安全檢查 + alias 標記 |
| skill_profile_book.py | v2.0.1 | Markdown 表格展示（3 欄 + 雙排序） |
| core_profile_io.py | v2.0.1 | 統一讀寫 skill_profile.json |
| core_logger.py | v2.0.1 | 統一使用記錄 |
| SKILL.md | v2.0.1 | LLM 執行指令集 |
| README.md | v2.0.1 | 人類可讀解釋書 |
| USAGE.md | v2.0.1 | 本文件：腳本用法說明 |

---

## 快速開始

### 1. 搜索技能

```bash
# 基本搜索
python scripts/skill_profile_search.py web crawl

# 搜索並記錄採納
python scripts/skill_profile_search.py web crawl --log

# JSON 輸出
python scripts/skill_profile_search.py web crawl --format json

# 最多 3 個結果
python scripts/skill_profile_search.py web crawl --max-results 3
```

**Python API：**
```python
from skill_profile_search import search

results = search(["web", "crawl"], max_results=5)
for name, meta, score in results:
    print(f"{name}: {score}")
```

### 2. 提取技能元數據

```bash
# 掃描全部目錄
python scripts/skill_profile_extract.py

# 只提取指定技能
python scripts/skill_profile_extract.py --names agent-skill-improving github-skill-organizer

# 預覽不保存
python scripts/skill_profile_extract.py --dry-run
```

**輸出示例：**
```
[OK] Profile updated: 27 skills total (15 user, 12 external)
[PENDING-ALIAS] 8 skills need alias assignment. Agent should review and suggest Chinese aliases for batch confirmation.
```

**Python API：**
```python
from skill_profile_extract import extract

profile = extract()  # 全部
profile = extract(["agent-skill-improving"])  # 指定
```

### 3. Alias 批量確認流程

提取後若有 `[PENDING-ALIAS]`，Agent 執行以下步驟：

1. **讀取** skill_profile.json，找出 alias = `[PENDING-ALIAS]` 的技能
2. **組合** skill_name + function_summary 生成建議
3. **精簡**為 2-4 個中文字符的簡短名稱
4. **列出**建議清單給主人確認
5. **寫回**確認後的 alias 到 skill_profile.json

**示例建議清單：**
```
| Skill Name | Suggested Alias | Current |
|------------|-----------------|---------|
| agent-skill-improving | 技能改進器 | [PENDING-ALIAS] |
| github-skill-organizer | GitHub整理 | [PENDING-ALIAS] |
| jira-restful-api-connector | Jira連接器 | [PENDING-ALIAS] |
```

主人回覆「確認」後，Agent 寫回 profile。

### 4. 展示技能表格

```bash
# 默認 Markdown 表格（裸輸出，不加 ```）
python scripts/skill_profile_book.py --page skills

# JSON 輸出
python scripts/skill_profile_book.py --page skills --format json
```

**輸出示例（裸 Markdown）：**
```markdown
| Alias | Skill Summary | Function Summary |
|-------|---------------|------------------|
| 技能改進器 | 技能改進執行 | 缺陷修復流程 |
| GitHub整理 | GitHub技能管理 | 倉庫同步上傳 |
| Jira連接器 | Jira API操作 | 工單查詢更新 |
```

**絕對禁止：** 用 ` ``` ` 代碼塊包裹上述表格。

**Python API：**
```python
from skill_profile_book import book

print(book("skills"))  # 裸 Markdown 表格
```

---

## 配置文件

`config/acquiring.config.json` 定義掃描路徑和工作站默認值（單一目錄佈局）：

```json
{
  "workstation_defaults": {
    "macos": {
      "skills_folder": "~/.workbuddy/skills",
      "data_folder": "~/.workbuddy/skills/agent-skill-acquiring/data"
    }
  },
  "scan_paths": {
    "user": ["{skills_folder}"],
    "external": []
  }
}
```

---

## 輸出文件規範

| 文件類型 | 命名格式 | 存放位置 | 說明 |
|---------|---------|---------|------|
| 技能索引 | `skill_profile.json` | `data/` | 由 extract 生成，搜索讀取 |
| 使用記錄 | `usage_log.json` | `data/` | 由 search --log 生成 |
| 配置文件 | `acquiring.config.json` | `config/` | 跨平台路徑配置 |

---

## 常見問題

**Q：搜索不到技能時怎麼辦？**
A：先運行 `python scripts/skill_profile_extract.py` 更新索引。如果仍然沒有，檢查 config 中的掃描路徑是否正確。

**Q：安全檢查警告的技能能否使用？**
A：警告只記錄不阻止。由主人查看 warnings 後決定。

**Q：如何修改技能的 alias？**
A：直接編輯 `data/skill_profile.json` 對應條目的 `alias` 欄位，或運行 extract 後由 Agent 建議批量確認。

**Q：Book 表格顯示為純文本怎麼辦？**
A：檢查 Agent 是否用 ` ``` ` 代碼塊包裹了表格。必須是裸 Markdown 語法。

**Q：為什麼有些技能顯示 [PENDING-ALIAS]？**
A：提取時 frontmatter 無 alias 欄位。Agent 需建議中文別名，主人確認後寫回。

---

*最後更新：2026-05-26*
*Fixes #37 #39*