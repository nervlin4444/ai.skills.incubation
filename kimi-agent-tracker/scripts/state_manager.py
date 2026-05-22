"""
---
title: "State Manager"
name: "kimi-agent-tracker"
description: "State Manager，Kimi 平台專用自動化追蹤器組件。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T17:15:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
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
from pathlib import Path
from datetime import datetime


def _default_state_path() -> str:
    base = Path(__file__).parent.parent
    config_dir = base / ".config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return str(config_dir / "downloads.json")


def _default_download_dir() -> str:
    base = Path(__file__).parent.parent
    d = base / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def _default_duplicate_dir() -> str:
    base = Path(__file__).parent.parent
    d = base / ".duplicate"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def load_state(path: str = None) -> dict:
    """讀取 downloads.json。文件不存在時返回初始狀態。"""
    path = path or _default_state_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"downloaded": {}, "duplicates": []}


def save_state(state: dict, path: str = None) -> str:
    """保存狀態到 downloads.json。"""
    path = path or _default_state_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return path


def compute_sha256(file_path: str) -> str:
    """計算文件 SHA256 哈希值。"""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_unique_filename(base_dir: str, filename: str) -> str:
    """若文件名已存在，追加 _1, _2, _3... 直到唯一。"""
    base_path = Path(base_dir) / filename
    if not base_path.exists():
        return filename

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        if not (Path(base_dir) / new_name).exists():
            return new_name
        counter += 1


def register_download(state: dict, file_path: str, conversation: str = "") -> dict:
    """註冊新下載：計算 SHA256 → 檢查重複 → 決定保留或移入 .duplicate/。"""
    file_hash = compute_sha256(file_path)
    filename = os.path.basename(file_path)
    download_dir = _default_download_dir()
    duplicate_dir = _default_duplicate_dir()

    if file_hash in state["downloaded"]:
        # 重複檔案：移入 .duplicate/
        dup_name = get_unique_filename(duplicate_dir, filename)
        dup_path = os.path.join(duplicate_dir, dup_name)
        shutil.move(file_path, dup_path)
        state["duplicates"].append({
            "filename": dup_name,
            "original_hash": file_hash,
            "timestamp": datetime.now().isoformat(),
            "conversation": conversation,
        })
    else:
        # 新檔案：保留在 downloads/
        state["downloaded"][file_hash] = {
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
            "conversation": conversation,
        }

    return state


if __name__ == "__main__":
    state = load_state()
    print("Downloaded:", len(state["downloaded"]))
    print("Duplicates:", len(state["duplicates"]))
