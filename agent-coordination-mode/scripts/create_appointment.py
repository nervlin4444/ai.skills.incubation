#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''---
title: Appointment Generator
name: agent-coordination-mode
description: Generates standardized Sub-Agent appointment documents with 8 mandatory fields per agent-coordination-mode v1.3.0 specification.
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
  local_path: "{baseDir}/create_appointment.py"
  github_path: "agent-coordination-mode/scripts/create_appointment.py"
---
'''

"""
create_appointment.py v1.0.0 - 委任狀生成器

由 coordinator（Main Agent L0）調用，統一生成 Sub-Agent 委任狀。
根據 agent-coordination-mode v1.3.0 規範，委任狀必須包含 8 個強制欄位。

調用方式:
    from create_appointment import create_appointment
    result = create_appointment(
        task_id="T20260511",
        role="PLANNER",
        original_request="請執行 currency-exchange-tracker 技能...",
        task_nature="修改",
        target_description="將 agent-conversation-mode 升級到 v3.3.1",
        p0_banlist=["禁止修改 SOUL.md", "禁止 hardcode 值"],
        expert_simulation="戰略大師：具備系統分析師背景，擅長拆解複雜需求",
        verification_requirements=["驗證 checklist 可完成率 ≥ 80%"],
        cautions=["上次執行時發現腳本不存在，需先確認技能包完整性"],
        family_manual=["agent-bootstrap", "agent-conversation-mode", "agent-mission-planning"]
    )

返回:
    dict: {
        "success": bool,
        "appointment_path": str,      # 委任狀文件路徑
        "task_id": str,
        "role": str,
        "timestamp": str,
        "content_preview": str        # 前 200 字預覽
    }
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).parent.resolve()
ASSETS_DIR = SCRIPT_DIR.parent / "assets"


def create_appointment(
    task_id: str,
    role: str,
    original_request: str,
    task_nature: str,
    target_description: str,
    p0_banlist: list,
    expert_simulation: str,
    verification_requirements: list,
    cautions: list,
    family_manual: list,
) -> dict:
    """
    生成標準委任狀文件 APPOINTMENT_{task_id}_{role}.md

    所有參數均為強制，缺一不可。調用方必須確保內容完整。
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    # 文件名規範: APPOINTMENT_{任務ID}_{角色}.md
    filename = f"APPOINTMENT_{task_id}_{role.upper()}.md"
    filepath = ASSETS_DIR / filename

    # 構建委任狀內容（8 個強制欄位）
    p0_lines = "\n".join(f"- {item}" for item in p0_banlist) if p0_banlist else "- （無）"
    verify_lines = "\n".join(f"- {item}" for item in verification_requirements) if verification_requirements else "- （無）"
    caution_lines = "\n".join(f"- {item}" for item in cautions) if cautions else "- （無）"
    family_lines = "\n".join(f"- [ ] {item}" for item in family_manual) if family_manual else "- （無）"

    content = f"""---
id: appointment-{task_id}-{role.lower()}
version: v1.0.0
generated_at: {timestamp_iso}
task_id: {task_id}
role: {role.upper()}
status: PENDING
---

# 委任狀 | {role.upper()} | {task_id}

## 1. 原始需求（一字不改）

{original_request}

## 2. 任務性質

{task_nature}

## 3. 目標描述

{target_description}

## 4. P0 禁止清單

{p0_lines}

## 5. 專家模擬

{expert_simulation}

## 6. 驗察需求

{verify_lines}

## 7. 注意事項

{caution_lines}

## 8. 家族手冊確認（執行前強制勾選）

{family_lines}

---

*本委任狀由 coordinator 生成，Sub-Agent 執行完成後調用 complete_appointment.py 回傳產物。*
*生成時間: {timestamp_iso}*
"""

    try:
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "appointment_path": str(filepath),
            "task_id": task_id,
            "role": role.upper(),
            "timestamp": timestamp_iso,
            "content_preview": content[:200].replace("\n", " ") + "...",
        }
    except Exception as e:
        sys.stderr.write(f"[create_appointment ERROR] {e}\n")
        return {
            "success": False,
            "appointment_path": "",
            "task_id": task_id,
            "role": role.upper(),
            "timestamp": timestamp_iso,
            "content_preview": f"[ERROR] {e}",
        }


if __name__ == "__main__":
    # 命令行後備接口
    import argparse
    parser = argparse.ArgumentParser(description="生成 Sub-Agent 委任狀")
    parser.add_argument("--task-id", required=True, help="任務 ID")
    parser.add_argument("--role", required=True, choices=["PLANNER", "EVALUATOR", "GENERATOR", "FINISHING"], help="角色")
    parser.add_argument("--original-request", required=True, help="原始需求")
    parser.add_argument("--task-nature", required=True, help="任務性質")
    parser.add_argument("--target-description", required=True, help="目標描述")
    parser.add_argument("--p0-banlist", required=True, help="P0 禁止清單（逗號分隔）")
    parser.add_argument("--expert-simulation", required=True, help="專家模擬")
    parser.add_argument("--verification-requirements", required=True, help="驗察需求（逗號分隔）")
    parser.add_argument("--cautions", default="", help="注意事項（逗號分隔）")
    parser.add_argument("--family-manual", required=True, help="家族手冊（逗號分隔）")
    args = parser.parse_args()

    result = create_appointment(
        task_id=args.task_id,
        role=args.role,
        original_request=args.original_request,
        task_nature=args.task_nature,
        target_description=args.target_description,
        p0_banlist=args.p0_banlist.split(","),
        expert_simulation=args.expert_simulation,
        verification_requirements=args.verification_requirements.split(","),
        cautions=args.cautions.split(",") if args.cautions else [],
        family_manual=args.family_manual.split(","),
    )
    print(result)
