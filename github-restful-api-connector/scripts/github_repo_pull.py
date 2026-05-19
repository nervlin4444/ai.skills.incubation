#!/usr/bin/env python3
"""
---
title: "Repo Pull Tool"
name: "github-restful-api-connector"
description: "從 GitHub 倉庫下載技能目錄並同步到本地。若本地檔案較新只報告不覆蓋，若倉庫較新則下載更新。"
version: "0.1.0"
github_repository: "nervlin4444/ai.skills.devops"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/github_repo_pull.py"
    github_path: "/github-restful-api-connector/scripts/github_repo_pull.py"
---

github_repo_pull.py — F-007 倉庫下載同步工具
從 GitHub 倉庫指定目錄下載全部檔案並同步到本地。
若本地檔案較新 → 只報告（WARN），不覆蓋。
若倉庫檔案較新或本地不存在 → 下載覆蓋。
版本：v0.1.0
技能：ai.skills.devops.github
Path: ai.skills.devops.github/github-restful-api-connector/scripts/github_repo_pull.py
"""

import os
import sys
import base64
import logging
from pathlib import Path
from datetime import datetime, timezone

scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))
from github_restful_core import rest_request, load_env, logger, get_owner

VERSION = "0.1.0"

# ============================================
# 核心函數 — 遞歸下載倉庫目錄
# ============================================

def list_repo_tree(owner: str, repo: str, repo_path: str = "") -> list:
    """
    遞歸列出倉庫指定路徑下的所有檔案。
    返回 [(repo_path, sha, download_url), ...]。
    """
    try:
        contents = rest_request("GET", f"/repos/{owner}/{repo}/contents/{repo_path}")
        if not contents:
            return []

        files = []
        for item in contents:
            if item.get("type") == "file":
                files.append({
                    "path": item.get("path", ""),
                    "sha": item.get("sha", ""),
                    "size": item.get("size", 0),
                    "download_url": item.get("download_url", ""),
                    "html_url": item.get("html_url", ""),
                })
            elif item.get("type") == "dir":
                sub_files = list_repo_tree(owner, repo, item.get("path", ""))
                files.extend(sub_files)
        return files
    except RuntimeError as e:
        if "404" in str(e):
            logger.error(f"Path not found in repo: {repo_path}")
            return []
        raise

def download_file(owner: str, repo: str, repo_path: str, local_path: Path) -> bool:
    """
    下載單個檔案從倉庫到本地。
    使用 GitHub Contents API 獲取 base64 內容。
    """
    try:
        data = rest_request("GET", f"/repos/{owner}/{repo}/contents/{repo_path}")
        if not data:
            return False

        content_b64 = data.get("content", "")
        if not content_b64:
            # 可能是空文件或 LFS 文件
            logger.warning(f"Empty or LFS file: {repo_path}")
            local_path.write_bytes(b"")
            return True

        content = base64.b64decode(content_b64)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
        logger.info(f"Downloaded: {repo_path} -> {local_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {repo_path}: {e}")
        return False

# ============================================
# 核心函數 — 同步倉庫到本地
# ============================================

def check_local_newer(local_path: Path, repo_date_str: str = None) -> dict:
    """
    檢查本地檔案是否比倉庫新。
    返回 {action: "download"/"warn"/"skip", reason: str}
    """
    if not local_path.exists():
        return {
            "action": "download",
            "reason": "File does not exist locally",
        }

    local_mtime = datetime.fromtimestamp(local_path.stat().st_mtime, tz=timezone.utc)

    # 如果沒有倉庫日期，比較 sha（這裡簡化為直接下載，因為 API 不提供文件級修改時間）
    # 實際上 GitHub Contents API 不返回文件級修改時間，只有 commit 歷史才有
    # 所以我們採用簡化策略：若本地存在，默認認為本地較新（保守策略）
    # 用戶可通過 --force 強制覆蓋

    return {
        "action": "warn",
        "reason": f"Local file exists (mtime: {local_mtime.isoformat()}). GitHub date unavailable via Contents API. Use --force to overwrite.",
    }

