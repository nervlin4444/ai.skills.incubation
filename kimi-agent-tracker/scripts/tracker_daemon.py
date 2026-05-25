#!/usr/bin/env python3
"""
---
title: "Tracker Daemon"
name: "kimi-agent-tracker"
description: "Tracker Daemon，Kimi 平台專用自動化追蹤器組件。v1.0.2 hotfix: 同步版本與 auth_config。"
version: "1.0.2"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T00:10:00+08:00"
fixes: [24]
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "scripts/tracker_daemon.py"
  github_path: "kimi-agent-tracker/scripts/tracker_daemon.py"
---
"""

# -*- coding: utf-8 -*-

import os
import sys
import time
import signal
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone


class TrackerDaemon:
    def __init__(self, interval: int = 900, count: int = 10):
        self.interval = interval
        self.count = count
        self.base_dir = Path(__file__).parent.parent
        self.pid_file = self.base_dir / ".config" / "daemon.pid"
        self.log_file = self.base_dir / ".logs" / "daemon.log"
        self.running = False
        self._setup_dirs()

    def _setup_dirs(self):
        for d in [self.base_dir / ".config", self.base_dir / ".logs",
                  self.base_dir / "downloads", self.base_dir / ".duplicate"]:
            d.mkdir(parents=True, exist_ok=True)

    def _log(self, message: str):
        timestamp = datetime.now(timezone.utc).isoformat()
        line = f"[{timestamp}] {message}"
        print(line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def run_cycle(self):
        """單次循環：驗證登入態 → 提取對話列表 → 下載文件 → 更新狀態。"""
        self._log("Starting cycle...")
        try:
            # 動態注入路徑
            scripts_path = Path(__file__).parent
            if str(scripts_path) not in sys.path:
                sys.path.insert(0, str(scripts_path))

            from kimi_login_manager import validate_login
            if not validate_login():
                self._log("[ERROR] Login invalid, aborting cycle.")
                return

            from kimi_conversation_lister import extract_conversations, save_conversation_list
            # v1.0.2: 使用 visible=False（headless）而非錯誤的 headless=True
            conversations = extract_conversations(count=self.count, visible=False)
            save_conversation_list(conversations)
            self._log(f"Extracted {len(conversations)} conversations")

            from kimi_downloader import download_from_list
            from state_manager import load_state, save_state, register_download
            state = load_state()
            results = download_from_list(
                str(self.base_dir / ".config" / "conversations.json"),
                visible=False
            )
            for success in results.get("success", []):
                if "path" in success:
                    state = register_download(
                        state, success["path"],
                        success.get("conversation", "unknown")
                    )
            save_state(state)
            self._log(
                f"Cycle complete: {len(results.get('success', []))} success, "
                f"{len(results.get('duplicates', []))} duplicates, "
                f"{len(results.get('errors', []))} errors"
            )
        except Exception as e:
            self._log(f"[ERROR] Cycle failed: {e}")

    def start(self):
        """啟動守護程序循環。"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, "r") as f:
                    old_pid = int(f.read().strip())
                os.kill(old_pid, 0)
                self._log(f"[ERROR] Daemon already running (PID {old_pid})")
                return
            except (ValueError, OSError, ProcessLookupError):
                pass
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))
        self.running = True
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        self._log(f"Daemon started (PID: {os.getpid()}), interval={self.interval}s")
        while self.running:
            self.run_cycle()
            if self.running:
                time.sleep(self.interval)
        self._log("Daemon stopped.")
        self.pid_file.unlink(missing_ok=True)

    def stop(self):
        """停止守護程序。"""
        if not self.pid_file.exists():
            print("[INFO] No PID file found. Daemon not running.")
            return
        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"[OK] Sent SIGTERM to daemon (PID: {pid})")
        except (ValueError, OSError, ProcessLookupError) as e:
            print(f"[ERROR] Failed to stop daemon: {e}")
            self.pid_file.unlink(missing_ok=True)

    def status(self):
        """查看運行狀態。"""
        if not self.pid_file.exists():
            print("[INFO] Daemon not running.")
            return False
        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"[OK] Daemon running (PID: {pid})")
            return True
        except (ValueError, OSError, ProcessLookupError):
            print("[WARN] Stale PID file found. Daemon not running.")
            self.pid_file.unlink(missing_ok=True)
            return False

    def run_once(self):
        """前台單次執行，用於測試和調試。"""
        self._log("Running single cycle (foreground)...")
        self.run_cycle()
        self._log("Single cycle complete.")

    def _signal_handler(self, signum, frame):
        self._log(f"Received signal {signum}, shutting down...")
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="Kimi Agent Tracker Daemon")
    parser.add_argument("--start", action="store_true", help="Start daemon (background)")
    parser.add_argument("--stop", action="store_true", help="Stop daemon")
    parser.add_argument("--status", action="store_true", help="Check status")
    parser.add_argument("--run-once", action="store_true", help="Single execution (foreground)")
    parser.add_argument("--interval", type=int, default=900, help="Cycle interval in seconds (default 900)")
    parser.add_argument("--count", type=int, default=10, help="Conversations per extraction (default 10)")
    args = parser.parse_args()

    daemon = TrackerDaemon(interval=args.interval, count=args.count)
    if args.start:
        daemon.start()
    elif args.stop:
        daemon.stop()
    elif args.status:
        daemon.status()
    elif args.run_once:
        daemon.run_once()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
