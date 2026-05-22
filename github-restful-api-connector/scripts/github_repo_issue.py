#!/usr/bin/env python3
"""
---
title: "GitHub Repo Issue Manager"
name: "github-restful-api-connector"
description: "GitHub 倉庫 Issue 管理：創建、列出、更新、關閉 Issue。依賴 F-001 github_restful_core.py。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-22T02:11:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/github_repo_issue.py"
    github_path: "github-restful-api-connector/scripts/github_repo_issue.py"
---

生成日期：2026-05-22 02:11:00
版本：v1.0.0
功能：GitHub 倉庫 Issue 管理（F-008）
依賴：F-001 github_restful_core.py
"""

import sys
import os
import json
import argparse
from pathlib import Path

# ============================================
# 依賴檢查與導入
# ============================================
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
ENV_PATH = BASE_DIR / ".env"

# 將 BASE_DIR 加入 sys.path，以便導入 github_restful_core
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 導入 F-001 核心模塊
try:
    from github_restful_core import (
        load_env,
        get_token,
        get_owner,
        get_repo,
        rest_request,
        logger,
    )
except ImportError:
    # 如果無法直接導入，嘗試從 scripts 目錄導入
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from github_restful_core import (
            load_env,
            get_token,
            get_owner,
            get_repo,
            rest_request,
            logger,
        )
    except ImportError as e:
        print(f"[ERROR] 無法導入 github_restful_core: {e}")
        print("[ERROR] 請確保 github_restful_core.py 在以下路徑之一：")
        print(f"  - {BASE_DIR / 'scripts'}")
        print(f"  - {SCRIPT_DIR}")
        sys.exit(1)

# ============================================
# 核心函數
# ============================================
def create_issue(owner: str, repo: str, title: str, body: str = None,
                labels: list = None, assignees: list = None) -> dict:
    """
    創建 Issue。

    Args:
        owner: 倉庫所有者（組織或個人）
        repo: 倉庫名稱
        title: Issue 標題
        body: Issue 正文（可選）
        labels: 標簽列表（可選）
        assignees: 分配用戶列表（可選）

    Returns:
        dict: 創建的 Issue 數據（含 number, html_url 等）

    Raises:
        RuntimeError: API 調用失敗
    """
    endpoint = f"/repos/{owner}/{repo}/issues"
    payload = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees

    logger.info(f"Creating issue: {title}")
    result = rest_request("POST", endpoint, payload)
    logger.info(f"Created issue #{result['number']}: {result['html_url']}")
    return result


def list_issues(owner: str, repo: str, state: str = "open",
                labels: str = None, assignee: str = None) -> list:
    """
    列出 Issues。

    Args:
        owner: 倉庫所有者
        repo: 倉庫名稱
        state: 狀態（"open", "closed", "all"）
        labels: 標簽過濾（逗號分隔）
        assignee: 分配用戶過濾

    Returns:
        list: Issue 列表
    """
    endpoint = f"/repos/{owner}/{repo}/issues"
    params = {"state": state, "per_page": 100}
    if labels:
        params["labels"] = labels
    if assignee:
        params["assignee"] = assignee

    # 處理分頁
    issues = []
    page = 1
    while True:
        params["page"] = page
        # 手動拼接查詢參數
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{endpoint}?{query}"
        batch = rest_request("GET", url)
        issues.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    logger.info(f"Listed {len(issues)} issues (state={state})")
    return issues


def update_issue(owner: str, repo: str, issue_number: int,
                 title: str = None, body: str = None,
                 state: str = None, labels: list = None) -> dict:
    """
    更新 Issue。

    Args:
        owner: 倉庫所有者
        repo: 倉庫名稱
        issue_number: Issue 編號
        title: 新標題（可選）
        body: 新正文（可選）
        state: 新狀態（"open", "closed"）
        labels: 新標簽列表（可選）

    Returns:
        dict: 更新後的 Issue 數據
    """
    endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}"
    payload = {}
    if title:
        payload["title"] = title
    if body:
        payload["body"] = body
    if state:
        payload["state"] = state
    if labels:
        payload["labels"] = labels

    logger.info(f"Updating issue #{issue_number}")
    result = rest_request("PATCH", endpoint, payload)
    logger.info(f"Updated issue #{result['number']}")
    return result


def close_issue(owner: str, repo: str, issue_number: int) -> dict:
    """
    關閉 Issue。

    Args:
        owner: 倉庫所有者
        repo: 倉庫名稱
        issue_number: Issue 編號

    Returns:
        dict: 更新後的 Issue 數據
    """
    return update_issue(owner, repo, issue_number, state="closed")


