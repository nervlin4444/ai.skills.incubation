"""
---
title: "Kimi Tracker Daemon"
name: "kimi-agent-tracker"
description: "Pure trigger daemon for scheduled Kimi download tasks. Delegates all business logic to Download Manager. Manages PID, timer, and process lifecycle only."
version: "v5.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-27T00:50:32.021+00:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
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
from pathlib import Path
from typing import Optional

_SKILL_DIR = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _SKILL_DIR / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from core_path_utils import get_config_dir, get_logs_dir, ensure_dir
from core_logger import CoreLogger, get_default_logger


DEFAULT_PID_FILE = get_config_dir() / "daemon.pid"
DEFAULT_LOG_FILE = get_logs_dir() / "daemon.log"
DEFAULT_INTERVAL_SEC = 300


def _read_pid() -> Optional[int]:
    try:
        with open(DEFAULT_PID_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _write_pid(pid: int):
    ensure_dir("{baseDir}/config")
    with open(DEFAULT_PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(pid))


def _remove_pid():
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


def _load_config() -> dict:
    cfg_path = get_config_dir() / "tracker_config.json"
    if not cfg_path.exists():
        return {"poll_interval_seconds": DEFAULT_INTERVAL_SEC}
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _run_download_manager(interval_sec: int, log: CoreLogger) -> dict:
    dm_script = _SCRIPTS_DIR / "kimi_download_manager.py"
    if not dm_script.exists():
        log.error("Download Manager not found: " + str(dm_script))
        return {"status": "error", "error": "DM not found"}
    cmd = [
        sys.executable,
        str(dm_script),
        "--interval", str(interval_sec),
        "--once",
    ]
    log.info("Triggering Download Manager: " + " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=interval_sec - 30)
        log.info("DM exit code: " + str(result.returncode))
        if result.stdout:
            last_lines = result.stdout.strip().splitlines()[-5:]
            for line in last_lines:
                log.info("DM stdout: " + line[:150])
        if result.stderr:
            log.warn("DM stderr: " + result.stderr[:200])
        parsed = {}
        if result.stdout:
            for line in reversed(result.stdout.strip().splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        parsed = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
        return parsed if parsed else {"status": "completed", "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        log.error("Download Manager timed out")
        return {"status": "timeout"}
    except Exception as e:
        log.error("Download Manager exception: " + str(e))
        return {"status": "error", "error": str(e)}


def run_daemon_loop(interval_sec: int):
    log = get_default_logger("DAEMON")
    log.info("Daemon started (PID: " + str(os.getpid()) + ")")
    log.info("Interval: " + str(interval_sec) + "s")
    _write_pid(os.getpid())
    try:
        while True:
            cycle_start = time.time()
            log.info("=" * 60)
            log.info("Triggering cycle...")
            result = _run_download_manager(interval_sec, log)
            elapsed = time.time() - cycle_start
            log.info("Cycle result: " + json.dumps(result, ensure_ascii=False)[:200])
            log.info("Cycle elapsed: " + str(int(elapsed)) + "s")
            sleep_time = max(10, interval_sec - int(elapsed))
            next_run = time.strftime("%H:%M:%S", time.gmtime(time.time() + sleep_time))
            log.info("Sleeping " + str(sleep_time) + "s... (next: ~" + next_run + " UTC)")
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        log.info("KeyboardInterrupt, shutting down...")
    except Exception as e:
        log.error("Loop error: " + str(e))
    finally:
        _remove_pid()
        log.info("Stopped.")


def main():
    parser = argparse.ArgumentParser(description="Kimi Tracker Daemon v5.0.0")
    parser.add_argument("--start", action="store_true", help="Start daemon in background")
    parser.add_argument("--stop", action="store_true", help="Stop running daemon")
    parser.add_argument("--status", action="store_true", help="Check daemon status")
    parser.add_argument("--run-once", action="store_true", help="Run single cycle and exit")
    parser.add_argument("--interval", type=int, default=None, help="Override cycle interval in seconds")
    args = parser.parse_args()

    config = _load_config()
    interval = args.interval if args.interval is not None else config.get("poll_interval_seconds", DEFAULT_INTERVAL_SEC)

    if args.status:
        pid = _read_pid()
        if pid and _is_running(pid):
            print("[RUNNING] PID: " + str(pid))
            print("[RUNNING] Log: " + str(DEFAULT_LOG_FILE))
        else:
            _remove_pid()
            print("[STOPPED] Not running")
        return

    if args.stop:
        pid = _read_pid()
        if pid and _is_running(pid):
            try:
                os.kill(pid, 15)
                time.sleep(1)
                if _is_running(pid):
                    os.kill(pid, 9)
                _remove_pid()
                print("[OK] Stopped")
            except Exception as e:
                print("[ERROR] " + str(e))
        else:
            _remove_pid()
            print("[OK] Not running")
        return

    if args.start:
        pid = _read_pid()
        if pid and _is_running(pid):
            print("[WARN] Already running (PID: " + str(pid) + ")")
            return
        try:
            pid = os.fork()
            if pid > 0:
                print("[OK] Started (PID: " + str(pid) + ")")
                print("[OK] Log: " + str(DEFAULT_LOG_FILE))
                print("[OK] tail -f " + str(DEFAULT_LOG_FILE))
                return
        except (OSError, AttributeError):
            pass
        run_daemon_loop(interval)
        return

    if args.run_once:
        log = get_default_logger("DAEMON")
        log.info("Running single cycle...")
        result = _run_download_manager(interval, log)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    parser.print_help()
    print("")
    print("Log: " + str(DEFAULT_LOG_FILE))
    print("Config: " + str(get_config_dir() / "tracker_config.json"))


if __name__ == "__main__":
    main()
