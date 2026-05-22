"""
---
title: "Tracker Daemon"
name: "kimi-agent-tracker"
description: "Tracker Daemon，Kimi 平台專用自動化追蹤器組件。"
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
  local_path: "{baseDir}/scripts/tracker_daemon.py"
  github_path: "kimi-agent-tracker/scripts/tracker_daemon.py"
---
"""

# -*- coding: utf-8 -*-

import os
import sys
import time
import signal
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

# 動態注入 connector 路徑
connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
if str(connector_path) not in sys.path:
    sys.path.insert(0, str(connector_path))

# 動態注入本技能腳本路徑
scripts_path = Path(__file__).parent
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))

from kimi_login_manager import validate_login
from kimi_conversation_lister import extract_conversations, save_conversation_list
from kimi_downloader import download_from_list
from state_manager import load_state, save_state


def setup_logging(log_dir):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "tracker_daemon.log"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)

    logger = logging.getLogger("kimi-agent-tracker")
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


class TrackerDaemon:
    def __init__(self, interval: int = 900, count: int = 10):
        self.interval = interval
        self.count = count
        self.running = False

        base_dir = Path(__file__).parent.parent
        self.log_dir = base_dir / ".logs"
        self.config_dir = base_dir / ".config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.pid_file = self.config_dir / "tracker_daemon.pid"
        self.logger = setup_logging(self.log_dir)

    def _write_pid(self):
        self.pid_file.write_text(str(os.getpid()), encoding="utf-8")

    def _remove_pid(self):
        if self.pid_file.exists():
            self.pid_file.unlink()

    def _is_running(self):
        if not self.pid_file.exists():
            return False
        try:
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            return True
        except (ValueError, OSError):
            return False

    def _signal_handler(self, signum, frame):
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def run_cycle(self):
        """單次循環：驗證登入態 → 提取對話列表 → 下載文件 → 更新狀態。"""
        self.logger.info("Cycle starting")

        # Phase 1: 驗證登入態
        if not validate_login():
            self.logger.error("Login invalid. Please run kimi_login_manager.py first.")
            return

        self.logger.info("Login valid")

        # Phase 2: 提取對話列表
        try:
            conversations = extract_conversations(count=self.count, headless=True)
            list_path = save_conversation_list(conversations)
            self.logger.info(f"Extracted {len(conversations)} conversations")
        except Exception as e:
            self.logger.error(f"Failed to extract conversations: {e}")
            return

        # Phase 3: 下載文件
        try:
            result = download_from_list(list_path, headless=True)
            self.logger.info(
                f"Download complete: {len(result['success'])} success, "
                f"{len(result['duplicates'])} duplicates, "
                f"{len(result['errors'])} errors"
            )
        except Exception as e:
            self.logger.error(f"Download failed: {e}")

        self.logger.info("Cycle completed")

    def start(self):
        """啟動守護程序循環。"""
        if self._is_running():
            self.logger.warning("Daemon already running")
            return

        self.running = True
        self._write_pid()

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        self.logger.info(f"Daemon started (PID: {os.getpid()}), interval={self.interval}s")

        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                self.logger.error(f"Cycle failed: {e}", exc_info=True)

            # 等待下一輪，支持優雅關閉
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)

        self._remove_pid()
        self.logger.info("Daemon stopped cleanly")

    def stop(self):
        """停止守護程序。"""
        if not self.pid_file.exists():
            print("[DAEMON] Not running (no PID file)")
            return

        try:
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
            os.kill(pid, signal.SIGTERM)
            print(f"[DAEMON] Sent SIGTERM to PID {pid}")
        except Exception as e:
            print(f"[ERROR] Failed to stop: {e}", file=sys.stderr)

    def status(self):
        """查看運行狀態。"""
        if self._is_running():
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
            print(f"[DAEMON] Running (PID: {pid})")
        else:
            print("[DAEMON] Not running")

    def run_once(self):
        """前台單次執行，用於測試。"""
        self.run_cycle()


def main():
    parser = argparse.ArgumentParser(description="Kimi Agent Tracker Daemon")
    parser.add_argument("--start", action="store_true", help="Start background daemon")
    parser.add_argument("--stop", action="store_true", help="Stop daemon")
    parser.add_argument("--status", action="store_true", help="Check daemon status")
    parser.add_argument("--run-once", action="store_true", help="Run one cycle immediately (foreground)")
    parser.add_argument("--interval", type=int, default=900, help="Cycle interval in seconds (default: 900)")
    parser.add_argument("--count", type=int, default=10, help="Number of conversations to extract (default: 10)")
    args = parser.parse_args()

    daemon = TrackerDaemon(interval=args.interval, count=args.count)

    if args.stop:
        daemon.stop()
    elif args.status:
        daemon.status()
    elif args.run_once:
        daemon.run_once()
    elif args.start:
        daemon.start()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
