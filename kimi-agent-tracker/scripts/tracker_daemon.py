"""
---
title: Kimi Tracker Daemon
name: kimi-agent-tracker
description: Background daemon for incremental Kimi conversation file downloads. Integrates with kimi_downloader.py v1.3.0 pipeline (discover -> dedup -> download -> record).
version: v1.3.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T16:53:00+0800
fixes: []
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/scripts/tracker_daemon.py"
  github_path: "kimi-agent-tracker/scripts/tracker_daemon.py"
---
"""

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# Constants
DEFAULT_SKILL_DIR = Path.home() / ".workbuddy" / "skills" / "kimi-agent-tracker"
DEFAULT_CONFIG_DIR = DEFAULT_SKILL_DIR / ".config"
DEFAULT_LOGS_DIR = DEFAULT_SKILL_DIR / ".logs"
DEFAULT_PID_FILE = DEFAULT_CONFIG_DIR / "daemon.pid"
DEFAULT_LOG_FILE = DEFAULT_LOGS_DIR / "daemon.log"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"


def _log(level: str, message: str) -> None:
    line = f"[{_timestamp()}] [{level}] {message}"
    print(line, flush=True)
    # Also append to log file
    try:
        DEFAULT_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _load_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: str, data: Any) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        _log("ERROR", f"Failed to save JSON: {e}")


