#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''---
title: Appointment Completion Collector
name: agent-coordination-mode
description: Collects and archives Sub-Agent outputs upon task completion, validates completeness against expected outputs, updates appointment status, and generates mission completion markers.
version: v1.3.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T09:26:53+08:00
fixes: []
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/complete_appointment.py"
  github_path: "agent-coordination-mode/scripts/complete_appointment.py"
---
'''

"""
complete_appointment.py v1.0.0 - 委任完成回收器

由 Sub-Agent 在完成任務後調用，或由 coordinator（Main Agent L0）主動調用。
統一回收 Sub-Agent 產出，驗證完整性，歸檔到 user skill assets 目錄。

調用方式:
    from complete_appointment import complete_appointment
    result = complete_appointment(
        task_id="T20260511",
        role="PLANNER",
        expected_outputs=["CHECKLIST.md", "PLANNER_REPORT_*.md"],
        produced_files=["CHECKLIST.md", "PLANNER_REPORT_20260511_143022.md"]
    )

返回:
    dict: {
        "success": bool,
        "task_id": str,
        "role": str,
        "archived_files": list,       # 已歸檔的文件路徑列表
        "missing_files": list,        # 預期但未找到的文件
        "status": str,                # COMPLETED / PARTIAL / FAILED
        "timestamp": str
    }
"""

import sys
from pathlib import Path
import fnmatch
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).parent.resolve()
ASSETS_DIR = SCRIPT_DIR.parent / "assets"


def complete_appointment(
    task_id: str,
    role: str,
    expected_outputs: list,
    produced_files: list = None,
) -> dict:
    """
    回收 Sub-Agent 產出，驗證完整性，統一歸檔。

    Args:
        task_id: 任務 ID
        role: 角色名稱（PLANNER / EVALUATOR / GENERATOR / FINISHING）
        expected_outputs: 預期產出文件列表（支持通配符，如 "PLANNER_REPORT_*.md"）
        produced_files: Sub-Agent 聲稱已產出的文件名列表（可選，若未提供則自動掃描）

    Returns:
        dict: 歸檔結果與狀態
    """
    ts = datetime.now(timezone.utc).isoformat()
    role_upper = role.upper()

    # 1. 掃描 assets 目錄，查找該角色的產出
    found_files = []
    scan_patterns = expected_outputs if expected_outputs else []

    if produced_files:
        # 若 Sub-Agent 提供了產出清單，優先驗證這些文件
        for fname in produced_files:
            fpath = ASSETS_DIR / fname
            if fpath.exists():
                found_files.append(fpath)
    else:
        # 自動掃描匹配預期模式的文件
        if ASSETS_DIR.exists():
            for pattern in scan_patterns:
                for fpath in ASSETS_DIR.glob(pattern):
                    if fpath.is_file():
                        found_files.append(fpath)

    # 2. 驗證完整性：檢查預期產出是否全部存在
    missing = []
    for pattern in expected_outputs:
        matched = any(fnmatch.fnmatch(f.name, pattern) for f in found_files)
        if not matched:
            missing.append(pattern)

    # 3. 更新委任狀狀態（從 PENDING 改為 COMPLETED 或 PARTIAL）
    appointment_file = ASSETS_DIR / f"APPOINTMENT_{task_id}_{role_upper}.md"
    if appointment_file.exists():
        try:
            with open(appointment_file, "r", encoding="utf-8") as f:
                content = f.read()
            # 替換狀態欄位
            content = content.replace("status: PENDING", f"status: {'COMPLETED' if not missing else 'PARTIAL'}")
            content = content.replace(f"*生成時間:", f"*完成時間: {ts}\n*生成時間:")
            with open(appointment_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            sys.stderr.write(f"[complete_appointment WARNING] 無法更新委任狀狀態: {e}\n")

    # 4. 生成歸檔摘要
    archived = [str(f) for f in found_files]
    status = "COMPLETED" if not missing else ("PARTIAL" if found_files else "FAILED")

    # 5. 生成 MISSION_COMPLETE 標記（若所有角色均完成）
    if status == "COMPLETED" and role_upper == "FINISHING":
        mission_complete_file = ASSETS_DIR / f"MISSION_COMPLETE_{task_id}.md"
        try:
            with open(mission_complete_file, "w", encoding="utf-8") as f:
                f.write(f"""---
id: mission-complete-{task_id}
version: v1.0.0
completed_at: {ts}
task_id: {task_id}
status: COMPLETED
---

# 任務完成標記 | {task_id}

所有 Pipeline 節點已完成：
- [x] Planner
- [x] Evaluator
- [x] Generator
- [x] Finishing

完成時間: {ts}
""")
        except Exception as e:
            sys.stderr.write(f"[complete_appointment WARNING] 無法生成完成標記: {e}\n")

    return {
        "success": status != "FAILED",
        "task_id": task_id,
        "role": role_upper,
        "archived_files": archived,
        "missing_files": missing,
        "status": status,
        "timestamp": ts,
    }


def scan_role_outputs(task_id: str, role: str) -> list:
    """
    主動掃描指定角色的產出文件（供 coordinator 在未收到 Sub-Agent 回報時使用）。

    Args:
        task_id: 任務 ID
        role: 角色名稱

    Returns:
        list: 找到的文件路徑列表
    """
    role_upper = role.upper()
    patterns = {
        "PLANNER": ["CHECKLIST.md", f"PLANNER_REPORT_*.md"],
        "EVALUATOR": [f"EVALUATOR_REPORT_*.md"],
        "GENERATOR": [f"GENERATOR_REPORT_*.md", "*.py", "*.md"],
        "FINISHING": [f"FINAL_REPORT_*.md", f"MISSION_COMPLETE_*.md"],
    }

    found = []
    if ASSETS_DIR.exists():
        for pattern in patterns.get(role_upper, []):
            for fpath in ASSETS_DIR.glob(pattern):
                if fpath.is_file():
                    found.append(str(fpath))
    return found


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="回收 Sub-Agent 委任產出")
    parser.add_argument("--task-id", required=True, help="任務 ID")
    parser.add_argument("--role", required=True, choices=["PLANNER", "EVALUATOR", "GENERATOR", "FINISHING"], help="角色")
    parser.add_argument("--expected-outputs", required=True, help="預期產出（逗號分隔，支持通配符）")
    parser.add_argument("--produced-files", default="", help="已產出文件（逗號分隔，可選）")
    args = parser.parse_args()

    result = complete_appointment(
        task_id=args.task_id,
        role=args.role,
        expected_outputs=args.expected_outputs.split(","),
        produced_files=args.produced_files.split(",") if args.produced_files else None,
    )
    print(result)
