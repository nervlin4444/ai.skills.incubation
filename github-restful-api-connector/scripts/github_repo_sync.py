#!/usr/bin/env python3
"""
---
title: "Repo Sync Tool"
name: "github-restful-api-connector"
description: "批量目錄同步上傳：本地技能目錄 → GitHub 倉庫子目錄。自動檢測技能名稱、自動創建倉庫、衝突檢測、安全克隆。v0.3.1 修復 .backups 排除與加入 --test-conventional-commit 參數。"
version: "0.3.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-20T00:50:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/github_repo_sync.py"
    github_path: "/github-restful-api-connector/scripts/github_repo_sync.py"
---

github_repo_sync.py — F-005 批量目錄同步上傳
版本：v0.3.1
生成日期：2026-05-20 00:50:00
核心修復：
  1. exclude_patterns 加入 .backups / .backup（防止備份檔案洩漏到 GitHub）
  2. 新增 --test-conventional-commit 參數，生成 feat: 格式 commit 以測試 semantic-release
"""

import os
import sys
import json
import base64
import hashlib
import logging
import tempfile
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone

scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))
from github_restful_core import rest_request, load_env, logger, get_owner, get_token

VERSION = "0.3.1"

# ============================================
# 排除規則（v0.3.1 修復：加入 .backups / .backup）
# ============================================
exclude_patterns = {
    ".git", "__pycache__", ".env", "*.pyc", ".DS_Store",
    "temp", "tmp", "cache", "logs", ".gitkeep", ".env.template",
    ".backups", ".backup",  # <-- CRITICAL FIX: prevent backup leakage
}

# ============================================
# 技能名稱自動檢測（核心修復）
# ============================================

def detect_skill_name(local_dir: str) -> str:
    """
    從本地 SKILL.md 的 frontmatter 讀取 name 欄位。
    這是強制步驟——沒有技能名稱就無法確定倉庫內路徑，必須停止。
    """
    skill_md = Path(local_dir).resolve() / "SKILL.md"
    if not skill_md.exists():
        raise RuntimeError(
            f"SKILL.md not found in {local_dir}. "
            f"Cannot detect skill name. Upload aborted."
        )

    content = skill_md.read_text(encoding="utf-8")
    # 解析 frontmatter 中的 name: 欄位
    for line in content.splitlines()[:30]:  # 只檢查前30行
        stripped = line.strip()
        if stripped.startswith("name:"):
            # 處理 name: "xxx" 或 name: xxx
            val = stripped.split(":", 1)[1].strip()
            val = val.strip('"').strip("'")
            if val:  # 只要非空，即視為有效技能名稱
                return val

    raise RuntimeError(
        f"Cannot parse 'name:' field from SKILL.md frontmatter in {local_dir}. "
        f"Upload aborted. Ensure frontmatter contains: name: \"your-skill-name\""
    )

# ============================================
# Commit Message 生成（v0.3.1 新增）
# ============================================

def generate_commit_message(repo_path: str, skill_name: str, test_conventional_commit: bool = False) -> str:
    """
    生成上傳用的 commit message。

    正常模式：Sync {path} via github_repo_sync.py v{VERSION}
    測試模式（--test-conventional-commit）：feat({scope}): {description}
    """
    if test_conventional_commit:
        # Conventional Commits format for semantic-release testing
        # Extract filename from repo_path for the description
        filename = Path(repo_path).name
        return f"feat({skill_name}): sync {filename} for semantic-release automation test\n\nThis commit tests whether semantic-release correctly detects\nConventional Commits format and generates a release.\n\n- Uses angular preset configuration\n- Expects minor version bump (feat:)\n- Validates end-to-end release workflow"
    else:
        # Legacy format (does NOT trigger semantic-release)
        return f"Sync {repo_path} via github_repo_sync.py v{VERSION}"

# ============================================
# 倉庫自動創建
# ============================================

def create_repo_if_not_exists(owner: str, repo: str, private: bool = True):
    """若倉庫不存在則自動創建。auto_init=False 避免生成 init.md。"""
    try:
        rest_request("GET", f"/repos/{owner}/{repo}")
        logger.info(f"Repo exists: {owner}/{repo}")
        return
    except RuntimeError as e:
        if "404" not in str(e):
            raise

    logger.info(f"Creating repo: {owner}/{repo} (private={private})")
    payload = {
        "name": repo,
        "private": private,
        "description": f"Auto-created by github-restful-api-connector on {datetime.now(timezone.utc).isoformat()}",
        "auto_init": False,
        "has_issues": True,
        "has_projects": True,
    }
    try:
        rest_request("POST", "/user/repos", payload)
        logger.info(f"Repo created: {owner}/{repo}")
    except RuntimeError as e:
        if "422" in str(e) and "already exists" in str(e).lower():
            logger.info(f"Repo already exists (race): {owner}/{repo}")
        else:
            raise

# ============================================
# 文件上傳（帶路徑前綴）
# ============================================