def _read_pid() -> Optional[int]:
    try:
        with open(DEFAULT_PID_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _write_pid(pid: int) -> None:
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(DEFAULT_PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(pid))


def _remove_pid() -> None:
    try:
        DEFAULT_PID_FILE.unlink()
    except Exception:
        pass


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _run_downloader_subprocess(
    mode: str,
    url: Optional[str] = None,
    list_path: Optional[str] = None,
    visible: bool = False,
    timeout_sec: int = 600,
) -> Dict[str, Any]:
    """
    Run kimi_downloader.py as subprocess with given mode.
    Modes: discover, process-pending, download-url, download-list
    """
    script_dir = DEFAULT_SKILL_DIR / "scripts"
    downloader_script = script_dir / "kimi_downloader.py"

    if not downloader_script.exists():
        return {"status": "error", "error": f"Downloader script not found: {downloader_script}"}

    cmd = [sys.executable, str(downloader_script)]

    if mode == "discover" and url:
        cmd.extend(["--url", url, "--discover-only"])
    elif mode == "process-pending":
        cmd.extend(["--process-pending"])
    elif mode == "download-url" and url:
        cmd.extend(["--url", url])
    elif mode == "download-list" and list_path:
        cmd.extend(["--from-list", list_path])
    else:
        return {"status": "error", "error": f"Invalid mode: {mode}"}

    if visible:
        cmd.append("--visible")

    _log("DAEMON", f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )

        output = result.stdout.strip()
        stderr = result.stderr.strip()

        # Try to parse JSON from last line
        json_data = None
        for line in reversed(output.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    json_data = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if result.returncode != 0:
            return {
                "status": "error",
                "returncode": result.returncode,
                "stdout": output[-2000:] if len(output) > 2000 else output,
                "stderr": stderr[-500:] if len(stderr) > 500 else stderr,
            }

        return {
            "status": "success",
            "data": json_data,
            "stdout": output[-1000:] if len(output) > 1000 else output,
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Subprocess timeout after {timeout_sec}s"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _discover_conversations() -> List[Dict[str, str]]:
    """Run conversation lister to get current conversations."""
    lister_script = DEFAULT_SKILL_DIR / "scripts" / "kimi_conversation_lister.py"
    if not lister_script.exists():
        _log("WARN", "Conversation lister not found, using cached conversations.json")
        return []

    try:
        result = subprocess.run(
            [sys.executable, str(lister_script)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            # Parse output for conversation list
            try:
                data = json.loads(result.stdout.strip().splitlines()[-1])
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "conversations" in data:
                    return data["conversations"]
            except Exception:
                pass
    except Exception as e:
        _log("WARN", f"Conversation lister failed: {e}")

    return []


def run_single_cycle(
    visible: bool = False,
    max_conversations: int = 3,
    per_conversation_timeout: int = 600,
) -> Dict[str, Any]:
    """
    Run one full daemon cycle:
        1. List conversations
        2. For each conversation (up to max_conversations):
           a. Discover files (add to pending)
           b. Process pending files for this conversation
        3. Log results
    """
    _log("DAEMON", "Starting single cycle...")
    cycle_start = time.time()

    results = {
        "cycle_start": _timestamp(),
        "conversations_processed": 0,
        "total_success": 0,
        "total_duplicates": 0,
        "total_errors": 0,
        "total_skipped": 0,
        "total_pending_added": 0,
        "details": [],
    }

    # Step 1: Get conversation list
    conversations = _discover_conversations()

    # Fallback: read from cached conversations.json
    if not conversations:
        cached = _load_json(str(DEFAULT_CONFIG_DIR / "conversations.json"), default={})
        if isinstance(cached, dict) and "conversations" in cached:
            conversations = cached["conversations"]
        elif isinstance(cached, list):
            conversations = cached

    _log("DAEMON", f"Found {len(conversations)} conversations")

    # Step 2: Process up to max_conversations
    for i, conv in enumerate(conversations[:max_conversations]):
        if isinstance(conv, dict):
            url = conv.get("url", "")
            title = conv.get("title", "unknown")
        else:
            url = str(conv)
            title = "unknown"

        if not url:
            continue

        conv_start = time.time()
        _log("DAEMON", f"[{i+1}/{min(len(conversations), max_conversations)}] Processing: {title}")

        # Phase A: Discover (add to pending)
        discover_result = _run_downloader_subprocess(
            mode="discover",
            url=url,
            visible=visible,
            timeout_sec=per_conversation_timeout,
        )

        pending_added = 0
        if discover_result.get("status") == "success":
            data = discover_result.get("data", {})
            if isinstance(data, dict):
                pending_added = data.get("pending_added", 0)

        # Phase B: Process pending for this conversation
        download_result = _run_downloader_subprocess(
            mode="download-url",
            url=url,
            visible=visible,
            timeout_sec=per_conversation_timeout,
        )

        conv_success = 0
        conv_dup = 0
        conv_err = 0
        conv_skip = 0

        if download_result.get("status") == "success":
            data = download_result.get("data", {})
            if isinstance(data, dict):
                conv_success = len(data.get("success", []))
                conv_dup = len(data.get("duplicates", []))
                conv_err = len(data.get("errors", []))
                conv_skip = len(data.get("skipped", []))
        else:
            conv_err = 1
            _log("ERROR", f"Download failed for {title}: {download_result.get('error', 'Unknown')}")

        conv_elapsed = time.time() - conv_start
        _log("DAEMON", f"[{title}] ({conv_elapsed:.0f}s): {conv_success} success, {conv_dup} dup, {conv_err} err, {conv_skip} skip, {pending_added} pending")

        cycle_results["details"].append({
            "title": title,
            "url": url,
            "elapsed_sec": round(conv_elapsed, 1),
            "success": conv_success,
            "duplicates": conv_dup,
            "errors": conv_err,
            "skipped": conv_skip,
            "pending_added": pending_added,
        })

        cycle_results["total_success"] += conv_success
        cycle_results["total_duplicates"] += conv_dup
        cycle_results["total_errors"] += conv_err
        cycle_results["total_skipped"] += conv_skip
        cycle_results["total_pending_added"] += pending_added
        cycle_results["conversations_processed"] += 1

    # Step 3: Process any remaining pending items (from previous cycles)
    pending = _load_json(str(DEFAULT_CONFIG_DIR / "pending.json"), default={})
    pending_count = len(pending.get("pending", []))

    if pending_count > 0:
        _log("DAEMON", f"Processing {pending_count} remaining pending items...")
        pending_result = _run_downloader_subprocess(
            mode="process-pending",
            visible=visible,
            timeout_sec=per_conversation_timeout * 2,
        )

        if pending_result.get("status") == "success":
            data = pending_result.get("data", {})
            if isinstance(data, dict):
                cycle_results["total_success"] += data.get("total_success", 0)
                cycle_results["total_duplicates"] += data.get("total_duplicates", 0)
                cycle_results["total_errors"] += data.get("total_errors", 0)
                cycle_results["total_skipped"] += data.get("total_skipped", 0)

    cycle_elapsed = time.time() - cycle_start
    cycle_results["cycle_elapsed_sec"] = round(cycle_elapsed, 1)
    cycle_results["cycle_end"] = _timestamp()

    _log("DAEMON", f"Cycle complete: {cycle_results['total_success']} success, {cycle_results['total_duplicates']} dup, {cycle_results['total_errors']} err, {cycle_results['total_skipped']} skip ({cycle_elapsed:.0f}s)")

    return cycle_results


def run_daemon_loop(
    interval_sec: int = 900,
    visible: bool = False,
    max_conversations: int = 3,
    per_conversation_timeout: int = 600,
) -> None:
    """Run daemon in infinite loop."""
    _log("DAEMON", f"Daemon started (PID: {os.getpid()})")
    _write_pid(os.getpid())

    try:
        while True:
            run_single_cycle(
                visible=visible,
                max_conversations=max_conversations,
                per_conversation_timeout=per_conversation_timeout,
            )
            _log("DAEMON", f"Sleeping for {interval_sec}s...")
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        _log("DAEMON", "Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        _log("ERROR", f"Daemon loop error: {e}")
        traceback.print_exc()
    finally:
        _remove_pid()
        _log("DAEMON", "Daemon stopped.")


def main():
    parser = argparse.ArgumentParser(description="Kimi Tracker Daemon v1.3.0")
    parser.add_argument("--start", action="store_true", help="Start daemon in background")
    parser.add_argument("--stop", action="store_true", help="Stop running daemon")
    parser.add_argument("--status", action="store_true", help="Check daemon status")
    parser.add_argument("--run-once", action="store_true", help="Run single cycle and exit")
    parser.add_argument("--visible", action="store_true", help="Use visible browser mode")
    parser.add_argument("--interval", type=int, default=900, help="Cycle interval in seconds")
    parser.add_argument("--max-conversations", type=int, default=3, help="Max conversations per cycle")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout per conversation in seconds")

    args = parser.parse_args()

    if args.status:
        pid = _read_pid()
        if pid and _is_running(pid):
            print(f"[RUNNING] Daemon PID: {pid}")
        else:
            _remove_pid()
            print("[STOPPED] Daemon not running")
        return

    if args.stop:
        pid = _read_pid()
        if pid and _is_running(pid):
            try:
                os.kill(pid, 15)  # SIGTERM
                time.sleep(1)
                if _is_running(pid):
                    os.kill(pid, 9)  # SIGKILL
                _remove_pid()
                print("[OK] Daemon stopped")
            except Exception as e:
                print(f"[ERROR] Failed to stop daemon: {e}")
        else:
            _remove_pid()
            print("[OK] Daemon not running")
        return

    if args.start:
        pid = _read_pid()
        if pid and _is_running(pid):
            print(f"[WARN] Daemon already running (PID: {pid})")
            return

        # Fork to background (Unix-like)
        try:
            pid = os.fork()
            if pid > 0:
                print(f"[OK] Daemon started (PID: {pid})")
                return
        except (OSError, AttributeError):
            # Windows or fork not available, run in foreground
            pass

        run_daemon_loop(
            interval_sec=args.interval,
            visible=args.visible,
            max_conversations=args.max_conversations,
            per_conversation_timeout=args.timeout,
        )
        return

    if args.run_once:
        run_single_cycle(
            visible=args.visible,
            max_conversations=args.max_conversations,
            per_conversation_timeout=args.timeout,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
