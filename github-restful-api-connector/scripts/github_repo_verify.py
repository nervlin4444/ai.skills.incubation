#!/usr/bin/env python3
"""
---
title: "Repo Verify Tool"
name: "github-restful-api-connector"
description: "雙向驗證工具：本地檔案與 GitHub 倉庫內容比對。用於腳本更新後或初次部署時確認同步完整性。"
version: "0.2.0"
github_repository: "nervlin4444/ai.skills.devops"
target_branch: "main"
updated_at: "2026-05-17T17:38:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/github_repo_verify.py"
    github_path: "/github-restful-api-connector/scripts/github_repo_verify.py"
---

github_repo_verify.py — F-006 雙向驗證工具
驗證本地目錄與 GitHub 倉庫內容是否一致。
適用場景：腳本更新後驗證、初次部署後確認、定期一致性檢查。
版本：v0.2.0
生成日期：2026-05-17 17:38:00
新增：--test-pat 參數，獨立診斷 PAT 有效性
"""

import os
import sys
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone

scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))
from github_restful_core import (
    rest_request, load_env, logger, get_owner,
    test_pat_diagnostic, get_token, get_repo
)

VERSION = "0.2.0"

# ============================================
# 核心函數 — 倉庫內容讀取
# ============================================

def list_repo_contents(owner: str, repo: str, path: str = "") -> list:
    """遞歸列出倉庫指定路徑下的所有檔案。返回 [(path, sha, size), ...]。"""
    try:
        contents = rest_request("GET", f"/repos/{owner}/{repo}/contents/{path}")
        if not contents:
            return []

        files = []
        for item in contents:
            if item.get("type") == "file":
                files.append({
                    "path": item.get("path", ""),
                    "sha": item.get("sha", ""),
                    "size": item.get("size", 0),
                })
            elif item.get("type") == "dir":
                sub_files = list_repo_contents(owner, repo, item.get("path", ""))
                files.extend(sub_files)
        return files
    except RuntimeError as e:
        if "404" in str(e):
            return []
        raise

def get_repo_file_sha(owner: str, repo: str, path: str) -> str:
    """獲取倉庫中指定檔案的 sha。不存在返回空字符串。"""
    try:
        data = rest_request("GET", f"/repos/{owner}/{repo}/contents/{path}")
        return data.get("sha", "") if data else ""
    except RuntimeError as e:
        if "404" in str(e):
            return ""
        raise

# ============================================
# 核心函數 — 本地內容讀取
# ============================================

def compute_git_blob_sha(filepath: Path) -> str:
    """計算本地文件的 Git blob sha。"""
    content = filepath.read_bytes()
    header = f"blob {len(content)}\0".encode("utf-8")
    blob = header + content
    return hashlib.sha1(blob).hexdigest()

def list_local_files(local_dir: str, exclude_patterns: set = None) -> list:
    """列出本地目錄下所有檔案。返回 [(rel_path, full_path, sha), ...]。"""
    if exclude_patterns is None:
        exclude_patterns = {".git", "__pycache__", ".env", "*.pyc", ".DS_Store", "temp", "tmp", "cache", "logs", ".gitkeep"}

    local_root = Path(local_dir).resolve()
    files = []

    for local_file in local_root.rglob("*"):
        if not local_file.is_file():
            continue
        rel_path = local_file.relative_to(local_root).as_posix()
        if any(part in exclude_patterns for part in local_file.parts):
            continue
        if any(rel_path.endswith(ext.replace("*.", ".")) for ext in exclude_patterns if ext.startswith("*.")):
            continue

        sha = compute_git_blob_sha(local_file)
        files.append({
            "path": rel_path,
            "full_path": str(local_file),
            "sha": sha,
            "size": local_file.stat().st_size,
        })

    return files

# ============================================
# 核心函數 — 雙向驗證
# ============================================

