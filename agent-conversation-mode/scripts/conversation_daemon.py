"""
---
title: "Conversation Daemon"
name: agent-conversation-mode
description: "Background daemon shell for agent conversation backup. Routes lifecycle through daemon-script-connector. Business logic: trace extraction and archival."
version: "v6.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T16:31:00+08:00"
fixes: []
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  - local_path: "{baseDir}/scripts/conversation_daemon.py"
    github_path: "agent-conversation-mode/scripts/conversation_daemon.py"
---
"""

# conversation_daemon.py v6.0.0
# Shell daemon for conversation backup.
# Lifecycle managed by daemon-script-connector.
# Business logic: trace extraction via trace_extractor.py

import os
import sys
import time
import signal
import argparse
import subprocess
import logging
from pathlib import Path

from trace_extractor import TraceExtractor

SKILL_NAME = "agent-conversation-mode"
SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_INTERVAL = 60


def _connector_cli():
    return Path.home() / ".workbuddy" / "skills" / "daemon-script-connector" / "scripts" / "daemon_connector.py"


def _setup_logging(log_dir):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "daemon.log"
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger = logging.getLogger("agent-conversation-mode")
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


class ConversationDaemon:
    def __init__(self, interval=DEFAULT_INTERVAL):
        self.interval = interval
        self.extractor = TraceExtractor()
        self.running = False
        self.logger = _setup_logging(Path(__file__).parent.parent / "logs")

    def _signal_handler(self, signum, frame):
        self.logger.info("Received signal " + str(signum) + ", shutting down...")
        self.running = False

    def run_cycle(self):
        self.logger.info("Cycle starting")
        try:
            result = self.extractor.process_new_traces()
            self.logger.info("Cycle complete: " + str(result.get("processed", 0)) + " new traces")
        except Exception as e:
            self.logger.error("Cycle failed: " + str(e), exc_info=True)

    def start(self):
        self.running = True
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        self.logger.info("Daemon started, interval=" + str(self.interval) + "s")

        while self.running:
            self.run_cycle()
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)

        self.logger.info("Daemon stopped cleanly")

    def stop(self):
        # No-op for direct execution; connector handles platform stop
        self.logger.info("Stop requested")

    def status(self):
        state_path = Path(__file__).parent.parent / "state" / "last_processed.json"
        if state_path.exists():
            import json
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            count = len(state.get("processed_traces", {}))
            return {"status": "ok", "processed_traces": count}
        return {"status": "ok", "processed_traces": 0}

    def run_now(self):
        self.logger.info("Run-now triggered")
        result = self.extractor.process_new_traces()
        self.logger.info("Run-now complete: " + str(result))
        return result


def _call_connector(action, skill_name=SKILL_NAME):
    cli = _connector_cli()
    if not cli.exists():
        print("[ERROR] daemon-script-connector not found at " + str(cli))
        sys.exit(1)

    cmd = [sys.executable, str(cli), action, "--skill-name", skill_name]
    if action == "--install":
        cmd.extend(["--script-path", str(SCRIPT_PATH), "--interval", str(DEFAULT_INTERVAL)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Conversation Daemon v6.0.0")
    parser.add_argument("--start", action="store_true", help="Start daemon (via connector)")
    parser.add_argument("--stop", action="store_true", help="Stop daemon (via connector)")
    parser.add_argument("--status", action="store_true", help="Check daemon status")
    parser.add_argument("--run-now", action="store_true", help="Execute one extraction cycle immediately")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Polling interval in seconds")
    args = parser.parse_args()

    if args.stop:
        sys.exit(_call_connector("--remove"))

    elif args.status:
        # Check connector status first
        _call_connector("--status")
        # Also check local state
        daemon = ConversationDaemon()
        local = daemon.status()
        print("[LOCAL] Processed traces: " + str(local.get("processed_traces", 0)))

    elif args.run_now:
        daemon = ConversationDaemon(args.interval)
        result = daemon.run_now()
        print(json.dumps(result, indent=2))

    elif args.start:
        # Register with connector first, then start local loop
        _call_connector("--install")
        daemon = ConversationDaemon(args.interval)
        daemon.start()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