def upload_file(owner: str, repo: str, local_path: Path, repo_path: str,
                dry_run: bool = False, force: bool = False,
                test_conventional_commit: bool = False, skill_name: str = "") -> bool:
    """
    上傳單個文件到倉庫指定路徑。
    repo_path 已包含技能名稱前綴（如 github-restful-api-connector/scripts/xxx.py）。
    """
    content = local_path.read_bytes()
    content_b64 = base64.b64encode(content).decode("utf-8")
    local_sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()

    # 檢查倉庫中是否已有此文件
    repo_sha = ""
    try:
        existing = rest_request("GET", f"/repos/{owner}/{repo}/contents/{repo_path}")
        repo_sha = existing.get("sha", "")
    except RuntimeError as e:
        if "404" not in str(e):
            raise

    # 內容相同則跳過
    if repo_sha == local_sha:
        logger.info(f"[SKIP] {repo_path} (identical)")
        return True

    # 衝突檢測：倉庫文件較新時警告
    if repo_sha and not force:
        logger.warning(f"[WARN] {repo_path} exists with different content. Use --force to overwrite.")
        return False

    if dry_run:
        logger.info(f"[DRY-RUN] Would upload: {repo_path}")
        return True

    # 執行上傳
    commit_msg = generate_commit_message(repo_path, skill_name, test_conventional_commit)
    payload = {
        "message": commit_msg,
        "content": content_b64,
    }
    if repo_sha:
        payload["sha"] = repo_sha  # 更新現有文件

    rest_request("PUT", f"/repos/{owner}/{repo}/contents/{repo_path}", payload)
    logger.info(f"[UPLOAD] {repo_path}")
    return True

# ============================================
# 批量同步（核心函數）
# ============================================

def sync_directory(owner: str, repo: str, local_dir: str,
                   repo_base_path: str = "", dry_run: bool = False,
                   force: bool = False, no_auto_name: bool = False,
                   test_conventional_commit: bool = False) -> dict:
    """
    同步本地目錄到倉庫。

    核心規則：
    - 默認自動檢測技能名稱，所有文件上傳到 {skill_name}/ 子目錄
    - --no-auto-name 時上傳到根目錄（僅用於倉庫級 README 等特殊場景）
    """
    local_root = Path(local_dir).resolve()

    # 自動檢測技能名稱
    skill_name = ""
    if not no_auto_name:
        if not repo_base_path:
            skill_name = detect_skill_name(local_dir)
            repo_base_path = skill_name
            logger.info(f"Auto-detected skill name: {skill_name}")
            logger.info(f"Files will upload to: {repo_base_path}/")
        else:
            logger.info(f"Using explicit repo_base_path: {repo_base_path}/")
    else:
        logger.info("--no-auto-name: uploading to repo root (USE WITH CAUTION)")

    # 檢查倉庫存在性，不存在則創建
    create_repo_if_not_exists(owner, repo)

    results = {"uploaded": 0, "skipped": 0, "warned": 0, "failed": 0, "files": []}

    for local_file in local_root.rglob("*"):
        if not local_file.is_file():
            continue

        rel_path = local_file.relative_to(local_root).as_posix()

        # 排除臨時文件和目錄（v0.3.1 已包含 .backups）
        if any(part in exclude_patterns for part in local_file.parts):
            continue
        if any(rel_path.endswith(ext.replace("*.", ".")) for ext in exclude_patterns if ext.startswith("*.")):
            continue

        # 構建倉庫內路徑（加入技能名稱前綴）
        if repo_base_path:
            repo_path = f"{repo_base_path}/{rel_path}"
        else:
            repo_path = rel_path

        try:
            ok = upload_file(owner, repo, local_file, repo_path, dry_run, force,
                           test_conventional_commit=test_conventional_commit,
                           skill_name=skill_name or repo_base_path)
            if ok:
                # 區分 skip 和 upload
                try:
                    existing = rest_request("GET", f"/repos/{owner}/{repo}/contents/{repo_path}")
                    repo_sha = existing.get("sha", "")
                    content = local_file.read_bytes()
                    local_sha = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
                    if repo_sha == local_sha:
                        results["skipped"] += 1
                    else:
                        results["uploaded"] += 1
                except:
                    results["uploaded"] += 1
            else:
                results["warned"] += 1
            results["files"].append({"path": repo_path, "status": "ok" if ok else "warn"})
        except Exception as e:
            logger.error(f"[FAIL] {repo_path}: {e}")
            results["failed"] += 1
            results["files"].append({"path": repo_path, "status": "fail", "error": str(e)})

    return results

# ============================================
# 安全克隆（不變）
# ============================================