def verify_local_to_repo(owner: str, repo: str, local_dir: str, repo_base_path: str = "") -> dict:
    """
    驗證方向 A：本地 → 倉庫
    檢查本地所有檔案是否都已正確上傳到倉庫，且內容一致。
    返回 {verified: [], missing: [], mismatch: []}
    """
    local_files = list_local_files(local_dir)
    report = {"verified": [], "missing": [], "mismatch": []}

    for lf in local_files:
        repo_path = f"{repo_base_path}/{lf['path']}" if repo_base_path else lf["path"]
        repo_sha = get_repo_file_sha(owner, repo, repo_path)

        if not repo_sha:
            report["missing"].append({
                "local_path": lf["path"],
                "repo_path": repo_path,
                "reason": "Not found in repo",
            })
        elif repo_sha == lf["sha"]:
            report["verified"].append({
                "local_path": lf["path"],
                "repo_path": repo_path,
                "sha": repo_sha[:8],
            })
        else:
            report["mismatch"].append({
                "local_path": lf["path"],
                "repo_path": repo_path,
                "local_sha": lf["sha"][:8],
                "repo_sha": repo_sha[:8],
            })

    return report

def verify_repo_to_local(owner: str, repo: str, local_dir: str, repo_base_path: str = "") -> dict:
    """
    驗證方向 B：倉庫 → 本地
    檢查倉庫中的檔案是否都在本地存在，且內容一致。
    返回 {verified: [], missing: [], mismatch: [], extra: []}
    """
    repo_files = list_repo_contents(owner, repo, repo_base_path)
    local_root = Path(local_dir).resolve()
    report = {"verified": [], "missing": [], "mismatch": [], "extra": []}

    for rf in repo_files:
        # 跳過 .gitkeep 占位文件
        if rf["path"].endswith("/.gitkeep"):
            continue

        # 計算相對路徑
        if repo_base_path:
            if not rf["path"].startswith(repo_base_path):
                continue
            rel_path = rf["path"][len(repo_base_path):].lstrip("/")
        else:
            rel_path = rf["path"]

        local_file = local_root / rel_path

        if not local_file.exists():
            report["missing"].append({
                "repo_path": rf["path"],
                "local_path": rel_path,
                "reason": "Not found locally",
            })
            continue

        local_sha = compute_git_blob_sha(local_file)
        if local_sha == rf["sha"]:
            report["verified"].append({
                "repo_path": rf["path"],
                "local_path": rel_path,
                "sha": rf["sha"][:8],
            })
        else:
            report["mismatch"].append({
                "repo_path": rf["path"],
                "local_path": rel_path,
                "local_sha": local_sha[:8],
                "repo_sha": rf["sha"][:8],
            })

    # 檢查本地是否有倉庫中沒有的額外檔案
    local_files = list_local_files(local_dir)
    local_paths = {lf["path"] for lf in local_files}
    repo_paths = set()
    for rf in repo_files:
        if repo_base_path:
            if rf["path"].startswith(repo_base_path):
                repo_paths.add(rf["path"][len(repo_base_path):].lstrip("/"))
        else:
            repo_paths.add(rf["path"])

    for lp in local_paths:
        if lp not in repo_paths and not any(p.endswith("/.gitkeep") for p in repo_paths if p.startswith(lp)):
            report["extra"].append({
                "local_path": lp,
                "reason": "Exists locally but not in repo",
            })

    return report

def run_full_verification(owner: str, repo: str, local_dir: str, repo_base_path: str = "") -> dict:
    """
    執行雙向完整驗證。
    返回 {local_to_repo: {}, repo_to_local: {}, summary: {}}
    """
    a_report = verify_local_to_repo(owner, repo, local_dir, repo_base_path)
    b_report = verify_repo_to_local(owner, repo, local_dir, repo_base_path)

    a_ok = len(a_report["missing"]) == 0 and len(a_report["mismatch"]) == 0
    b_ok = len(b_report["missing"]) == 0 and len(b_report["mismatch"]) == 0

    summary = {
        "local_to_repo_ok": a_ok,
        "repo_to_local_ok": b_ok,
        "fully_synced": a_ok and b_ok,
        "total_local_files": len(a_report["verified"]) + len(a_report["missing"]) + len(a_report["mismatch"]),
        "total_repo_files": len(b_report["verified"]) + len(b_report["missing"]) + len(b_report["mismatch"]),
        "verified_count": len(a_report["verified"]),
        "missing_count": len(a_report["missing"]) + len(b_report["missing"]),
        "mismatch_count": len(a_report["mismatch"]) + len(b_report["mismatch"]),
        "extra_local_count": len(b_report["extra"]),
    }

    return {
        "local_to_repo": a_report,
        "repo_to_local": b_report,
        "summary": summary,
    }

