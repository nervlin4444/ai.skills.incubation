"""
---
title: Kimi Agent Tracker Daemon
description: F-005 Background daemon that periodically checks Kimi conversations and downloads new files using content extraction strategy (v1.2.0+).
version: "1.2.1"
name: kimi-agent-tracker
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T15:01:00+00:00"
auth_config:
  provider: kimi
  auth_method: persistent_profile
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/scripts/tracker_daemon.py"
  github_path: "kimi-agent-tracker/scripts/tracker_daemon.py"
---
"""

import os
import sys
import json
import time
import signal
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"


def log_event(msg):
    print(f"[{_now_iso()}] {msg}")


def get_base_dir():
    return Path(__file__).resolve().parent.parent


def load_config():
    p = get_base_dir() / ".config" / "kimi_tracker_config.json"
    if not p.exists():
        log_event(f"[ERROR] Config not found: {p}")
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def get_pid_file():
    return get_base_dir() / ".config" / "daemon.pid"


def get_log_file():
    return get_base_dir() / ".logs" / "daemon.log"


def ensure_dir(path):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def get_daemon_pid():
    pid_file = get_pid_file()
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            if is_running(pid):
                return pid
        except (ValueError, OSError):
            pass
    return None


def write_pid(pid):
    ensure_dir(get_pid_file().parent)
    get_pid_file().write_text(str(pid))


def remove_pid():
    pid_file = get_pid_file()
    if pid_file.exists():
        pid_file.unlink()


def run_login_validate():
    """Run login manager validate and return True/False."""
    script = get_base_dir() / "scripts" / "kimi_login_manager.py"
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--validate"],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout + result.stderr
        log_event(f"[VALIDATE] {output.strip()}")
        return "Login valid: True" in output or "valid: True" in output.lower()
    except Exception as e:
        log_event(f"[ERROR] Login validation failed: {e}")
        return False


def run_conversation_list(count=10):
    """Run conversation lister and return path to conversations.json."""
    script = get_base_dir() / "scripts" / "kimi_conversation_lister.py"
    config = load_config()
    visible = config.get("daemon", {}).get("visible", False)
    try:
        cmd = [sys.executable, str(script), "--count", str(count)]
        if visible:
            cmd.append("--visible")
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        output = result.stdout + result.stderr
        log_event(f"[LIST] {output.strip()[-200:]}")  # Last 200 chars
        conv_file = get_base_dir() / ".config" / "conversations.json"
        if conv_file.exists():
            return str(conv_file)
    except Exception as e:
        log_event(f"[ERROR] Conversation listing failed: {e}")
    return None


def run_download(conv_file):
    """Run downloader on conversation list."""
    script = get_base_dir() / "scripts" / "kimi_downloader.py"
    config = load_config()
    visible = config.get("daemon", {}).get("visible", False)
    try:
        cmd = [sys.executable, str(script), "--from-list", conv_file]
        if visible:
            cmd.append("--visible")
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        output = result.stdout + result.stderr
        log_event(f"[DOWNLOAD] {output.strip()[-300:]}")  # Last 300 chars
        # Parse JSON result for summary
        try:
            # Find JSON output in last lines
            lines = output.strip().split("\n")
            for line in reversed(lines):
                if line.strip().startswith("{"):
                    data = json.loads(line.strip())
                    success = len(data.get("success", []))
                    dup = len(data.get("duplicates", []))
                    err = len(data.get("errors", []))
                    skip = len(data.get("skipped", []))
                    log_event(f"[DOWNLOAD] Result: {success} success, {dup} duplicates, {err} errors, {skip} skipped")
                    break
        except Exception:
            pass
        return True
    except subprocess.TimeoutExpired:
        log_event("[ERROR] Download timeout (300s)")
        return False
    except Exception as e:
        log_event(f"[ERROR] Download failed: {e}")
        return False


def daemon_cycle(config):
    """Execute one daemon cycle: validate -> list -> download."""
    log_event("Starting cycle...")

    # Step 1: Validate login
    if not run_login_validate():
        log_event("[ERROR] Login invalid, aborting cycle.")
        return False

    # Step 2: List conversations
    count = config.get("daemon", {}).get("conversation_count", 10)
    conv_file = run_conversation_list(count)
    if not conv_file:
        log_event("[ERROR] Failed to list conversations, aborting cycle.")
        return False

    # Step 3: Download files
    run_download(conv_file)

    log_event("Cycle complete.")
    return True


def daemon_main(config):
    """Main daemon loop."""
    interval = config.get("daemon", {}).get("interval_sec", 900)
    log_event(f"Daemon started (PID: {os.getpid()}), interval={interval}s")
    write_pid(os.getpid())

    try:
        while True:
            daemon_cycle(config)
            log_event(f"Sleeping {interval}s...")
            time.sleep(interval)
    except KeyboardInterrupt:
        log_event("Daemon interrupted by user.")
    finally:
        remove_pid()
        log_event("Daemon stopped.")


def start_daemon(config):
    """Start daemon in background."""
    existing_pid = get_daemon_pid()
    if existing_pid:
        log_event(f"[ERROR] Daemon already running (PID {existing_pid})")
        return False

    # Fork to background
    try:
        pid = os.fork()
        if pid > 0:
            # Parent process
            log_event(f"[OK] Daemon started (PID: {pid})")
            write_pid(pid)
            return True
        else:
            # Child process - daemon
            os.setsid()
            daemon_main(config)
    except OSError as e:
        log_event(f"[ERROR] Failed to fork daemon: {e}")
        return False


def stop_daemon():
    """Stop running daemon."""
    pid = get_daemon_pid()
    if not pid:
        log_event("[STOPPED] Daemon not running")
        return True

    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for process to exit
        for _ in range(30):
            if not is_running(pid):
                remove_pid()
                log_event(f"[OK] Daemon stopped (PID: {pid})")
                return True
            time.sleep(0.5)
        # Force kill if still running
        os.kill(pid, signal.SIGKILL)
        remove_pid()
        log_event(f"[OK] Daemon killed (PID: {pid})")
        return True
    except (OSError, ProcessLookupError):
        remove_pid()
        log_event("[OK] Daemon already stopped")
        return True
    except Exception as e:
        log_event(f"[ERROR] Failed to stop daemon: {e}")
        return False


def daemon_status():
    """Check daemon status."""
    pid = get_daemon_pid()
    if pid:
        log_event(f"[RUNNING] Daemon active (PID: {pid})")
        return True
    else:
        log_event("[STOPPED] Daemon not running")
        return False


def run_once(config):
    """Run single cycle in foreground."""
    log_event("Running single cycle...")
    daemon_cycle(config)


def main():
    parser = argparse.ArgumentParser(description="Kimi Agent Tracker Daemon v1.2.1")
    parser.add_argument("--start", action="store_true", help="Start daemon in background")
    parser.add_argument("--stop", action="store_true", help="Stop running daemon")
    parser.add_argument("--status", action="store_true", help="Check daemon status")
    parser.add_argument("--run-once", action="store_true", help="Run single cycle in foreground")
    args = parser.parse_args()

    config = load_config()

    if args.start:
        start_daemon(config)
    elif args.stop:
        stop_daemon()
    elif args.status:
        daemon_status()
    elif args.run_once:
        run_once(config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
