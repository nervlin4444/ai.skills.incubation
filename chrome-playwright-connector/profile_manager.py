"""
---
title: "Profile Manager"
name: "chrome-playwright-connector"
description: "瀏覽器 Persistent Profile 管理工具，負責 profile 目錄創建、驗證、列舉、刪除、複製與網址轉換命名。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T16:39:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/scripts/profile_manager.py"
  github_path: "chrome-playwright-connector/scripts/profile_manager.py"
---
"""

# -*- coding: utf-8 -*-

import os
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse


def _base_dir() -> Path:
    return Path(__file__).parent.parent


def get_profile_path(profile_name: str) -> Path:
    """返回 {baseDir}/profiles/{profile_name}/ 的 Path 對象。目錄不存在時自動創建。"""
    path = _base_dir() / "profiles" / profile_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_profile(profile_name: str) -> dict:
    """檢查 profile 是否可用。"""
    path = get_profile_path(profile_name)
    files = list(path.rglob("*"))
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    last_used = ""
    if files:
        mtimes = [f.stat().st_mtime for f in files if f.is_file()]
        last_used = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(max(mtimes)))
    return {
        "valid": path.exists() and len(files) > 0,
        "size_mb": round(total_size / 1024 / 1024, 2),
        "files_count": len(files),
        "last_used": last_used,
    }


def list_profiles() -> list:
    """返回所有已存在的 profile 名稱列表。"""
    profiles_dir = _base_dir() / "profiles"
    if not profiles_dir.exists():
        return []
    return [d.name for d in profiles_dir.iterdir() if d.is_dir()]


def remove_profile(profile_name: str) -> bool:
    """刪除指定 profile 目錄。返回是否成功。警告：此操作不可逆，必須經主人確認。"""
    path = get_profile_path(profile_name)
    if path.exists():
        shutil.rmtree(path)
        return True
    return False


def clone_profile(source: str, target: str) -> bool:
    """複製現有 profile 到新名稱。用於備份或測試。"""
    src = get_profile_path(source)
    dst = get_profile_path(target)
    if not src.exists():
        return False
    if dst.exists():
        return False
    shutil.copytree(src, dst)
    return True


def url_to_profile_name(url: str) -> str:
    """將網址轉換為 profile 目錄名稱。例如 https://www.kimi.com/ → kimi_com"""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    # 移除 www 前綴
    if netloc.startswith("www."):
        netloc = netloc[4:]
    # 移除端口
    if ":" in netloc:
        netloc = netloc.split(":")[0]
    # 點號換下劃線
    return netloc.replace(".", "_")


if __name__ == "__main__":
    print("Profiles:", list_profiles())
    print("kimi_com valid:", validate_profile("kimi_com"))
    print("url_to_profile:", url_to_profile_name("https://www.kimi.com/chat"))
