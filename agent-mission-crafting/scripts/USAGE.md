---
title: Crafting Report Script Usage Guide
name: agent-mission-crafting
description: Usage documentation for crafting_report.py covering GENERATOR_REPORT generation, checklist status update, CORRECTION.md recording, SUGGESTION.md management, and content integrity pre-check.
version: v1.2.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T17:18:10+08:00
fixes: []
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/USAGE.md"
  github_path: "agent-mission-crafting/scripts/USAGE.md"
---

# USAGE.md — crafting_report.py 使用說明

> 版本：v1.1.0（對齊 agent-mission-crafting v1.2.0）
> 位置：`scripts/USAGE.md`

---

## 版本對齊表

| 文件 | 版本 | 用途 |
|------|------|------|
| crafting_report.py | v1.1.0 | 生成 GENERATOR_REPORT、更新 checklist、記錄 CORRECTION.md、管理 SUGGESTION.md |
| LLM/SKILL.md | v1.2.0 | Generator 執行指令集 |
| readme/SKILL.md | v1.2.0 | 人類可讀解釋書 |
| USAGE.md | v1.1.0 | 本文件：腳本用法說明 |

---

## 快速開始

### 1. 生成 GENERATOR_REPORT

```python
from crafting_report import generate_generator_report

result = generate_generator_report(
    task_id="T20260511",
    subtask_results=[
        {"subtask_id": "T1", "status": "DONE", "output": "已讀取 SKILL.md"},
        {"subtask_id": "T2", "status": "DONE", "output": "今日匯率未記錄"},
        {"subtask_id": "T3", "status": "BLOCKED", "output": "腳本不存在"}
    ],
    issues_found=[
        {"subtask_id": "T3", "category": "執行問題", "description": "analyze_exchange_rate.py 腳本不存在"}
    ],
    conclusion="2/3 完成，1 項阻塞",
    assets_dir=Path("assets")
)
```

### 2. 更新 checklist 狀態

```python
from crafting_report import update_checklist_status

result = update_checklist_status(
    checklist_path=Path("assets/checklist.md"),
    subtask_id="T3",
    new_status="BLOCKED",
    issue_category="執行問題",
    issue_desc="腳本不存在"
)
```

### 3. 記錄 CORRECTION.md

```python
from crafting_report import record_correction

result = record_correction(
    task_id="T20260511",
    subtask_id="T3",
    error_type="執行問題",
    description="analyze_exchange_rate.py 腳本不存在",
    impact="無法執行趨勢分析",
    fix="上報 coordinator，由 Planner 補充腳本生成步驟",
    prevention="checklist 必須包含『確認腳本存在』步驟"
)
```

### 4. 追加 SUGGESTION.md（Planner / Evaluator 對 Generator 提出）

```python
from crafting_report import append_suggestion

# Planner 在計劃階段給 Generator 執行建議
result = append_suggestion(
    gap_id="C-001",
    subtask_id="T3",
    finder="PLANNER",
    round_num="R1",
    category="執行建議",
    description="條碼佔位請使用等寬字體，避免非等寬字體導致編號長度計算錯誤",
    impact="若使用比例字體，30 ASCII 長度的條碼編號可能視覺上溢出容器",
    suggestion="指定 font-family: 'Courier New', monospace; 並預留 35ch 寬度",
    status="待解決",
    suggestion_path=Path("agent-mission-crafting/assets/SUGGESTION.md")
)

# Evaluator 在 QC 階段給 Generator 更正
result = append_suggestion(
    gap_id="C-002",
    subtask_id="T5",
    finder="EVALUATOR",
    round_num="R11",
    category="QC 更正",
    description="分店資訊字體大小需微調，Generator 輸出為 12pt，但 PDF 原稿為 10pt",
    impact="顧客視覺上感覺排版擁擠，專業感下降",
    suggestion="將分店資訊字體統一調整為 10pt，行高 1.4",
    status="待解決"
)
```

### 5. 更新 SUGGESTION 狀態（Generator 修正後）

