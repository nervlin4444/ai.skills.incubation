"""
---
title: "Kimi Tracker Daemon - F005"
name: "kimi-agent-tracker"
description: "Daemon with robust stop/start handling and subprocess isolation for downloads."
version: "1.1.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T11:25:00+08:00"
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

import os
import sys
import json
import time
import signal
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone

connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
if str(connector_path) not in sys.path:
    sys.path.insert(0, str(connector_path))

from browser_connector import BrowserConnector


def _load_config():
    config_path = Path(__file__).parent.parent / ".config" / "kimi_tracker_config.json"
    defaults = {
        "platform": {"base_url": "https://www.kimi.com"},
        "login": {
            "profile_name": "kimi_com",
            "validate_timeout_ms": 5000
        },
        "selectors": {
            "login_indicators": [".chat-info-item", ".user-avatar", ".user-name"]
        },
        "daemon": {
            "interval_sec": 900,
            "visible": False,
            "conversation_count": 10
        },
        "state": {
            "conversations_file": "{baseDir}/.config/conversations.json"
        }
    }
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            for section in defaults:
                if section in user_cfg and isinstance(user_cfg[section], dict):
                    defaults[section].update(user_cfg[section])
        except Exception:
            pass
    return defaults


CONFIG = _load_config()
PID_FILE = Path(__file__).parent.parent / ".config" / "daemon.pid"


def _resolve_path(path_tpl: str) -> Path:
    base = Path(__file__).parent.parent
    return Path(path_tpl.replace("{baseDir}", str(base)))


def _log(msg: str):
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] {msg}")


def validate_login(profile_name: str = None) -> bool:
    profile = profile_name or CONFIG["login"]["profile_name"]
    timeout = CONFIG["login"]["validate_timeout_ms"]
    driver = BrowserConnector(profile_name=profile, visible=False)
    try:
        context = driver.launch()
        page = driver.navigate(CONFIG["platform"]["base_url"])
        page.wait_for_load_state("networkidle", timeout=timeout)
        selectors = CONFIG.get("selectors", {}).get("login_indicators", [
            ".chat-info-item", ".user-avatar", ".user-name"
        ])
        for sel in selectors:
            try:
                if page.query_selector(sel):
                    return True
            except Exception:
                continue
        return False
    except Exception as e:
        _log(f"[ERROR] validate_login: {e}")
        return False
    finally:
        try:
            driver.close()
        except Exception:
            pass


def extract_conversations(profile_name: str = None, count: int = None) -> list:
    script_dir = Path(__file__).parent
    cmd = [
        sys.executable,
        str(script_dir / "kimi_conversation_lister.py"),
        "--count", str(count or CONFIG["daemon"]["conversation_count"])
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            conv_path = _resolve_path(CONFIG["state"]["conversations_file"])
            if conv_path.exists():
                with open(conv_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        else:
            _log(f"[ERROR] lister failed: {result.stderr}")
    except Exception as e:
        _log(f"[ERROR] lister: {e}")
    return []


def run_downloads(profile_name: str = None) -> dict:
    """使用 subprocess 調用 downloader，完全隔離 asyncio 環境。"""
    script_dir = Path(__file__).parent
    cmd = [
        sys.executable,
        str(script_dir / "kimi_downloader.py"),
        "--from-list", str(_resolve_path(CONFIG["state"]["conversations_file"]))
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        _log(f"[DOWNLOAD] stdout: {result.stdout.strip()[-500:]}")  # 只顯示最後 500 字符
        if result.stderr:
            _log(f"[DOWNLOAD] stderr: {result.stderr.strip()[-500:]}")
        return {"success": result.returncode == 0}
    except Exception as e:
        _log(f"[ERROR] downloader: {e}")
        return {"success": False, "error": str(e)}


def run_cycle():
    _log("Starting cycle...")
    if not validate_login():
        _log("[ERROR] Login invalid, aborting cycle.")
        return
    _log("[OK] Login valid")
    conversations = extract_conversations()
    _log(f"[OK] Extracted {len(conversations)} conversations")
    if not conversations:
        _log("[WARN] No conversations, skipping download.")
        return
    download_result = run_downloads()
    if download_result.get("success"):
        _log("[OK] Download cycle complete")
    else:
        _log(f"[WARN] Download issues: {download_result.get('error', 'unknown')}")
    _log("Cycle complete.")


def _ensure_stopped():
    """確保 daemon 完全停止，包括強制 kill。"""
    if not PID_FILE.exists():
        return True
    try:
        pid = int(PID_FILE.read_text().strip())
        # 先嘗試 SIGTERM
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            os.kill(pid, 0)  # 檢查是否還在
            # 還在，用 SIGKILL
            os.kill(pid, signal.SIGKILL)
            time.sleep(1)
        except OSError:
            pass  # 已經死了
        PID_FILE.unlink(missing_ok=True)
        return True
    except (ValueError, OSError):
        PID_FILE.unlink(missing_ok=True)
        return True


def start_daemon(interval: int = None):
    interval = interval or CONFIG["daemon"]["interval_sec"]

    # 確保舊進程已死
    _ensure_stopped()

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    _log(f"Daemon started (PID: {os.getpid()}), interval={interval}s")

    def _signal_handler(signum, frame):
        _log(f"Signal {signum} received, shutting down...")
        if PID_FILE.exists():
            PID_FILE.unlink()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    while True:
        try:
            run_cycle()
        except Exception as e:
            _log(f"[ERROR] Cycle exception: {e}")
        _log(f"Sleeping {interval}s...")
        time.sleep(interval)


def stop_daemon():
    if _ensure_stopped():
        print("[OK] Daemon stopped")
    else:
        print("[WARN] Stop may have issues")


def daemon_status():
    if not PID_FILE.exists():
        print("[STOPPED] Daemon not running")
        return
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        print(f"[RUNNING] Daemon active (PID: {pid})")
    except (OSError, ValueError):
        print("[STOPPED] PID file stale")
        PID_FILE.unlink(missing_ok=True)


def run_once():
    _log("Running single cycle...")
    run_cycle()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--interval", type=int, default=None)
    args = parser.parse_args()

    if args.stop:
        stop_daemon()
    elif args.status:
        daemon_status()
    elif args.run_once:
        run_once()
    elif args.start:
        start_daemon(args.interval)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
