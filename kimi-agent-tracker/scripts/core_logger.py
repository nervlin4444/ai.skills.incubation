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


# =============================================================================
# TEST MODULE
# =============================================================================

def _run_tests():
    passed = 0
    failed = 0

    def _t(name, condition, ok_detail="", fail_reason=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name}: {ok_detail}" if ok_detail else f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}: {fail_reason}" if fail_reason else f"  [FAIL] {name}")

    from io import StringIO
    import tempfile

    print("=" * 60)
    print("  core_logger.py — UNIT TESTS (AST only)")
    print("=" * 60)

    # T1: init without log_file
    l1 = CoreLogger(component="T1")
    _t("T1 test_init_no_file",
       l1.component == "T1" and l1.log_file is None,
       f"component={l1.component}, log_file={l1.log_file}")

    # T2: init with log_file (auto-create parent dir)
    tmp_file = Path(tempfile.gettempdir()) / f"kimi_logger_test_{int(__import__('time').time())}.log"
    l2 = CoreLogger(log_file=tmp_file, component="T2")
    _t("T2 test_init_with_file",
       l2.component == "T2" and l2.log_file == tmp_file and tmp_file.parent.is_dir(),
       f"component={l2.component}, log_file={l2.log_file}")

    # T3: info() output format
    old_stdout = sys.stdout
    cap = StringIO()
    sys.stdout = cap
    l3 = CoreLogger(component="T3")
    l3.info("hello world")
    output = cap.getvalue()
    sys.stdout = old_stdout
    _t("T3 test_info_output",
       "[INFO]" in output and "[T3]" in output and "hello world" in output,
       output.strip())

    # T4: warn() output format
    cap = StringIO()
    sys.stdout = cap
    l4 = CoreLogger(component="T4")
    l4.warn("test warning")
    output = cap.getvalue()
    sys.stdout = old_stdout
    _t("T4 test_warn_output",
       "[WARN]" in output and "[T4]" in output and "test warning" in output,
       output.strip())

    # T5: error() output format
    cap = StringIO()
    sys.stdout = cap
    l5 = CoreLogger(component="T5")
    l5.error("critical error")
    output = cap.getvalue()
    sys.stdout = old_stdout
    _t("T5 test_error_output",
       "[ERROR]" in output and "[T5]" in output and "critical error" in output,
       output.strip())

    # T6: debug() + fatal() exist and work
    cap = StringIO()
    sys.stdout = cap
    l6 = CoreLogger(component="T6")
    l6.debug("debug msg")
    l6.fatal("fatal msg")
    output = cap.getvalue()
    sys.stdout = old_stdout
    has_debug = "[DEBUG]" in output and "debug msg" in output
    has_fatal = "[FATAL]" in output and "fatal msg" in output
    _t("T6 test_debug_and_fatal",
       has_debug and has_fatal,
       output.strip().replace("\n", " | "))

    # T7: step() format [S001]
    cap = StringIO()
    sys.stdout = cap
    l7 = CoreLogger(component="T7")
    l7.step("S001", "Config loaded successfully")
    output = cap.getvalue()
    sys.stdout = old_stdout
    _t("T7 test_step_format",
       "[STEP]" in output and "[S001]" in output and "Config loaded successfully" in output,
       output.strip())

    # T8: metric() format key=value
    cap = StringIO()
    sys.stdout = cap
    l8 = CoreLogger(component="T8")
    l8.metric("cycle_time", "45s")
    output = cap.getvalue()
    sys.stdout = old_stdout
    _t("T8 test_metric_format",
       "[METRIC]" in output and "cycle_time=45s" in output,
       output.strip())

    # T9: writes to log file
    tf9 = Path(tempfile.gettempdir()) / f"kimi_logger_file_test_{int(__import__('time').time())}.log"
    try:
        l9 = CoreLogger(log_file=tf9, component="T9")
        l9.info("file write test")
        l9.warn("file warn test")
        written = tf9.read_text(encoding="utf-8")
        _t("T9 test_file_writing",
           "file write test" in written and "file warn test" in written,
           f"lines={len(written.splitlines())}, file={tf9}")
    finally:
        if tf9.exists():
            tf9.unlink()

    # T10: get_default_logger returns CoreLogger
    l10 = get_default_logger("T10_TEST")
    _t("T10 test_get_default_logger",
       isinstance(l10, CoreLogger) and l10.component == "T10_TEST" and l10.log_file.name == "tracker.log",
       f"type={type(l10).__name__}, component={l10.component}, log_file={l10.log_file.name}")

    # cleanup tmp files
    if tmp_file.exists():
        tmp_file.unlink()

    print()
    print("=" * 60)
    print(f"  TEST RESULTS: {passed}/{passed + failed} passed, {failed} failed")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Core Logger v5.0.0")
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    args = parser.parse_args()

    if args.test:
        _run_tests()
        sys.exit(0)

    log = get_default_logger("TEST")
    log.info("Logger initialized")
    log.step("S001", "Config loaded")
    log.metric("cycle_time", "45s")
    log.warn("Test warning")
    log.error("Test error")
