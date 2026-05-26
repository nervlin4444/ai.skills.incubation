---
title: Agent Skill Acquiring - Human Readable Guide
name: agent-skill-acquiring
description: Human-readable explanation of skill profile management, multi-keyword search, directory scanning with security check, and markdown book display.
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
  local_path: "{baseDir}/README.md"
  github_path: "agent-skill-acquiring/README.md"
---

# Agent Skill Acquiring 解釋書

## 文件定位

| 檔案 | 讀者 | 用途 |
|------|------|------|
| SKILL.md（根目錄） | LLM + 主人掃描 | 執行指令集 |
| README.md（本檔） | 主人 | 設計原理與使用說明 |
| scripts/USAGE.md | 主人 | 腳本用法說明 |

---

## 為何需要這個技能？

當 Agent 需要查找技能時：
- 憑空創造技能，成功率低且容易引入漏洞
- 每次搜索都掃描目錄，速度極慢
- 不知道技能是否有身分（frontmatter），無法判斷可信度
- 沒有使用記錄，無法判斷哪些技能值得保留

Skill Acquiring v2.0.0 的設計目標是：**快速搜索（讀 JSON）、安全提取（掃目錄 + 檢查）、清晰展示（表格）。**

---

## 核心設計原理

### 1. 搜索與提取分離

| 操作 | 數據源 | 速度 | 用途 |
|------|--------|------|------|
| **Search** | skill_profile.json | 快（< 10ms） | 日常查找 |
| **Extract** | 目錄掃描 | 慢（視目錄大小） | 更新索引 |

**關鍵價值**：搜索不掃描目錄，只讀 JSON，確保即時響應。

### 2. 用戶優先排序

搜索結果排序：
1. user 目錄中的技能（優先）
2. external 目錄中的技能（次之）

### 3. 安全檢查內建於提取

提取時自動掃描 .py 文件中的危險模式：
- `os.system(`、`subprocess.call(`、`eval(`、`exec(`
- `rm -rf`、`shutil.rmtree`

發現時記錄警告，但不阻止提取（由主人決定是否使用）。

### 4. 使用記錄自動化

搜索時加 `--log` 參數，自動記錄命中採納到 usage_log.json：
- 時間戳、技能名稱、關鍵字、排名、是否採納

---

## 目錄結構

```
agent-skill-acquiring/
├── SKILL.md                    # LLM 執行指令
├── README.md                   # 本檔案：人類解釋書
├── config/
│   └── acquiring.config.json   # 跨平台配置
├── scripts/
│   ├── USAGE.md                # 腳本用法
│   ├── core_profile_io.py      # 統一讀寫 skill_profile.json
│   ├── core_logger.py          # 統一使用記錄
│   ├── skill_profile_search.py # 關鍵字搜索
│   ├── skill_profile_extract.py # 目錄掃描 + 提取
│   └── skill_profile_book.py   # 表格展示
└── data/
    └── skill_profile.json      # 技能索引（由 extract 生成）
    └── usage_log.json          # 使用記錄（由 search --log 生成）
```

---

## 常見誤解糾偏

### 誤解 1：「搜索應該直接掃描目錄」

**錯誤理解**：每次搜索都掃描 skills/ 目錄，確保最新。

**正確理解**：搜索只讀 skill_profile.json。目錄變化後需手動運行 extract 更新索引。

**後果**：每次搜索掃描目錄，100+ 技能時延遲數秒，Agent 響應極慢。

### 誤解 2：「extract 可以跳過安全檢查」

**錯誤理解**：安全檢查太嚴格，應該關閉。

**正確理解**：安全檢查只記錄警告，不阻止提取。主人可查看 warnings 後決定。

**後果**：關閉安全檢查後，惡意腳本（如含 `os.system("rm -rf /")`）被標記為正常技能。

### 誤解 3：「skill_profile.json 可以手動編輯」

**錯誤理解**：直接編輯 JSON 比運行 extract 更快。

**正確理解**：手動編輯容易格式錯誤（缺少引號、UTF-8 BOM）。應通過 extract 更新。

**後果**：格式錯誤的 JSON 導致搜索失敗，需刪除重建。

---

## 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|---------|
| v1.0.0 | 2026-05-01 | 初始版本，單一描述搜索 |
| v1.2.0 | 2026-05-10 | 加入安全掃描、使用記錄 |
| v2.0.0 | 2026-05-26 | 重大重構：多關鍵字搜索、JSON 索引、搜索提取分離、core 模組化 |

---

*最後更新：2026-05-26*
*本檔案為人類可讀解釋書，LLM 執行指令請參考 SKILL.md*