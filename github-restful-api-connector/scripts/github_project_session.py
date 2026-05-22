#!/usr/bin/env python3
"""
---
title: "Session Tracker"
name: "github-restful-api-connector"
description: "Agent Sessions 追蹤：GitHub 2026 原生 Agent Sessions API 整合"
version: "0.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/github_project_session.py"
    github_path: "/github-restful-api-connector/scripts/github_project_session.py"
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
from github_restful_core import rest_request, load_env, logger

VERSION = "0.1.0"

def track_session_start(owner: str, repo: str, issue_number: int, agent_name: str) -> str:
    endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/agent-sessions"
    payload = {
        "agent": agent_name,
        "status": "queued",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        result = rest_request("POST", endpoint, payload)
        session_id = result.get("id", "")
        logger.info(f"Session started: {session_id} for issue #{issue_number}")
        return session_id
    except RuntimeError as e:
        if "404" in str(e):
            logger.error("Sessions API not available. Ensure Copilot Agent is enabled.")
        raise

def track_session_update(owner: str, repo: str, session_id: str, status: str, log_url: str = None) -> bool:
    if status not in {"queued", "working", "completed", "failed"}:
        raise ValueError(f"Invalid session status: {status}")
    endpoint = f"/repos/{owner}/{repo}/agent-sessions/{session_id}"
    payload = {"status": status}
    if log_url:
        payload["log_url"] = log_url
    rest_request("PATCH", endpoint, payload)
    logger.info(f"Updated session {session_id} to '{status}'")
    return True

def track_session_end(owner: str, repo: str, session_id: str, final_status: str, summary: str) -> bool:
    if final_status not in {"completed", "failed"}:
        raise ValueError(f"Invalid final status: {final_status}")
    endpoint = f"/repos/{owner}/{repo}/agent-sessions/{session_id}"
    payload = {
        "status": final_status,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
    }
    rest_request("PATCH", endpoint, payload)
    logger.info(f"Ended session {session_id} with status '{final_status}'")
    return True

def get_session_logs(owner: str, repo: str, session_id: str) -> dict:
    endpoint = f"/repos/{owner}/{repo}/agent-sessions/{session_id}"
    result = rest_request("GET", endpoint)
    logger.info(f"Retrieved session {session_id} details")
    return result

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Project Session Tracker — F-004")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--end", action="store_true")
    parser.add_argument("--get", action="store_true")
    parser.add_argument("--issue-number", type=int, default=0)
    parser.add_argument("--session-id", type=str, default="")
    parser.add_argument("--agent-name", type=str, default="")
    parser.add_argument("--status", type=str, default="", choices=["queued", "working", "completed", "failed"])
    parser.add_argument("--log-url", type=str, default="")
    parser.add_argument("--final-status", type=str, default="", choices=["completed", "failed"])
    parser.add_argument("--summary", type=str, default="")
    args = parser.parse_args()

    if args.version:
        print(f"github_project_session.py v{VERSION}")
        return

    load_env()
    owner = os.environ.get("GITHUB_OWNER", "").strip()
    repo = os.environ.get("GITHUB_REPO", "").strip()
    if not owner or not repo:
        logger.error("GITHUB_OWNER and GITHUB_REPO required.")
        sys.exit(1)

    if args.start:
        if not args.issue_number or not args.agent_name:
            logger.error("--issue-number and --agent-name required for --start")
            sys.exit(1)
        sid = track_session_start(owner, repo, args.issue_number, args.agent_name)
        print(f"Session started: {sid}")
        return

    if args.update:
        if not args.session_id or not args.status:
            logger.error("--session-id and --status required for --update")
            sys.exit(1)
        track_session_update(owner, repo, args.session_id, args.status, args.log_url)
        print(f"Updated session {args.session_id} to {args.status}")
        return

    if args.end:
        if not args.session_id or not args.final_status:
            logger.error("--session-id and --final-status required for --end")
            sys.exit(1)
        track_session_end(owner, repo, args.session_id, args.final_status, args.summary)
        print(f"Ended session {args.session_id}")
        return

    if args.get:
        if not args.session_id:
            logger.error("--session-id required for --get")
            sys.exit(1)
        details = get_session_logs(owner, repo, args.session_id)
        print(json.dumps(details, indent=2, ensure_ascii=False))
        return

    parser.print_help()

if __name__ == "__main__":
    main()