# ============================================
# PAT 測試診斷輸出
# ============================================

def print_pat_report(report: dict):
    """格式化輸出 PAT 診斷報告。"""
    print("=" * 60)
    print("PAT DIAGNOSTIC REPORT")
    print("=" * 60)

    # Token 信息
    print("\n[Token Info]")
    print(f"  Loaded from .env: {'YES' if report['token_loaded'] else 'NO'}")
    print(f"  Prefix: {report['token_prefix']}")
    print(f"  Length: {report['token_length']} chars")
    print(f"  Format OK (ghp_ + 40): {'YES' if report['token_format_ok'] else 'NO'}")

    # API 連通
    print("\n[API Reachability]")
    print(f"  GitHub API reachable: {'YES' if report['api_reachable'] else 'NO'}")

    # 認證結果
    print("\n[Authentication]")
    print(f"  Auth success: {'YES' if report['auth_success'] else 'NO'}")
    if report['user_login']:
        print(f"  Authenticated as: {report['user_login']}")

    # 速率限制
    if report.get('rate_limit'):
        rl = report['rate_limit']
        print("\n[Rate Limit]")
        print(f"  Remaining: {rl.get('remaining', '?')}/{rl.get('limit', '?')}")
        reset_ts = rl.get('reset_timestamp', 0)
        if reset_ts:
            reset_dt = datetime.fromtimestamp(reset_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            print(f"  Resets at: {reset_dt}")

    # 倉庫檢查
    print("\n[Repository Check]")
    if report['repo_name']:
        print(f"  Target repo: {report['repo_name']}")
        print(f"  Repo exists: {'YES' if report['repo_exists'] else 'NO'}")
        print(f"  Repo accessible: {'YES' if report['repo_accessible'] else 'NO'}")
    else:
        print("  GITHUB_OWNER/GITHUB_REPO not set — skipping repo check")

    # 錯誤匯總
    if report['errors']:
        print("\n[ERRORS]")
        for err in report['errors']:
            print(f"  ✗ {err}")
    else:
        print("\n[ERRORS] None")

    # 總結
    print("\n" + "=" * 60)
    if report['auth_success']:
        if report['repo_exists'] or not report['repo_name']:
            print("RESULT: PAT is VALID and ready for sync operations.")
        else:
            print("RESULT: PAT valid, repo missing — sync will auto-create repo.")
    else:
        print("RESULT: PAT INVALID — check token value and 'repo' scope.")
    print("=" * 60)

# ============================================
# CLI 入口
# ============================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Repo Verify — F-006 Bidirectional Verification")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--repo-name", type=str, required=False, help="Target repo name")
    parser.add_argument("--local-dir", type=str, required=False, help="Local directory to verify against")
    parser.add_argument("--repo-base-path", type=str, default="", help="Base path in repo")
    parser.add_argument("--direction", type=str, default="both", choices=["both", "local-to-repo", "repo-to-local"],
                        help="Verification direction")
    parser.add_argument("--json", action="store_true", help="Output raw JSON report")
    parser.add_argument("--test-pat", action="store_true", help="Test PAT validity before verification")
    args = parser.parse_args()

    if args.version:
        print(f"github_repo_verify.py v{VERSION}")
        return

    # --test-pat 模式：獨立診斷 PAT
    if args.test_pat:
        report = test_pat_diagnostic()
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return
        print_pat_report(report)
        if not report["auth_success"]:
            sys.exit(1)
        return

    # 驗證模式：需要 repo-name + local-dir
    if not args.repo_name or not args.local_dir:
        print("[ERROR] --repo-name and --local-dir required for verification.")
        print("        Use --test-pat to diagnose PAT issues without these args.")
        sys.exit(1)

    load_env()
    owner = get_owner()
    if not owner:
        logger.error("GITHUB_OWNER required.")
        sys.exit(1)

    # Run verification
    if args.direction == "local-to-repo":
        report = verify_local_to_repo(owner, args.repo_name, args.local_dir, args.repo_base_path)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return

        print("=" * 60)
        print("VERIFICATION: Local → Repo")
        print("=" * 60)
        _print_single_report(report)

    elif args.direction == "repo-to-local":
        report = verify_repo_to_local(owner, args.repo_name, args.local_dir, args.repo_base_path)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return

        print("=" * 60)
        print("VERIFICATION: Repo → Local")
        print("=" * 60)
        _print_single_report(report, show_extra=True)

    else:
        full_report = run_full_verification(owner, args.repo_name, args.local_dir, args.repo_base_path)
        if args.json:
            print(json.dumps(full_report, indent=2, ensure_ascii=False))
            return

        print("=" * 60)
        print("FULL VERIFICATION REPORT")
        print("=" * 60)

        # Direction A
        print("\n[Direction A] Local → Repo")
        print("-" * 40)
        _print_single_report(full_report["local_to_repo"])

        # Direction B
        print("\n[Direction B] Repo → Local")
        print("-" * 40)
        _print_single_report(full_report["repo_to_local"], show_extra=True)

        # Summary
        summary = full_report["summary"]
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  Local → Repo OK: {'YES' if summary['local_to_repo_ok'] else 'NO'}")
        print(f"  Repo → Local OK: {'YES' if summary['repo_to_local_ok'] else 'NO'}")
        print(f"  FULLY SYNCED: {'YES ✓' if summary['fully_synced'] else 'NO ✗'}")
        print(f"  Total local files checked: {summary['total_local_files']}")
        print(f"  Total repo files checked: {summary['total_repo_files']}")
        print(f"  Verified (sha match): {summary['verified_count']}")
        print(f"  Missing: {summary['missing_count']}")
        print(f"  Mismatch: {summary['mismatch_count']}")
        print(f"  Extra local files: {summary['extra_local_count']}")

        if not summary["fully_synced"]:
            print("\n[!] Sync incomplete. Run github_repo_sync.py to fix.")
            sys.exit(1)
        else:
            print("\n[OK] All files are fully synchronized.")

def _print_single_report(report: dict, show_extra: bool = False):
    """Helper to print a single-direction report."""
    if report.get("verified"):
        print(f"  [OK] Verified: {len(report['verified'])} files")
        for item in report["verified"]:
            path = item.get("local_path", item.get("repo_path", "unknown"))
            print(f"       ✓ {path}")

    if report.get("missing"):
        print(f"\n  [FAIL] Missing: {len(report['missing'])} files")
        for item in report["missing"]:
            local = item.get("local_path", "-")
            repo = item.get("repo_path", "-")
            print(f"       ✗ {local} <-> {repo}")

    if report.get("mismatch"):
        print(f"\n  [WARN] Mismatch: {len(report['mismatch'])} files")
        for item in report["mismatch"]:
            local = item.get("local_path", item.get("repo_path", "unknown"))
            local_sha = item.get("local_sha", "?")
            repo_sha = item.get("repo_sha", "?")
            print(f"       ! {local} (local:{local_sha} repo:{repo_sha})")

    if show_extra and report.get("extra"):
        print(f"\n  [INFO] Extra local files: {len(report['extra'])} files")
        for item in report["extra"]:
            print(f"       + {item['local_path']}")

if __name__ == "__main__":
    main()
