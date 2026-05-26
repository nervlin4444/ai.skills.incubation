'''---
title: Crafting Report Core Script
name: agent-mission-crafting
description: Core script for Agent Mission Crafting. Generates GENERATOR_REPORT, updates checklist status, records CORRECTION.md, manages SUGGESTION.md append and status update, and content integrity pre-check.
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
  local_path: "{baseDir}/crafting_report.py"
  github_path: "agent-mission-crafting/scripts/crafting_report.py"
---
'''

"""
crafting_report.py v1.1.0
Agent Mission Crafting 配套腳本
生成 GENERATOR_REPORT、更新 checklist 狀態、記錄 CORRECTION.md、管理 SUGGESTION.md

用法:
    from crafting_report import (
        generate_generator_report,
        update_checklist_status,
        record_correction,
        append_suggestion,
        update_suggestion_status,
        check_content_integrity
    )
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

__version__ = "1.1.0"

# 預設路徑：user skill assets 目錄（相對路徑）
DEFAULT_ASSETS_DIR = Path("assets")
DEFAULT_CORRECTION_PATH = Path("assets/CORRECTION.md")
DEFAULT_SUGGESTION_PATH = Path("agent-mission-crafting/assets/SUGGESTION.md")


def generate_generator_report(
    task_id: str,
    subtask_results: List[Dict],
    issues_found: List[Dict],
    conclusion: str,
    assets_dir: Optional[Path] = None
) -> Dict:
    """
    生成 GENERATOR_REPORT_{YYYYMMDD_HHMMSS}.md

    Args:
        task_id: 任務編號
        subtask_results: 子任務執行結果列表，每項含 subtask_id, status, output
        issues_found: 發現的問題列表，每項含 subtask_id, category, description
        conclusion: 總結文字
        assets_dir: 產出目錄

    Returns:
        dict: {success, file_path, written_length, timestamp, warning}
    """
    assets_dir = assets_dir or DEFAULT_ASSETS_DIR
    assets_dir = Path(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"GENERATOR_REPORT_{timestamp}.md"
    filepath = assets_dir / filename

    total = len(subtask_results)
    done = sum(1 for r in subtask_results if r.get("status") == "DONE")
    blocked = sum(1 for r in subtask_results if r.get("status") == "BLOCKED")
    in_progress = sum(1 for r in subtask_results if r.get("status") == "IN_PROGRESS")

    lines = [
        f"---",
        f"id: generator-report-{task_id}",
        f"task_id: {task_id}",
        f"generated_at: {datetime.now().isoformat()}",
        f"version: {__version__}",
        f"---",
        f"",
        f"# GENERATOR REPORT — {task_id}",
        f"",
        f"## 基本資訊",
        f"",
        f"| 欄位 | 內容 |",
        f"|------|------|",
        f"| 任務 ID | {task_id} |",
        f"| 生成時間 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |",
        f"| 子任務總數 | {total} |",
        f"| 已完成 | {done} |",
        f"| 執行中 | {in_progress} |",
        f"| 阻塞 | {blocked} |",
        f"| 完成率 | {done/total*100:.1f}% |" if total > 0 else "| 完成率 | N/A |",
        f"",
        f"## 子任務執行結果",
        f"",
        f"| 子任務ID | 狀態 | 輸出摘要 |",
        f"|---------|------|---------|",
    ]

    for result in subtask_results:
        status = result.get("status", "UNKNOWN")
        output = result.get("output", "")
        output_summary = output[:50] + "..." if len(output) > 50 else output
        lines.append(f"| {result.get('subtask_id', 'N/A')} | {status} | {output_summary} |")

    lines.extend([
        f"",
        f"## 發現的問題",
        f"",
    ])

    if issues_found:
        lines.append("| 子任務ID | 問題類型 | 描述 |")
        lines.append("|---------|---------|------|")
        for issue in issues_found:
            lines.append(
                f"| {issue.get('subtask_id', 'N/A')} | "
                f"{issue.get('category', '執行問題')} | "
                f"{issue.get('description', '')} |"
            )
    else:
        lines.append("✅ 本輪未發現執行問題。")

    lines.extend([
        f"",
        f"## 結論",
        f"",
        f"{conclusion}",
        f"",
        f"---",
        f"*報告由 crafting_report.py v{__version__} 生成*",
    ])

    content = "\n".join(lines)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "success": True,
        "file_path": str(filepath),
        "written_length": len(content),
        "timestamp": datetime.now().isoformat(),
        "warning": None
    }


def update_checklist_status(
    checklist_path: Path,
    subtask_id: str,
    new_status: str,
    issue_category: Optional[str] = None,
    issue_desc: Optional[str] = None
) -> Dict:
    """
    更新 checklist 中指定子任務的狀態

    Args:
        checklist_path: checklist.md 路徑
        subtask_id: 子任務 ID
        new_status: TODO / IN_PROGRESS / DONE / BLOCKED
        issue_category: 如有問題，標記類型（計劃問題 / 評估問題 / 執行問題）
        issue_desc: 問題描述

    Returns:
        dict: {success, updated, timestamp, warning}
    """
    checklist_path = Path(checklist_path)

    if not checklist_path.exists():
        return {
            "success": False,
            "updated": False,
            "timestamp": datetime.now().isoformat(),
            "warning": f"checklist 不存在於 {checklist_path}"
        }

    with open(checklist_path, "r", encoding="utf-8") as f:
        content = f.read()

    update_log = (
        f"\n\n---\n"
        f"**狀態更新** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- 子任務: {subtask_id}\n"
        f"- 新狀態: {new_status}\n"
    )
    if issue_category and issue_desc:
        update_log += f"- 問題標記: [{issue_category}] {issue_desc}\n"

    with open(checklist_path, "a", encoding="utf-8") as f:
        f.write(update_log)

    return {
        "success": True,
        "updated": True,
        "timestamp": datetime.now().isoformat(),
        "warning": None
    }


def record_correction(
    task_id: str,
    subtask_id: str,
    error_type: str,
    description: str,
    impact: str,
    fix: str,
    prevention: str,
    correction_path: Optional[Path] = None
) -> Dict:
    """
    記錄錯誤到 CORRECTION.md（累積追加）

    Args:
        task_id: 任務編號
        subtask_id: 子任務 ID
        error_type: 計劃問題 / 評估問題 / 執行問題
        description: 錯誤描述
        impact: 影響範圍
        fix: 修正方案
        prevention: 預防措施
        correction_path: CORRECTION.md 路徑

    Returns:
        dict: {success, file_path, appended_length, timestamp, warning}
    """
    correction_path = correction_path or DEFAULT_CORRECTION_PATH
    correction_path = Path(correction_path)
    correction_path.parent.mkdir(parents=True, exist_ok=True)

    entry = (
        f"\n---\n"
        f"## 錯誤記錄 — {task_id} / {subtask_id}\n"
        f"\n"
        f"- **時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- **錯誤類型**: {error_type}\n"
        f"- **描述**: {description}\n"
        f"- **影響**: {impact}\n"
        f"- **修正方案**: {fix}\n"
        f"- **預防措施**: {prevention}\n"
    )

    with open(correction_path, "a", encoding="utf-8") as f:
        f.write(entry)

    return {
        "success": True,
        "file_path": str(correction_path),
        "appended_length": len(entry),
        "timestamp": datetime.now().isoformat(),
        "warning": None
    }


def append_suggestion(
    gap_id: str,
    subtask_id: str,
    finder: str,
    round_num: str,
    category: str,
    description: str,
    impact: str,
    suggestion: str,
    status: str = "待解決",
    suggestion_path: Optional[Path] = None
) -> Dict:
    """
    追加缺口到 crafting/assets/SUGGESTION.md（Planner / Evaluator 對 Generator 提出）

    Args:
        gap_id: 缺口編號，如 "C-001"
        subtask_id: 關聯 checklist 子任務 ID
        finder: 誰發現的（PLANNER / EVALUATOR）
        round_num: 輪次，如 "R1", "R11"
        category: 問題類型（執行建議 / QC 更正 / 技術警告）
        description: 具體缺口描述
        impact: 不解決的後果
        suggestion: 修正建議
        status: 待解決 / 已解決
        suggestion_path: SUGGESTION.md 路徑

    Returns:
        dict: {success, file_path, appended_length, timestamp, warning}
    """
    suggestion_path = suggestion_path or DEFAULT_SUGGESTION_PATH
    suggestion_path = Path(suggestion_path)
    suggestion_path.parent.mkdir(parents=True, exist_ok=True)

    if not suggestion_path.exists():
        header = (
            "# SUGGESTION.md — Generator 雙向累積型反饋規範\n"
            "\n"
            "> 核心規則：自己不建议自己。Planner 和 Evaluator 對 Generator 提出缺口，Generator 修正後標記「已解決」。\n"
            "> 文件位置：agent-mission-crafting/assets/SUGGESTION.md\n"
            "> 性質：累積型文件，持續追加，不覆蓋\n"
            "\n"
            "## 索引表\n"
            "\n"
            "| 缺口編號 | 子任務ID | 發現者 | 輪次 | 問題類型 | 狀態 | 關鍵詞 |\n"
            "|---------|---------|--------|------|---------|------|--------|\n"
        )
        with open(suggestion_path, "w", encoding="utf-8") as f:
            f.write(header)

    entry_line = (
        f"| {gap_id} | {subtask_id} | {finder} | {round_num} | {category} | {status} | "
        f"{description[:20]}... |\n"
    )

    detail = (
        f"\n---\n"
        f"## {gap_id}\n"
        f"\n"
        f"- **子任務 ID**: {subtask_id}\n"
        f"- **發現者**: {finder}\n"
        f"- **輪次**: {round_num}\n"
        f"- **問題類型**: {category}\n"
        f"- **描述**: {description}\n"
        f"- **影響**: {impact}\n"
        f"- **建議**: {suggestion}\n"
        f"- **狀態**: {status}\n"
        f"- **修正驗證**: （Generator 修正後填寫）\n"
    )

    with open(suggestion_path, "r", encoding="utf-8") as f:
        existing = f.read()

    lines = existing.split("\n")
    insert_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("|") and "缺口編號" not in lines[i] and "---" not in lines[i]:
            insert_idx = i + 1
            break

    lines.insert(insert_idx, entry_line.rstrip())
    new_content = "\n".join(lines) + detail

    with open(suggestion_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return {
        "success": True,
        "file_path": str(suggestion_path),
        "appended_length": len(entry_line) + len(detail),
        "timestamp": datetime.now().isoformat(),
        "warning": None
    }


def update_suggestion_status(
    gap_id: str,
    new_status: str,
    verification_note: str = "",
    suggestion_path: Optional[Path] = None
) -> Dict:
    """
    更新 crafting/assets/SUGGESTION.md 中指定缺口的狀態

    Args:
        gap_id: 缺口編號，如 "C-001"
        new_status: 新狀態（待解決 / 已解決）
        verification_note: 修正驗證說明
        suggestion_path: SUGGESTION.md 路徑

    Returns:
        dict: {success, file_path, updated, timestamp, warning}
    """
    suggestion_path = suggestion_path or DEFAULT_SUGGESTION_PATH
    suggestion_path = Path(suggestion_path)

    if not suggestion_path.exists():
        return {
            "success": False,
            "file_path": str(suggestion_path),
            "updated": False,
            "timestamp": datetime.now().isoformat(),
            "warning": f"SUGGESTION.md 不存在於 {suggestion_path}"
        }

    with open(suggestion_path, "r", encoding="utf-8") as f:
        content = f.read()

    old_status_pattern = f"**狀態**: 待解決\n"
    new_status_line = f"**狀態**: {new_status}\n"

    if old_status_pattern in content:
        content = content.replace(old_status_pattern, new_status_line, 1)

    if verification_note:
        old_verification = "**修正驗證**: （Generator 修正後填寫）\n"
        new_verification = f"**修正驗證**: {verification_note}\n"
        if old_verification in content:
            content = content.replace(old_verification, new_verification, 1)

    with open(suggestion_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "success": True,
        "file_path": str(suggestion_path),
        "updated": True,
        "timestamp": datetime.now().isoformat(),
        "warning": None
    }


def check_content_integrity(content: str, expected_length: int = 0) -> Dict:
    """
    內容完整性預檢（供 LLM 調用前自檢）

    Args:
        content: 準備寫入的內容
        expected_length: 畫面上實際輸出的字數預期

    Returns:
        dict: {is_complete, actual_length, expected_length, ratio, warning}
    """
    actual_length = len(content)
    ratio = actual_length / expected_length if expected_length > 0 else 1.0
    is_complete = ratio >= 0.9

    warning = None
    if expected_length > 0 and ratio < 0.9:
        warning = (
            f"[CONTENT-INCOMPLETE-WARNING] 記錄長度 {actual_length} < 預期 {expected_length} "
            f"（達成率 {ratio:.1%}）。禁止傳入摘要，必須傳入完整內容。"
        )

    return {
        "is_complete": is_complete,
        "actual_length": actual_length,
        "expected_length": expected_length,
        "ratio": ratio,
        "warning": warning
    }


if __name__ == "__main__":
    print(f"crafting_report.py v{__version__} 已載入")
    print(f"預設產出目錄: {DEFAULT_ASSETS_DIR}")
    print(f"預設 CORRECTION 路徑: {DEFAULT_CORRECTION_PATH}")
    print(f"預設 SUGGESTION 路徑: {DEFAULT_SUGGESTION_PATH}")
