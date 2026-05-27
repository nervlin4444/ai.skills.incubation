#!/usr/bin/env python3
"""
---
title: "State Manager"
name: "kimi-agent-tracker"
description: "State management for download deduplication and duplicate archiving."
version: "v4.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-26T09:07:40.603+00:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{baseDir}/scripts/state_manager.py"
  github_path: "kimi-agent-tracker/scripts/state_manager.py"
---
"""


# -*- coding: utf-8 -*-

import os
import json
import hashlib
import shutil
import time
from pathlib import Path


def load_state(path: str = None) -> dict:
    """讀取 downloads.json。文件不存在時返回初始狀態。"""
    if path is None:
        base = Path(__file__).parent.parent
        config_dir = base / ".config"
        config_dir.mkdir(parents=True, exist_ok=True)
        path = str(config_dir / "downloads.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"downloaded": {}, "duplicates": []}


def save_state(state: dict, path: str = None) -> str:
    """保存狀態到 downloads.json。"""
    if path is None:
        base = Path(__file__).parent.parent
        config_dir = base / ".config"
        config_dir.mkdir(parents=True, exist_ok=True)
        path = str(config_dir / "downloads.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return path


def compute_sha256(file_path: str) -> str:
    """計算文件 SHA256 哈希值。"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_unique_filename(base_dir: str, filename: str) -> str:
    """若文件名已存在，追加 _1, _2, _3... 直到唯一。"""
    base = Path(base_dir)
    target = base / filename
    if not target.exists():
        return filename
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        if not (base / new_name).exists():
            return new_name
        counter += 1


def register_download(state: dict, file_path: str, conversation: str) -> dict:
    """註冊新下載：計算 SHA256 → 檢查重複 → 決定保留或移入 .duplicate/。"""
    sha = compute_sha256(file_path)
    if sha in state.get("downloaded", {}):
        # 重複檔案：移入 .duplicate/
        base = Path(file_path).parent.parent
        dup_dir = base / ".duplicate"
        dup_dir.mkdir(parents=True, exist_ok=True)
        dup_path = dup_dir / Path(file_path).name
        shutil.move(file_path, str(dup_path))
        state["duplicates"].append({
            "sha256": sha,
            "original": state["downloaded"][sha].get("path"),
            "duplicate": str(dup_path),
            "conversation": conversation,
        })
    else:
        state["downloaded"][sha] = {
            "path": file_path,
            "conversation": conversation,
            "timestamp": time.time(),
        }
    return state


if __name__ == "__main__":
    state = load_state()
    print("Downloaded:", len(state["downloaded"]))
    print("Duplicates:", len(state["duplicates"]))
