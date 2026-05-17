"""
---
title: Scheduler Daemon
name: github-skill-organizer
description: Background daemon that runs every 60 seconds to scan, classify, install, and sync skill files. Includes file logging.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/scheduler_daemon.py"
  github_path: "github-skill-organizer/scripts/scheduler_daemon.py"
---
"""

import os
import sys
import time
import signal
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

from skill_organizer_config import load_config, ConfigError
from local_scanner import LocalScanner
from change_classifier import ChangeClassifier
from sync_engine import SyncEngine
from skill_installer import SkillInstaller


def setup_logging(log_dir, log_level):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "organizer.log"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)

    logger = logging.getLogger("github-skill-organizer")
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


class SkillOrganizerDaemon:
    def __init__(self):
        try:
            self.cfg = load_config()
        except ConfigError as e:
            print(f"[FATAL] {e}", file=sys.stderr)
            sys.exit(1)

        self.logger = setup_logging(self.cfg.log_dir, self.cfg.log_level)
        self.scanner = LocalScanner()
        self.classifier = ChangeClassifier()
        self.sync = SyncEngine()
        self.installer = SkillInstaller()

        self.running = False
        self.pid_file = Path(self.cfg.pid_file_path)

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
        self.logger.info("Cycle starting")

        # Phase 1: Process DOWNLOAD_FOLDER (new files from Kimi/web/manual)
        new_files = self.scanner.scan()
        if new_files:
            self.logger.info(f"Found {len(new_files)} new file(s) in download folder")

            installed = self.installer.install_batch(new_files)
            for r in installed:
                if r["status"] == "installed":
                    self.logger.info(f"INSTALLED {r['skill_name']}: {r['target_path']} (from {r.get('derived_from', 'unknown')})")
                elif r["status"] == "unclassified":
                    self.logger.warning(f"UNCLASSIFIED: {r.get('reason', 'unknown')}")
                else:
                    self.logger.error(f"ERROR: {r.get('reason', 'unknown')}")

            # Phase 2: Classify and upload approved changes
            skill_groups = {}
            for r in installed:
                if r["status"] == "installed":
                    sn = r["skill_name"]
                    skill_groups.setdefault(sn, []).append(r["target_path"])

            for skill_name, files in skill_groups.items():
                classification = self.classifier.classify(skill_name, files)
                self.logger.info(f"CLASSIFY {skill_name}: {classification['bump_type']} "
                                 f"v{classification['current_version']} -> v{classification['new_version']}")

                if classification["approval_required"]:
                    self.logger.info(f"PENDING {skill_name} requires owner approval")
                else:
                    result = self.sync.upload_skill(skill_name, files, classification)
                    self.logger.info(f"UPLOAD {skill_name}: {result['status']}")
        else:
            self.logger.debug("No new files in download folder")

        # Phase 3: Download sync (pull latest from GitHub to local)
        self._sync_downloads()

        self.scanner.set_last_run_time()
        self.logger.info("Cycle completed")

    def _sync_downloads(self):
        """Pull latest skills from GitHub to local skills folder."""
        try:
            results = self.sync.download_all_skills()
            for skill_name, result in results.items():
                if result.get("updated"):
                    self.logger.info(f"DOWNLOAD {skill_name}: updated to {result.get('version', 'unknown')}")
                elif result.get("error"):
                    self.logger.error(f"DOWNLOAD {skill_name}: {result['error']}")
                else:
                    self.logger.debug(f"DOWNLOAD {skill_name}: already up to date")
        except Exception as e:
            self.logger.error(f"Download sync failed: {e}")

    def start(self):
        if self._is_running():
            self.logger.warning("Daemon already running")
            return

        self.running = True
        self._write_pid()

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        self.logger.info(f"Daemon started (PID: {os.getpid()}), interval={self.cfg.scan_interval}s")

        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                self.logger.error(f"Cycle failed: {e}", exc_info=True)

            for _ in range(self.cfg.scan_interval):
                if not self.running:
                    break
                time.sleep(1)

        self._remove_pid()
        self.logger.info("Daemon stopped cleanly")

    def stop(self):
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
        if self._is_running():
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
            print(f"[DAEMON] Running (PID: {pid})")
        else:
            print("[DAEMON] Not running")

    def run_once(self):
        self.run_cycle()


def main():
    parser = argparse.ArgumentParser(description="GitHub Skill Organizer Daemon")
    parser.add_argument("--start", action="store_true", help="Start background daemon")
    parser.add_argument("--stop", action="store_true", help="Stop daemon")
    parser.add_argument("--status", action="store_true", help="Check daemon status")
    parser.add_argument("--sync-now", action="store_true", help="Run one sync cycle immediately")
    args = parser.parse_args()

    daemon = SkillOrganizerDaemon()

    if args.stop:
        daemon.stop()
    elif args.status:
        daemon.status()
    elif args.sync_now:
        daemon.run_once()
    elif args.start:
        daemon.start()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