def sync_repo_to_local(owner: str, repo: str, repo_base_path: str, local_dir: str,
                       dry_run: bool = False, force: bool = False) -> list:
    """
    將倉庫目錄同步到本地。
    若本地檔案較新 → WARN（不覆蓋）。
    若倉庫檔案較新或本地不存在 → DOWNLOAD。
    返回操作報告列表。
    """
    local_root = Path(local_dir).resolve()
    exclude_patterns = {'.git', '__pycache__', '.env', '*.pyc', '.DS_Store', 'temp', 'tmp', 'cache', 'logs'}
    local_root.mkdir(parents=True, exist_ok=True)

    results = []
    repo_files = list_repo_tree(owner, repo, repo_base_path)

    if not repo_files:
        logger.warning(f"No files found at repo path: {repo_base_path}")
        return results

    for rf in repo_files:
        repo_path = rf["path"]

        # 計算本地相對路徑
        if repo_base_path:
            if not repo_path.startswith(repo_base_path):
                continue
            rel_path = repo_path[len(repo_base_path):].lstrip("/")
        else:
            rel_path = repo_path

        # 跳過 .gitkeep 占位文件
        if rel_path.endswith("/.gitkeep"):
            continue

        local_file = local_root / rel_path

        # 檢查本地狀態
        conflict = check_local_newer(local_file)

        action = conflict["action"]
        if action == "warn" and not force:
            results.append({
                "repo_path": repo_path,
                "local_path": rel_path,
                "action": "WARN",
                "reason": conflict["reason"],
            })
            continue

        if not dry_run:
            success = download_file(owner, repo, repo_path, local_file)
            if success:
                results.append({
                    "repo_path": repo_path,
                    "local_path": rel_path,
                    "action": "DOWNLOAD",
                    "reason": "Downloaded from repo",
                })
            else:
                results.append({
                    "repo_path": repo_path,
                    "local_path": rel_path,
                    "action": "FAIL",
                    "reason": "Download failed",
                })
        else:
            results.append({
                "repo_path": repo_path,
                "local_path": rel_path,
                "action": "DRY-RUN",
                "reason": "Would download from repo",
            })

    return results

# ============================================
# CLI 入口
# ============================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Repo Pull — F-007 Download from repo to local")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--repo-name", type=str, required=True, help="Target repo name")
    parser.add_argument("--repo-path", type=str, default="", help="Path inside repo to download (e.g. 'github-restful-api-connector')")
    parser.add_argument("--local-dir", type=str, required=True, help="Local directory to sync to")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without downloading")
    parser.add_argument("--force", action="store_true", help="Force overwrite even if local file exists")
    args = parser.parse_args()

    if args.version:
        print(f"github_repo_pull.py v{VERSION}")
        return

    load_env()
    owner = get_owner()
    if not owner:
        logger.error("GITHUB_OWNER required.")
        sys.exit(1)

    results = sync_repo_to_local(
        owner, args.repo_name, args.repo_path, args.local_dir,
        dry_run=args.dry_run,
        force=args.force,
    )

    # Print report
    print("\n" + "=" * 60)
    print(f"PULL REPORT: {owner}/{args.repo_name}/{args.repo_path} -> {args.local_dir}")
    print("=" * 60)

    for r in results:
        status = r["action"]
        icon = {"DOWNLOAD": "[+]", "WARN": "[!]", "FAIL": "[X]", "DRY-RUN": "[~]"}.get(status, "[?]")
        print(f"{icon} {status:8} {r['local_path']}")
        if r.get("reason"):
            print(f"    -> {r['reason']}")

    # Summary
    download_count = sum(1 for r in results if r["action"] == "DOWNLOAD")
    warn_count = sum(1 for r in results if r["action"] == "WARN")
    fail_count = sum(1 for r in results if r["action"] == "FAIL")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total files: {len(results)}")
    print(f"  Downloaded: {download_count}")
    print(f"  Local newer (report only): {warn_count}")
    print(f"  Failed: {fail_count}")

    if warn_count > 0 and not args.force:
        print(f"\n[!] {warn_count} file(s) exist locally and may be newer. Use --force to overwrite.")
    if fail_count > 0:
        print(f"\n[X] {fail_count} file(s) failed to download.")
        sys.exit(1)

if __name__ == "__main__":
    main()
