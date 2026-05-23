---
title: "GitHub Skill Organizer - Usage Guide"
name: github-skill-organizer
description: "Human-readable usage guide for github-skill-organizer. v1.0.15 fixes Issue #16 - corrects all change_classifier API examples from classify_change() to ChangeClassifier().classify(). Retains v1.0.14 three-step workflow documentation."
version: "1.0.15"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T13:45:00+08:00"
fixes: [16]
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "scripts/USAGE.md"
  github_path: "github-skill-organizer/scripts/USAGE.md"
---

# github-skill-organizer Usage Guide

版本：v1.0.15
更新時間：2026-05-23 13:45:00
核心變更：修正 change_classifier API 文檔（Issue #16），所有示例改用 ChangeClassifier().classify()。保留 classify_change() 向後兼容包裝函數。

---

## 目錄

1. [快速開始](#1-快速開始)
2. [強制三步上傳流程](#2-強制三步上傳流程)
3. [腳本說明](#3-腳本說明)
4. [常見問題](#4-常見問題)
5. [版本歷史](#5-版本歷史)

---

## 1. 快速開始

### 1.1 環境配置

在 `~/.workbuddy/skills/github-skill-organizer/.env` 創建：

    GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    GITHUB_OWNER=nervlin4444
    GITHUB_REPO=ai.skills.incubation

### 1.2 安裝依賴

    cd ~/.workbuddy/skills/github-skill-organizer
    pip install -r requirements.txt  # 如果有

---

## 2. 強制三步上傳流程

⚠️ **重要**：上傳技能到 GitHub **必須** 嚴格遵循以下三步順序。跳過任何一步都會導致錯誤。

### Step 1: 比較本地與 GitHub（compare_skill）

```python
from scripts.sync_engine import SyncEngine

engine = SyncEngine()
skill_name = "my-skill"
local_dir = "~/.workbuddy/skills/my-skill"

# 比較本地與 GitHub
comparison = engine.compare_skill(skill_name, local_dir)

# 檢查結果
if comparison["action"] == "identical":
    print("本地與 GitHub 完全一致，無需上傳")
    exit(0)
elif comparison["action"] == "github_ahead":
    print("GitHub 版本較新，建議先執行 pull")
    exit(1)

print(f"Action: {comparison['action']}")
print(f"Modified: {comparison['modified_files']}")
print(f"New files: {comparison['local_only_files']}")
```

**注意**：`compare_skill()` 返回值 **缺少** `approval_required`、`bump_type`、`new_version`、`reason`。不能直接傳入 `upload_skill()`。

### Step 2: 分類變更（change_classifier - 必須步驟）

```python
from pathlib import Path
from scripts.change_classifier import ChangeClassifier

# 必須調用：產生完整的 classification
classifier = ChangeClassifier()
changed_files = comparison.get("modified_files", []) + comparison.get("local_only_files", [])
skill_name = Path(comparison.get("local_dir", ".")).name
classification = classifier.classify(skill_name, changed_files)

print(f"Approval required: {classification['approval_required']}")
print(f"Bump type: {classification['bump_type']}")
print(f"New version: {classification['new_version']}")
print(f"Reason: {classification['reason']}")

# 如果需要主人確認
if classification["approval_required"]:
    print("⚠️ 此上傳需要主人確認。請審核變更後手動設置 approval_required=False")
    exit(1)
```

**向後兼容包裝函數**（v1.0.15 Issue #16 新增，等同上述四行）：

```python
from scripts.change_classifier import classify_change

# 一行搞定，自動提取 skill_name 和 changed_files
classification = classify_change(comparison)
```

**為什麼必須調用 change_classifier？**

| 欄位 | compare_skill() | ChangeClassifier().classify() | 用途 |
|------|----------------|------------------------------|------|
| action | ✅ | ✅ | 判斷同步方向 |
| modified_files | ✅ | ✅ | 列出變更文件 |
| approval_required | ❌ | ✅ | 判斷是否需要主人確認 |
| bump_type | ❌ | ✅ | commit message 類型（major/minor/patch） |
| new_version | ❌ | ✅ | 新版本號 |
| reason | ❌ | ✅ | 變更原因描述 |
| current_version | ❌ | ✅ | 當前版本號 |
| file_count | ❌ | ✅ | 變更文件數量 |
| has_forbidden | ❌ | ✅ | 是否觸及禁止模式 |
| has_hardcode | ❌ | ✅ | 是否檢測到硬編碼路徑 |

### Step 3: 上傳（upload_skill）

```python
from pathlib import Path

# 準備文件列表（modified + local_only）
files = []
for fname in comparison["modified_files"] + comparison["local_only_files"]:
    fpath = Path(local_dir) / fname
    if fpath.exists():
        files.append(fpath)

# 上傳（傳入完整的 classification）
result = engine.upload_skill(skill_name, files, classification)

if result["status"] == "uploaded":
    print(f"✅ 上傳成功: {result['commit_message']}")
else:
    print(f"❌ 上傳失敗: {result.get('error', 'Unknown error')}")
```

### 完整示例（一步不漏）

```python
#!/usr/bin/env python3
"""完整的三步上傳示例 - v1.0.15 Issue #16 修正版"""

from pathlib import Path
from scripts.sync_engine import SyncEngine
from scripts.change_classifier import ChangeClassifier

# 配置
SKILL_NAME = "my-skill"
LOCAL_DIR = "~/.workbuddy/skills/my-skill"

# Step 1: Compare
engine = SyncEngine()
comparison = engine.compare_skill(SKILL_NAME, LOCAL_DIR)

if comparison["action"] == "identical":
    print("✅ 無需上傳")
    exit(0)

if comparison["action"] == "github_ahead":
    print("⚠️ GitHub 較新，請先 pull")
    exit(1)

# Step 2: Classify（必須）
classifier = ChangeClassifier()
changed_files = comparison.get("modified_files", []) + comparison.get("local_only_files", [])
skill_name = Path(comparison.get("local_dir", ".")).name
classification = classifier.classify(skill_name, changed_files)

if classification["approval_required"]:
    print(f"⚠️ 需要主人確認: {classification['reason']}")
    exit(1)

# Step 3: Upload
files = [Path(LOCAL_DIR) / f for f in
         comparison["modified_files"] + comparison["local_only_files"]]
files = [f for f in files if f.exists()]

result = engine.upload_skill(SKILL_NAME, files, classification)
print(f"Result: {result['status']}")
```

---

## 3. 腳本說明

| 腳本 | 版本 | 職責 | 調用方式 |
|------|------|------|----------|
| `sync_engine.py` | 1.0.15 | 核心引擎（compare/upload/sync_changelog）+ Issue #16 自動防禦 | `from scripts.sync_engine import SyncEngine` |
| `change_classifier.py` | 1.0.1 | **變更分類器（必須步驟）** | `from scripts.change_classifier import ChangeClassifier` |
| `skill_issue_reporter.py` | 1.0.13 | Issue 報告生成器 | `python scripts/skill_issue_reporter.py --skill-dir <path>` |
| `scheduler_daemon.py` | 0.2.2 | 定時守護進程 | `python scripts/scheduler_daemon.py --start` |

### change_classifier.py 詳細說明

**推薦用法**（直接調用類別方法）：

```python
from scripts.change_classifier import ChangeClassifier

classifier = ChangeClassifier()
classification = classifier.classify(skill_name, changed_files)

# 輸出欄位:
#   - bump_type: "major" / "minor" / "patch"
#   - current_version: 當前版本號（如 "1.2.3"）
#   - new_version: 自動計算的新版本號
#   - approval_required: bool
#   - reason: 變更原因描述
#   - file_count: 變更文件數量
#   - has_forbidden: 是否觸及禁止模式
#   - has_hardcode: 是否檢測到硬編碼路徑
```

**向後兼容用法**（包裝函數，v1.0.15 新增）：

```python
from scripts.change_classifier import classify_change

# 輸入: compare_skill() 的返回值
# 輸出: 合併 comparison + classification 的完整 dict
classification = classify_change(comparison)
```

分類規則：

| action | 版本變更 | approval_required | bump_type |
|--------|---------|-------------------|-----------|
| identical | 無 | False | 無需上傳 |
| local_ahead | patch | False | patch |
| local_ahead | minor | False | minor |
| local_ahead | major | **True** | major |
| github_ahead | 任何 | False | 建議先 pull |
| diverged | 任何 | **True** | 需人工判斷 |

---

## 4. 常見問題

### Q: 為什麼 compare_skill() 不能直接傳給 upload_skill()？

`compare_skill()` 只負責比較文件差異，不負責判斷上傳策略。`upload_skill()` 需要知道：
- 這次變更是 major / minor / patch？（bump_type）
- 是否需要主人確認？（approval_required）
- 新版本號是什麼？（new_version）
- 變更原因是什麼？（reason）

這些資訊由 `ChangeClassifier().classify()` 根據變更內容自動判斷。

### Q: 如果跳過 change_classifier 會怎樣？

v1.0.13 之前：直接 `KeyError: approval_required` 崩潰。
v1.0.14 之後：`upload_skill()` 會自動檢測到缺少欄位，嘗試自動調用 `classify_change()` 補全。但這是防禦機制，不應依賴。**正確做法仍是顯式調用 ChangeClassifier().classify()。**

### Q: 舊代碼用了 classify_change() 還能用嗎？

v1.0.15 在 `change_classifier.py` 中加入了 `classify_change()` 包裝函數，舊代碼無需修改即可繼續使用。但**推薦遷移到新 API** `ChangeClassifier().classify()`，因為：
- 更明確的參數控制（skill_name, changed_files, diff_summary）
- 更符合 Python 類別設計慣例
- 文檔和示例均以新 API 為準

### Q: change_classifier 在哪裡？

    github-skill-organizer/scripts/change_classifier.py

如果找不到，請確認技能包已完整下載。

### Q: 如何判斷是否需要主人確認？

```python
if classification["approval_required"]:
    print("需要主人確認")
else:
    print("可以自動上傳")
```

通常 major version 變更（如 1.0.0 → 2.0.0）或 diverged 狀態需要確認。

---

## 5. 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.15 | 2026-05-23 | 修正 change_classifier API 文檔（Issue #16）：所有示例改用 `ChangeClassifier().classify()`；保留 `classify_change()` 向後兼容包裝函數說明 |
| 1.0.14 | 2026-05-23 | 新增強制三步上傳流程文檔（compare -> classify -> upload）；加入 change_classifier.py 使用說明；完整示例代碼 |
| 1.0.13 | 2026-05-23 | 統一 frontmatter 格式；sync_engine.py 安全訪問 classification（Issue #12） |
| 1.0.12 | 2026-05-22 | 新增 skill_issue_reporter.py + CONTRIBUTING.md |
| 1.0.11 | 2026-05-22 | 子目錄過濾、local_only 判定、強制 CLI 上傳、CHANGELOG 同步 |
| 1.0.10 | 2026-05-21 | expanduser(~) 路徑展開修正 |
| 1.0.9 | 2026-05-21 | local_dir 路徑推導修正 |
| 1.0.8 | 2026-05-21 | CHANGELOG.md CI 後處理、sync_changelog() |
| 1.0.5 | 2026-05-21 | compare_skill 路徑前綴過濾 + action 判定修正 |
| 1.0.4 | 2026-05-21 | 初始版本，基礎同步功能 |
