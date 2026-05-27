"""
---
title: "Core Logger"
name: "kimi-agent-tracker"
description: "Shared logging utilities with ISO timestamp, level tagging, and log rotation. All skill components use this for unified output format."
version: "v5.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-26T18:15:30.038+00:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{{baseDir}}/scripts/core_logger.py"
  github_path: "kimi-agent-tracker/scripts/core_logger.py"
---
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"


class CoreLogger:
    # Unified logger for all skill components.
    # Writes to both stdout and file with ISO timestamps.

    def __init__(self, log_file: Path = None, component: str = "CORE"):
        self.component = component
        self.log_file = log_file
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, level: str, message: str):
        ts = _timestamp()
        line = f"[{ts}] [{level}] [{self.component}] {message}"
        print(line, flush=True)
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass

    def debug(self, message: str):
        self._write("DEBUG", message)

    def info(self, message: str):
        self._write("INFO", message)

    def warn(self, message: str):
        self._write("WARN", message)

    def error(self, message: str):
        self._write("ERROR", message)

    def fatal(self, message: str):
        self._write("FATAL", message)

    def step(self, step_id: str, message: str):
        # Fixed step registry format for Download Manager
        self._write("STEP", f"[{step_id}] {message}")

    def metric(self, name: str, value: str):
        # Metric logging for performance tracking
        self._write("METRIC", f"{name}={value}")


def get_default_logger(component: str = "CORE") -> CoreLogger:
    # Create logger with default log file in skill logs directory
    from core_path_utils import get_logs_dir
    log_dir = get_logs_dir()
    log_file = log_dir / "tracker.log"
    return CoreLogger(log_file=log_file, component=component)


if __name__ == "__main__":
    log = get_default_logger("TEST")
    log.info("Logger initialized")
    log.step("S001", "Config loaded")
    log.metric("cycle_time", "45s")
    log.warn("Test warning")
    log.error("Test error")
