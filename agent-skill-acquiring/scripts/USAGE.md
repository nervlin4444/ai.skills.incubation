---
title: Skill Profile Scripts Usage Guide
name: agent-skill-acquiring
description: Usage documentation for skill_profile_search.py, skill_profile_extract.py, and skill_profile_book.py.
version: v2.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T12:10:00+08:00
fixes: []
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

> 版本：v2.0.0（對齊 agent-skill-acquiring v2.0.0）
> 位置：`scripts/USAGE.md`

---

## 版本對齊表

| 文件 | 版本 | 用途 |
|------|------|------|
| skill_profile_search.py | v2.0.0 | 多關鍵字搜索 |
| skill_profile_extract.py | v2.0.0 | 目錄掃描 + 提取 + 安全檢查 |
| skill_profile_book.py | v2.0.0 | Markdown 表格展示 |
| core_profile_io.py | v2.0.0 | 統一讀寫 skill_profile.json |
| core_logger.py | v2.0.0 | 統一使用記錄 |
| SKILL.md | v2.0.0 | LLM 執行指令集 |
| README.md | v2.0.0 | 人類可讀解釋書 |
| USAGE.md | v2.0.0 | 本文件：腳本用法說明 |

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

**Python API：**
```python
from skill_profile_extract import extract

profile = extract()  # 全部
profile = extract(["agent-skill-improving"])  # 指定
```

### 3. 展示技能表格

```bash
# 默認 Markdown 表格
python scripts/skill_profile_book.py --page skills

# JSON 輸出
python scripts/skill_profile_book.py --page skills --format json
```

**Python API：**
```python
from skill_profile_book import book

print(book("skills"))
```

---

## 配置文件

`config/acquiring.config.json` 定義掃描路徑和工作站默認值：

```json
{
  "workstation_defaults": {
    "macos": {
      "skills_folder": "~/.workbuddy/skills",
      "data_folder": "~/.workbuddy/skills/agent-skill-acquiring/data"
    }
  },
  "scan_paths": {
    "user": ["{skills_folder}/user"],
    "external": ["{skills_folder}/vendor", "{skills_folder}/shared"]
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

**Q：如何修改技能的 alias 或 summary？**
A：直接編輯 `data/skill_profile.json` 對應條目，或刪除後重新運行 extract（由 LLM 重新生成）。

---

*最後更新：2026-05-26*