def get_issue(owner: str, repo: str, issue_number: int) -> dict:
    """
    獲取單個 Issue 詳情。

    Args:
        owner: 倉庫所有者
        repo: 倉庫名稱
        issue_number: Issue 編號

    Returns:
        dict: Issue 數據
    """
    endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}"
    result = rest_request("GET", endpoint)
    return result


# ============================================
# CLI 入口
# ============================================
def main():
    parser = argparse.ArgumentParser(
        description="GitHub Repo Issue Manager — F-008",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 創建 Issue
  python scripts/github_repo_issue.py --create --title "Bug: upload failed" --body "Details..."

  # 列出開放 Issue
  python scripts/github_repo_issue.py --list --state open

  # 更新 Issue
  python scripts/github_repo_issue.py --update 42 --title "Fixed" --state closed

  # 關閉 Issue
  python scripts/github_repo_issue.py --close 42

  # 使用自定義 owner/repo（覆蓋 .env）
  python scripts/github_repo_issue.py --create --owner myorg --repo myproject --title "Test"
"""
    )
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--owner", type=str, default=None, help="Repository owner (overrides .env)")
    parser.add_argument("--repo", type=str, default=None, help="Repository name (overrides .env)")
    parser.add_argument("--create", action="store_true", help="Create a new issue")
    parser.add_argument("--list", action="store_true", help="List issues")
    parser.add_argument("--update", type=int, metavar="NUM", help="Update issue number")
    parser.add_argument("--close", type=int, metavar="NUM", help="Close issue number")
    parser.add_argument("--get", type=int, metavar="NUM", help="Get issue details")
    parser.add_argument("--title", type=str, default=None, help="Issue title")
    parser.add_argument("--body", type=str, default=None, help="Issue body (text or file path)")
    parser.add_argument("--labels", type=str, default=None, help="Comma-separated labels")
    parser.add_argument("--assignees", type=str, default=None, help="Comma-separated assignees")
    parser.add_argument("--state", type=str, default="open", choices=["open", "closed", "all"], help="Issue state for list/update")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.version:
        print("github_repo_issue.py v1.0.0")
        return

    # 載入環境
    load_env()

    # 確定 owner/repo
    owner = args.owner or get_owner()
    repo = args.repo or get_repo()

    if not owner or not repo:
        print("[ERROR] Owner/repo not specified. Use --owner/--repo or set in .env")
        sys.exit(1)

    # 處理 --body 可能是文件路徑
    body = args.body
    if body and Path(body).exists():
        with open(body, "r", encoding="utf-8") as f:
            body = f.read()
            logger.info(f"Read body from file: {args.body}")

    # 解析 labels/assignees
    labels = args.labels.split(",") if args.labels else None
    assignees = args.assignees.split(",") if args.assignees else None

    # 執行操作
    try:
        if args.create:
            if not args.title:
                print("[ERROR] --title required for create")
                sys.exit(1)
            result = create_issue(owner, repo, args.title, body, labels, assignees)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"[OK] Created issue #{result['number']}")
                print(f"  URL: {result['html_url']}")
                print(f"  Title: {result['title']}")

        elif args.list:
            issues = list_issues(owner, repo, args.state, args.labels, args.assignee)
            if args.json:
                print(json.dumps(issues, indent=2, ensure_ascii=False))
            else:
                print(f"[OK] Found {len(issues)} issues (state={args.state}):")
                for issue in issues:
                    print(f"  #{issue['number']} [{issue['state']}] {issue['title']}")
                    print(f"    {issue['html_url']}")

        elif args.get is not None:
            result = get_issue(owner, repo, args.get)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"[OK] Issue #{result['number']}")
                print(f"  Title: {result['title']}")
                print(f"  State: {result['state']}")
                print(f"  URL: {result['html_url']}")
                if result.get("body"):
                    print(f"  Body: {result['body'][:200]}...")

        elif args.update is not None:
            if not any([args.title, body, args.state, labels]):
                print("[ERROR] --update requires at least one of --title/--body/--state/--labels")
                sys.exit(1)
            result = update_issue(owner, repo, args.update, args.title, body, args.state, labels)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"[OK] Updated issue #{result['number']}")
                print(f"  Title: {result['title']}")
                print(f"  State: {result['state']}")

        elif args.close is not None:
            result = close_issue(owner, repo, args.close)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"[OK] Closed issue #{result['number']}")

        else:
            parser.print_help()

    except RuntimeError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        logger.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
