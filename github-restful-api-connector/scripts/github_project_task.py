#!/usr/bin/env python3
"""
---
title: "Task Scheduler"
name: "github-restful-api-connector"
description: "任務發派與排程：讀取分配卡片、執行回報、標記完成/失敗"
version: "0.1.0"
github_repository: "nervlin4444/ai.skills.devops"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/github_project_task.py"
    github_path: "/github-restful-api-connector/scripts/github_project_task.py"
---
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))
from github_restful_core import graphql_query, rest_request, load_env, logger
from github_project_agent import (
    get_project_id, load_field_cache, cache_project_fields,
    move_card, update_card_field, list_cards_by_status
)

# ============================================
# 配置
# ============================================
VERSION = "0.1.0"

# ============================================
# 核心函數
# ============================================
def poll_assigned_tasks(project_id: str, agent_name: str, owner: str, project_number: int, cache: dict = None) -> list:
    """
    輪詢看板上分配給指定 Agent 的 Todo 卡片。
    返回卡片列表，每項含 id、title、body。
    """
    if cache is None:
        cache = load_field_cache()
    cards = list_cards_by_status(project_id, "Todo", owner, project_number, cache)
    assigned = []
    for card in cards:
        # Check agent_name field via additional query or cached assumption
        # For now, filter by title/body mention or rely on external field
        assigned.append(card)
    logger.info(f"Polled {len(assigned)} tasks for agent '{agent_name}'")
    return assigned

def mark_task_in_progress(project_id: str, card_id: str, cache: dict = None) -> bool:
    """
    將卡片移至 In Progress，記錄開始時間戳。
    """
    if cache is None:
        cache = load_field_cache()
    move_card(project_id, card_id, "In Progress", cache)
    now = datetime.now(timezone.utc).isoformat()
    update_card_field(project_id, card_id, "start_time", now, cache)
    logger.info(f"Marked card {card_id} as In Progress at {now}")
    return True

def report_task_completion(project_id: str, card_id: str, result_summary: str, git_commit: str = None, cache: dict = None) -> bool:
    """
    將卡片移至 Done，附加結果摘要與可選 Git commit SHA。
    """
    if cache is None:
        cache = load_field_cache()
    move_card(project_id, card_id, "Done", cache)
    now = datetime.now(timezone.utc).isoformat()
    update_card_field(project_id, card_id, "end_time", now, cache)
    update_card_field(project_id, card_id, "error_summary", result_summary, cache)
    if git_commit:
        update_card_field(project_id, card_id, "git_commit", git_commit, cache)
    # Calculate duration if start_time exists
    logger.info(f"Marked card {card_id} as Done")
    return True

def report_task_failure(project_id: str, card_id: str, error_log: str, retryable: bool = False, cache: dict = None) -> bool:
    """
    將卡片移至 Failed，附加錯誤日誌。
    若 retryable=True，標記待重試（retry_count + 1）。
    """
    if cache is None:
        cache = load_field_cache()
    move_card(project_id, card_id, "Failed", cache)
    update_card_field(project_id, card_id, "error_summary", error_log, cache)
    if retryable:
        # Read current retry count and increment
        current_retry = 0  # Placeholder: would need actual field read
        update_card_field(project_id, card_id, "retry_count", str(current_retry + 1), cache)
    logger.info(f"Marked card {card_id} as Failed (retryable={retryable})")
    return True

# ============================================
# CLI 入口
# ============================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Project Task Scheduler — F-003")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--poll", action="store_true", help="Poll assigned tasks")
    parser.add_argument("--agent-name", type=str, default="")
    parser.add_argument("--complete", action="store_true", help="Mark task complete")
    parser.add_argument("--fail", action="store_true", help="Mark task failed")
    parser.add_argument("--card-id", type=str, default="")
    parser.add_argument("--summary", type=str, default="")
    parser.add_argument("--error-log", type=str, default="")
    parser.add_argument("--git-commit", type=str, default="")
    parser.add_argument("--retryable", action="store_true", help="Mark as retryable")
    args = parser.parse_args()

    if args.version:
        print(f"github_project_task.py v{VERSION}")
        return

    load_env()
    owner = os.environ.get("GITHUB_OWNER", "").strip()
    project_number = int(os.environ.get("GITHUB_PROJECT_NUMBER", "0").strip() or 0)
    if not owner or not project_number:
        logger.error("GITHUB_OWNER and GITHUB_PROJECT_NUMBER required.")
        sys.exit(1)

    project_id = get_project_id(owner, project_number)
    cache = load_field_cache()
    if not cache:
        cache = cache_project_fields(project_id)

    if args.poll:
        if not args.agent_name:
            logger.error("--agent-name required for --poll")
            sys.exit(1)
        tasks = poll_assigned_tasks(project_id, args.agent_name, owner, project_number, cache)
        print(json.dumps(tasks, indent=2, ensure_ascii=False))
        return

    if args.complete:
        if not args.card_id:
            logger.error("--card-id required for --complete")
            sys.exit(1)
        report_task_completion(project_id, args.card_id, args.summary, args.git_commit, cache)
        print(f"Completed card {args.card_id}")
        return

    if args.fail:
        if not args.card_id:
            logger.error("--card-id required for --fail")
            sys.exit(1)
        report_task_failure(project_id, args.card_id, args.error_log, args.retryable, cache)
        print(f"Failed card {args.card_id}")
        return

    parser.print_help()

if __name__ == "__main__":
    main()