```python
from crafting_report import update_suggestion_status

result = update_suggestion_status(
    gap_id="C-002",
    new_status="已解決",
    verification_note="已修正為 10pt / 1.4 行高，Evaluator R12 驗證通過",
    suggestion_path=Path("agent-mission-crafting/assets/SUGGESTION.md")
)
```

### 6. 內容完整性預檢

```python
from crafting_report import check_content_integrity

result = check_content_integrity(
    content="這是準備寫入的完整內容...",
    expected_length=500
)
```

---

## 標準整合模板（Agent 直接複用）

```python
from pathlib import Path
from crafting_report import (
    generate_generator_report,
    update_checklist_status,
    record_correction,
    append_suggestion,
    update_suggestion_status
)

# 步驟 1：執行子任務
subtask_results = []
issues_found = []

for subtask in checklist["subtasks"]:
    try:
        result = execute_subtask(subtask)
        subtask_results.append({
            "subtask_id": subtask["id"],
            "status": "DONE",
            "output": result
        })
    except Exception as e:
        subtask_results.append({
            "subtask_id": subtask["id"],
            "status": "BLOCKED",
            "output": str(e)
        })
        issues_found.append({
            "subtask_id": subtask["id"],
            "category": "執行問題",
            "description": str(e)
        })
        record_correction(
            task_id=task_id,
            subtask_id=subtask["id"],
            error_type="執行問題",
            description=str(e),
            impact=f"子任務 {subtask['id']} 阻塞",
            fix="待 coordinator 處理",
            prevention="執行前確認環境與依賴"
        )

# 步驟 2：生成報告
report = generate_generator_report(
    task_id=task_id,
    subtask_results=subtask_results,
    issues_found=issues_found,
    conclusion=f"執行完成，{len(issues_found)} 項問題待處理"
)

# 步驟 3：讀取 SUGGESTION.md 並修正（如有）
# Planner / Evaluator 提出的建議在 SUGGESTION.md 中
# Generator 修正後更新狀態
```

---

## 輸出文件規範

| 文件類型 | 命名格式 | 存放位置 | 說明 |
|---------|---------|---------|------|
| GENERATOR_REPORT | `GENERATOR_REPORT_{YYYYMMDD_HHMMSS}.md` | `assets/` | 執行報告，每次執行生成一份 |
| CORRECTION.md | `CORRECTION.md` | `assets/` | 錯誤日誌，累積追加 |
| SUGGESTION.md | `SUGGESTION.md` | `agent-mission-crafting/assets/` | 外部反饋，Planner/Evaluator 寫入、Generator 讀取 |

---

## 三向 SUGGESTION.md 機制總覽

| 角色 | SUGGESTION.md 位置 | 誰給我提建議 | 我給誰提建議 |
|------|-------------------|-------------|-------------|
| Planner | `planning/assets/SUGGESTION.md` | Evaluator、Generator | — |
| Evaluator | `evaluating/assets/SUGGESTION.md` | Planner、Generator | Planner |
| Generator | `crafting/assets/SUGGESTION.md` | **Planner、Evaluator** | Planner、Evaluator |

---

## 常見問題

**Q：Planner 如何給 Generator 提 SUGGESTION？**
A：Planner 在生成 checklist 時，若預見執行難點，調用 `append_suggestion()` 寫入 `crafting/assets/SUGGESTION.md`。Generator 在「先想好」階段必須讀取此文件。

**Q：Evaluator 的 QC 更正和 SUGGESTION.md 有什麼區別？**
A：QC 更正（R11）是 Evaluator 對 Generator 輸出的直接反饋，應同時寫入 EVALUATOR_REPORT（正式報告）和 SUGGESTION.md（累積缺口庫）。

**Q：Generator 可以拒絕 Planner 的執行建議嗎？**
A：可以，但必須輸出 [QUESTION] 說明拒絕理由，由 coordinator 或主人裁決。禁止擅自無視。

---

*最後更新：2026-05-11*
