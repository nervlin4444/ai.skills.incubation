"""
---
title: "Kimi Download Manager"
name: "kimi-agent-tracker"
description: "Business logic core for Kimi conversation file downloads. Fixed step registry, HEAD pre-check, incremental timeout, cycle safety. Delegates browser automation to downloader and lister."
version: "v5.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-27T00:48:55.090+00:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{baseDir}/scripts/kimi_download_manager.py"
  github_path: "kimi-agent-tracker/scripts/kimi_download_manager.py"
---
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Inject skill scripts into path for core module imports
_SKILL_DIR = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _SKILL_DIR / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from core_path_utils import (
    get_skill_dir,
    get_config_dir,
    get_data_dir,
    get_download_dir,
    get_tracker_config_path,
    get_conversations_json_path,
    get_download_state_path,
    ensure_dir,
)
from core_logger import CoreLogger, get_default_logger


# Constants
DEFAULT_TIMEOUT_SEC = 20
TIMEOUT_INCREMENT_SEC = 20
MAX_TIMEOUT_SEC = 120
SAFETY_MARGIN_SEC = 30


# Config I/O
def load_tracker_config() -> dict:
    cfg_path = get_tracker_config_path()
    if not cfg_path.exists():
        return {}
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_conversations_json(conversations: list) -> Path:
    conv_path = get_conversations_json_path()
    ensure_dir("{baseDir}/config")
    with open(conv_path, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    return conv_path


def load_conversations_json() -> list:
    conv_path = get_conversations_json_path()
    if not conv_path.exists():
        return []
    with open(conv_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data if isinstance(data, list) else []


def load_download_state() -> dict:
    state_path = get_download_state_path()
    if not state_path.exists():
        return {"conversations": [], "global_stats": {}}
    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_download_state(state: dict) -> Path:
    state_path = get_download_state_path()
    ensure_dir("{baseDir}/data")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state_path


# Subprocess helpers
def run_lister(auto_discover: bool = True, target_url: str = "") -> tuple:
    lister_script = _SCRIPTS_DIR / "kimi_conversation_lister.py"
    if not lister_script.exists():
        return [], "Lister not found: " + str(lister_script)
    cmd = [sys.executable, str(lister_script)]
    if not auto_discover and target_url:
        cmd.extend(["--url", target_url])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return [], "Lister exit " + str(result.returncode) + ": " + result.stderr[:500]
        conversations = load_conversations_json()
        return conversations, ""
    except subprocess.TimeoutExpired:
        return [], "Lister timed out after 120s"
    except Exception as e:
        return [], "Lister exception: " + str(e)


def run_downloader(url: str, max_files: int, visible: bool, timeout_sec: int) -> tuple:
    dl_script = _SCRIPTS_DIR / "kimi_downloader.py"
    if not dl_script.exists():
        return {}, "Downloader not found: " + str(dl_script)
    cmd = [
        sys.executable,
        str(dl_script),
        "--url", url,
        "--max-files", str(max_files),
        "--timeout", str(timeout_sec),
    ]
    if visible:
        cmd.append("--visible")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec + 60)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        parsed = {}
        if stdout:
            for line in reversed(stdout.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        parsed = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
                if line.startswith("[") and line.endswith("]"):
                    try:
                        parsed = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
        return parsed, stderr if result.returncode != 0 else ""
    except subprocess.TimeoutExpired:
        return {}, "Downloader timed out"
    except Exception as e:
        return {}, "Downloader exception: " + str(e)


# HEAD pre-check
def head_pre_check(url: str) -> dict:
    import urllib.request
    result = {"status": 0, "content_length": -1, "filename": "", "error": ""}
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result["status"] = resp.status
            result["content_length"] = int(resp.headers.get("Content-Length", -1))
            cd = resp.headers.get("Content-Disposition", "")
            if "filename=" in cd:
                result["filename"] = cd.split("filename=")[1].strip('"')
    except Exception as e:
        result["error"] = str(e)
    return result


# Step registry helpers
def step(log: CoreLogger, step_id: str, message: str):
    log.step(step_id, message)


def metric(log: CoreLogger, name: str, value: str):
    log.metric(name, value)


# Main Download Manager cycle
def run_cycle(log: CoreLogger, poll_interval_sec: int = 300) -> dict:
    cycle_start = time.time()
    cycle_result = {
        "cycle_start": cycle_start,
        "cycle_end": 0.0,
        "conversations_processed": 0,
        "files_downloaded": 0,
        "files_skipped": 0,
        "files_error": 0,
        "errors": [],
    }

    step(log, "S001", "Cycle started")

    step(log, "S002", "Loading tracker_config.json")
    config = load_tracker_config()
    if not config:
        step(log, "S002-E", "tracker_config.json empty or missing")
        cycle_result["errors"].append("Config missing")
        return cycle_result
    metric(log, "config_loaded", "true")

    conversations_cfg = config.get("conversations", [])
    if not conversations_cfg:
        step(log, "S003-E", "No conversations configured")
        cycle_result["errors"].append("No conversations")
        return cycle_result

    has_placeholder = any(
        isinstance(c, dict) and ("PLACEHOLDER" in c.get("url", "") or not c.get("url"))
        for c in conversations_cfg
    )

    conversations = []
    if has_placeholder:
        step(log, "S004", "Placeholder detected, auto-discovering conversations")
        discovered, err = run_lister(auto_discover=True)
        if err:
            step(log, "S004-E", "Auto-discovery failed: " + err)
            cycle_result["errors"].append("Lister: " + err)
            return cycle_result
        if not discovered:
            step(log, "S004-E", "Auto-discovery returned empty")
            cycle_result["errors"].append("Discovery empty")
            return cycle_result
        conversations = discovered
        save_conversations_json(conversations)
        step(log, "S005", "Saved " + str(len(conversations)) + " conversations to config/conversations.json")
    else:
        step(log, "S004", "Using configured conversation URLs")
        validated = []
        for c in conversations_cfg:
            url = c.get("url", "") if isinstance(c, dict) else str(c)
            if not url:
                continue
            step(log, "S005", "Validating URL: " + url)
            single, err = run_lister(auto_discover=False, target_url=url)
            if err:
                step(log, "S005-E", "Validation failed for " + url + ": " + err)
                cycle_result["errors"].append("Validate " + url + ": " + err)
                continue
            if single:
                validated.extend(single)
        if not validated:
            step(log, "S005-E", "No valid conversations after manual validation")
            cycle_result["errors"].append("All validations failed")
            return cycle_result
        conversations = validated
        save_conversations_json(conversations)
        step(log, "S005", "Saved " + str(len(conversations)) + " validated conversations")

    step(log, "S006", "Loading download state")
    state = load_download_state()
    metric(log, "state_conversations", str(len(state.get("conversations", []))))

    visible = config.get("headless", True) is False
    if config.get("debug_mode", False):
        visible = True
    step(log, "S007", "Browser visible=" + str(visible))
    metric(log, "browser_visible", str(visible))

    max_files_per_run = config.get("max_files_per_run", 10)
    for idx, conv in enumerate(conversations):
        conv_url = conv.get("url", "") if isinstance(conv, dict) else str(conv)
        conv_label = conv.get("label", conv.get("title", "conv-" + str(idx))) if isinstance(conv, dict) else "conv-" + str(idx)
        if not conv_url:
            continue

        step(log, "S008", "[" + str(idx+1) + "/" + str(len(conversations)) + "] Processing: " + conv_label)
        metric(log, "conv_url", conv_url)

        elapsed = time.time() - cycle_start
        remaining = poll_interval_sec - elapsed
        if remaining < SAFETY_MARGIN_SEC:
            step(log, "S009-W", "Cycle time approaching limit (" + str(int(elapsed)) + "s / " + str(poll_interval_sec) + "s). Breaking loop.")
            cycle_result["errors"].append("Cycle time limit approaching")
            break

        conv_state = next((c for c in state.get("conversations", []) if c.get("url") == conv_url), None)
        prev_timeout = DEFAULT_TIMEOUT_SEC
        if conv_state:
            pending_files = [f for f in conv_state.get("files", []) if f.get("status") == "pending"]
            if pending_files:
                attempt_counts = [f.get("attempt_count", 0) for f in pending_files]
                max_attempts = max(attempt_counts) if attempt_counts else 0
                prev_timeout = min(DEFAULT_TIMEOUT_SEC + (max_attempts * TIMEOUT_INCREMENT_SEC), MAX_TIMEOUT_SEC)

        step(log, "S010", "Using timeout=" + str(prev_timeout) + "s for " + conv_label)
        metric(log, "conv_timeout", str(prev_timeout))

        dl_result, dl_err = run_downloader(conv_url, max_files_per_run, visible, prev_timeout)
        if dl_err:
            step(log, "S011-E", "Downloader error for " + conv_label + ": " + dl_err)
            cycle_result["errors"].append("DL " + conv_label + ": " + dl_err)
            continue

        success_count = len(dl_result.get("success", [])) if isinstance(dl_result, dict) else 0
        skip_count = len(dl_result.get("skipped", [])) if isinstance(dl_result, dict) else 0
        error_count = len(dl_result.get("errors", [])) if isinstance(dl_result, dict) else 0
        cycle_result["files_downloaded"] += success_count
        cycle_result["files_skipped"] += skip_count
        cycle_result["files_error"] += error_count
        cycle_result["conversations_processed"] += 1

        step(log, "S012", conv_label + ": " + str(success_count) + " success, " + str(skip_count) + " skip, " + str(error_count) + " error")
        metric(log, "conv_success", str(success_count))
        metric(log, "conv_skip", str(skip_count))
        metric(log, "conv_error", str(error_count))

    cycle_end = time.time()
    cycle_result["cycle_end"] = cycle_end
    total_elapsed = cycle_end - cycle_start
    step(log, "S013", "Cycle complete: " + str(cycle_result["conversations_processed"]) + " conv, " + str(cycle_result["files_downloaded"]) + " dl, " + str(cycle_result["files_error"]) + " err, " + str(int(total_elapsed)) + "s")
    metric(log, "cycle_elapsed_sec", str(int(total_elapsed)))
    metric(log, "cycle_total_success", str(cycle_result["files_downloaded"]))
    metric(log, "cycle_total_error", str(cycle_result["files_error"]))

    save_download_state(state)
    step(log, "S014", "Download state saved")

    return cycle_result


# Entry point for daemon or manual invocation
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Kimi Download Manager")
    parser.add_argument("--interval", type=int, default=300, help="Poll interval in seconds for cycle safety check")
    parser.add_argument("--once", action="store_true", help="Run single cycle and exit")
    args = parser.parse_args()

    log = get_default_logger("DM")
    log.info("Download Manager starting")

    if args.once:
        result = run_cycle(log, args.interval)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        log.info("Daemon mode: run_cycle should be called by tracker_daemon")
        result = run_cycle(log, args.interval)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