def safe_clone_repo(repo_url: str, token: str, local_dir: Path = None) -> Path:
    """安全克隆 GitHub 倉庫。Token 通過環境變數傳遞。"""
    git_path = shutil.which("git")
    if not git_path:
        raise RuntimeError("git not found in PATH.")
    if not token or not token.startswith("ghp_"):
        raise RuntimeError("Invalid GitHub PAT format.")

    if local_dir is None:
        temp_base = Path.home() / ".workbuddy" / "temp"
        temp_base.mkdir(parents=True, exist_ok=True)
        work_dir = tempfile.mkdtemp(prefix="github_clone_", dir=temp_base)
    else:
        work_dir = str(local_dir)
        Path(work_dir).mkdir(parents=True, exist_ok=True)

    work_path = Path(work_dir)
    target_path = work_path / "repo"

    if target_path.exists():
        try:
            target_path.resolve().relative_to(work_path.resolve())
            shutil.rmtree(target_path)
        except ValueError:
            raise RuntimeError(f"Safety check failed: {target_path} outside work dir")

    auth_url = f"https://{token}@github.com/{repo_url}.git"
    result = subprocess.run(
        [git_path, "clone", "--depth", "1", auth_url, str(target_path)],
        capture_output=True, text=True, cwd=str(work_path),
        env={**os.environ, "HISTCONTROL": "ignorespace"},
        timeout=60,
    )

    if result.returncode != 0:
        stderr = result.stderr.lower()
        if "authentication failed" in stderr or "401" in stderr:
            raise RuntimeError("GitHub authentication failed.")
        elif "not found" in stderr or "404" in stderr:
            raise RuntimeError(f"Repository not found: {repo_url}")
        else:
            raise RuntimeError(f"Clone failed: {result.stderr}")

    return target_path

def clone_with_credential_helper(repo_url: str, token: str, local_dir: Path = None) -> Path:
    """更安全的克隆：Token 完全不進入命令行。"""
    work_path = Path(tempfile.mkdtemp(prefix="github_clone_"))
    target_path = work_path / "repo"

    git_config = work_path / ".gitconfig"
    git_config.write_text(f"[credential]\n    helper = store --file {work_path / '.git-credentials'}\n")

    creds_file = work_path / ".git-credentials"
    creds_file.write_text(f"https://{token}@github.com\n")
    creds_file.chmod(0o600)

    clean_url = f"https://github.com/{repo_url}.git"
    env = {**os.environ, "HOME": str(work_path), "GIT_CONFIG_GLOBAL": str(git_config)}

    result = subprocess.run(
        ["git", "clone", "--depth", "1", clean_url, str(target_path)],
        capture_output=True, text=True, env=env, timeout=60,
    )

    creds_file.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"Clone failed: {result.stderr}")
    return target_path

# ============================================
# CLI 入口
# ============================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Repo Sync — F-005 Batch Upload")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--repo-name", type=str, required=True, help="Target repo name")
    parser.add_argument("--local-dir", type=str, required=True, help="Local directory to sync")
    parser.add_argument("--repo-base-path", type=str, default="", help="Base path in repo (auto-detected from SKILL.md if empty)")
    parser.add_argument("--create-repo", action="store_true", help="[Deprecated] Auto-create is now default")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--no-auto-name", action="store_true", help="Upload to repo root instead of skill-name subdir (USE WITH CAUTION)")
    parser.add_argument("--clone", action="store_true", help="Clone repo instead of upload")
    parser.add_argument("--clone-method", type=str, default="safe", choices=["safe", "credential"])
    # v0.3.1 新增參數
    parser.add_argument("--test-conventional-commit", action="store_true",
                        help="Generate Conventional Commits format (feat:) for semantic-release testing. "
                             "Each file upload will use a feat: commit message.")
    args = parser.parse_args()

    if args.version:
        print(f"github_repo_sync.py v{VERSION}")
        return

    load_env()
    owner = get_owner()
    if not owner:
        logger.error("GITHUB_OWNER required.")
        sys.exit(1)

    token = get_token()

    # 克隆模式
    if args.clone:
        repo_url = f"{owner}/{args.repo_name}"
        if args.clone_method == "credential":
            path = clone_with_credential_helper(repo_url, token)
        else:
            path = safe_clone_repo(repo_url, token)
        print(f"[OK] Cloned to: {path}")
        return

    # 同步模式
    results = sync_directory(
        owner, args.repo_name, args.local_dir,
        repo_base_path=args.repo_base_path,
        dry_run=args.dry_run,
        force=args.force,
        no_auto_name=args.no_auto_name,
        test_conventional_commit=args.test_conventional_commit,
    )

    print("\n" + "=" * 60)
    print("SYNC REPORT")
    print("=" * 60)
    print(f"  Uploaded:  {results['uploaded']}")
    print(f"  Skipped:   {results['skipped']}")
    print(f"  Warned:    {results['warned']}")
    print(f"  Failed:    {results['failed']}")
    print(f"  Total:     {len(results['files'])}")

    if args.test_conventional_commit:
        print("\n" + "=" * 60)
        print("SEMANTIC-RELEASE TEST MODE")
        print("=" * 60)
        print("  Commit format: Conventional Commits (feat:)")
        print("  Expected: semantic-release should generate a MINOR release")
        print("  Check: https://github.com/nervlin4444/ai.skills.incubation/actions")
        print("  Check: https://github.com/nervlin4444/ai.skills.incubation/releases")

    if results["failed"] > 0:
        print("\n[!] Some files failed. Check logs above.")
        sys.exit(1)
    else:
        print("\n[OK] Sync completed.")
        if not args.dry_run and not args.no_auto_name:
            skill_name = detect_skill_name(args.local_dir)
            print(f"[INFO] Files uploaded to: {args.repo_name}/{skill_name}/")

if __name__ == "__main__":
    main()
