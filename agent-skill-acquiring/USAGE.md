---
title: Skill Profile Scripts Usage Guide
name: agent-skill-acquiring
description: Usage documentation for skill_profile_search.py, skill_profile_extract.py, and skill_profile_book.py.
version: v2.0.1
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T17:30:00+08:00
fixes: [37, 38, 39, 40]
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

## 常見誤解與設計決策說明

### 誤解 1：「安全檢查為什麼報告註釋中的危險模式？」

**觀察**：`_security_check()` 報告 `Found dangerous pattern 'os.system(' in xxx.py`，但實際上該模式只在註釋中出現。

**設計決策**：安全檢查使用 **字符串匹配**（string match），不是 **AST 解析**。

**原因**：
- AST 解析需要編譯 Python 代碼，對於語法不完整的臨時文件會失敗
- 字符串匹配速度快，不需要編譯環境
- 代價是會誤報註釋和字符串中的模式

**正確理解**：這是 **預期行為**，不是 bug。警告只記錄不阻止，主人可手動確認。

**不要這樣做**：
- ❌ 報告「安全檢查誤報」為 bug（如 Issue #38 最初描述）
- ❌ 要求改為 AST 解析（會引入編譯依賴和性能問題）

**應該這樣做**：
- ✅ 從 `dangerous_patterns` 中移除過於寬鬆的模式（如 `shutil.rmtree`，見 Issue #38 修復）
- ✅ 接受字符串匹配的局限性，將警告視為「需人工審核」標記

---

### 誤解 2：「為什麼新增技能後 search 找不到？」

**觀察**：git clone 了新技能到 `~/.workbuddy/skills/`，但 `search` 返回空。

**設計決策**：`search` **只讀** `skill_profile.json`，**不掃描**目錄。

**原因**：
- 搜索需要即時響應（< 10ms）
- 掃描 100+ 技能目錄需要數秒
- JSON 索引是搜索與提取分離架構的核心

**正確理解**：新增技能後 **必須先運行 extract**，更新索引後 search 才能找到。

**流程**：
```
git clone new-skill → extract → search (finds it)
```

**不要這樣做**：
- ❌ 認為 search 壞了，反覆調用 search
- ❌ 要求 search 自動掃描目錄（破壞性能設計）

**應該這樣做**：
- ✅ 運行 `python scripts/skill_profile_extract.py`
- ✅ 確認 `skill_profile.json` 已更新

---

### 誤解 3：「為什麼所有技能都是 user（沒有 external）？」

**觀察**：extract 後所有技能的 `source` 都是 `user`，沒有 `external` 或 `connector`。

**設計決策**：`source` 由 frontmatter 中的 `auth_config.provider` 決定，**不是**由目錄路徑決定。

**規則**：
- `auth_config.provider == "none"` → `source = "user"`
- `auth_config.provider == "github"` → `source = "github"`
- `auth_config.provider == "openclaw"` → `source = "openclaw"`

**正確理解**：如果所有技能的 `provider` 都是 `none`，那麼它們確實都是 user 技能。這是正確的。

**不要這樣做**：
- ❌ 認為 source 檢測壞了（如 Issue #39 最初描述）
- ❌ 要求按目錄路徑區分 source（與單一目錄佈局衝突）

**應該這樣做**：
- ✅ 檢查 frontmatter 中的 `auth_config.provider` 欄位
- ✅ 對於需要標記為 connector 的技能，確保 frontmatter 設置正確的 provider

---

### 誤解 4：「為什麼 alias 顯示 [PENDING-ALIAS]？」

**觀察**：Book 表格中某些技能的 Alias 欄位顯示 `[PENDING-ALIAS]`。

**設計決策**：Alias 必須由 **Agent 建議 + 主人確認**後寫入，不能自動生成。

**原因**：
- 自動生成中文別名可能不準確（如 `agent-skill-improving` → 「代理技能獲取」不夠精簡）
- 需要主人審核確保別名符合業務語境
- 批量確認效率最高（一次確認多個）

**正確理解**：`[PENDING-ALIAS]` 是 **正常標記**，表示該技能尚未分配中文別名。

**流程**：
```
Extract → [PENDING-ALIAS] 標記 → Agent 建議 → 主人批量確認 → 寫回 profile
```

**不要這樣做**：
- ❌ 認為這是錯誤或亂碼
- ❌ 手動直接編輯 JSON（可能格式錯誤）

**應該這樣做**：
- ✅ Agent 讀取 pending 列表，生成建議清單
- ✅ 主人回覆「確認」或「修改 xxx 為 yyy」
- ✅ Agent 寫回確認結果

---

### 誤解 5：「為什麼 Book 表格用 ``` 包裹後無法渲染？」

**觀察**：Agent 輸出 Book 表格時用 ` ```markdown ` 包裹，結果顯示為純文本。

**設計決策**：Book 輸出必須是 **裸 Markdown 表格**，禁止任何包裹。

**原因**：
- Markdown 表格在代碼塊中不會被渲染
- Agent 對話界面只渲染裸 Markdown 語法
- 包裹後主人看到 `| Alias | Summary |` 純文本，無法閱讀

**正確輸出**：
```markdown
| Alias | Skill Summary | Function Summary |
|-------|---------------|------------------|
| 技能改進器 | 技能改進執行 | 缺陷修復流程 |
```

**錯誤輸出**：
```markdown
```markdown
| Alias | Skill Summary | Function Summary |
|-------|---------------|------------------|
```
```

**不要這樣做**：
- ❌ 用 ` ``` `、` ```markdown `、` ```text ` 包裹表格
- ❌ 認為「保護格式」需要代碼塊

**應該這樣做**：
- ✅ 直接輸出 Markdown 表格語法
- ✅ 確保每行以 `|` 開頭

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
A：警告只記錄不阻止。由主人查看 warnings 後決定。注意：字符串匹配可能誤報註釋中的模式，這是預期行為。

**Q：如何修改技能的 alias？**
A：直接編輯 `data/skill_profile.json` 對應條目的 `alias` 欄位，或運行 extract 後由 Agent 建議批量確認。

**Q：Book 表格顯示為純文本怎麼辦？**
A：檢查 Agent 是否用 ` ``` ` 代碼塊包裹了表格。必須是裸 Markdown 語法。

**Q：為什麼有些技能顯示 [PENDING-ALIAS]？**
A：提取時 frontmatter 無 alias 欄位。Agent 需建議中文別名，主人確認後寫回。

**Q：為什麼新增技能後 search 找不到？**
A：search 只讀 JSON 不掃目錄。必須先運行 extract 更新 skill_profile.json。

**Q：為什麼所有技能都是 user（沒有 external）？**
A：source 由 auth_config.provider 決定。如果所有技能的 provider 都是 none，它們確實都是 user 技能。

---

*最後更新：2026-05-26*
*Fixes #37 #38 #39 #40*