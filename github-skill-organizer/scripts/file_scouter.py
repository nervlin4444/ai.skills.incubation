"""
---
title: File Scouter
name: github-skill-organizer
description: Scans Downloads folder, extracts frontmatter, classifies files as classified/invalid/unclassified. Supports force scan (ignore last_run_time). Replaces local_scanner.py.
version: 1.2.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-24T20:03:00+08:00
fixes: []
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: scripts/file_scouter.py
  github_path: github-skill-organizer/scripts/file_scouter.py
---
"""

import sys
import time
from pathlib import Path

try:
    from skill_organizer_config import load_config
    from core_frontmatter import FrontmatterExtractor
    from core_path_utils import normalize_path
    from core_logger import log
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config
    from core_frontmatter import FrontmatterExtractor
    from core_path_utils import normalize_path
    from core_logger import log


class FileScouter:
    """
    File identity scout.
    Scans Downloads, identifies files, marks status.
    Does NOT move or backup files - that is skill_installer's job.
    """

    def __init__(self):
        self.cfg = load_config()
        self.downloads_dir = normalize_path(self.cfg.download_folder)
        self._last_run_time = 0

    def scan(self, downloads_dir=None, force=False):
        """
        Scan downloads directory and classify files.

        Args:
            downloads_dir: Override downloads directory path
            force: If True, scan ALL files regardless of mtime (first cycle mode).
                   If False, only scan files modified since last run.
        Returns: list of file records with status.
        """
        if downloads_dir is None:
            downloads_dir = self.downloads_dir
        else:
            downloads_dir = normalize_path(downloads_dir)

        if not downloads_dir.exists():
            log("SCOUTER", f"Downloads directory not found: {downloads_dir}", "WARN")
            return []

        results = []
        cutoff_time = 0 if force else self._last_run_time

        for file_path in downloads_dir.iterdir():
            if not file_path.is_file():
                continue
            if file_path.name.startswith("."):
                continue
            # Skip incomplete downloads (Opera .opdownload, Chrome .crdownload, Firefox .part)
            if file_path.suffix in (".opdownload", ".crdownload", ".part", ".tmp"):
                log("SCOUTER", f"Skipped incomplete download: {file_path.name}")
                continue

            # Skip files not modified since last run (unless force=True)
            if not force:
                try:
                    mtime = file_path.stat().st_mtime
                    if mtime <= cutoff_time:
                        continue
                except OSError:
                    continue

            record = {
                "file_name": file_path.name,
                "file_path": str(file_path),
                "size": file_path.stat().st_size,
                "mtime": file_path.stat().st_mtime,
            }

            # Try extract frontmatter
            fm = FrontmatterExtractor.extract(file_path)
            if fm:
                record["status"] = "classified"
                record["frontmatter"] = fm
                record["skill_name"] = fm.get("name", "unknown")
                record["version"] = fm.get("version", "unknown")
            else:
                # Check if it has traces but unparseable
                invalid = FrontmatterExtractor.is_invalid(file_path)
                if invalid:
                    record["status"] = "is_invalid"
                    record["invalid_reason"] = invalid.get("reason", "unknown")
                else:
                    record["status"] = "unclassified"

            results.append(record)
            log("SCOUTER", f"{file_path.name}: {record['status']}")

        log("SCOUTER", f"Scan complete: {len(results)} files found (force={force})")
        return results

    def scan_and_report(self, downloads_dir=None, force=False):
        """Scan and return structured report."""
        results = self.scan(downloads_dir, force=force)
        classified = [r for r in results if r["status"] == "classified"]
        invalid = [r for r in results if r["status"] == "is_invalid"]
        unclassified = [r for r in results if r["status"] == "unclassified"]

        return {
            "total": len(results),
            "classified": len(classified),
            "invalid": len(invalid),
            "unclassified": len(unclassified),
            "files": results,
            "summary": {
                "ready_for_install": [r["file_name"] for r in classified],
                "needs_manual_review": [r["file_name"] for r in invalid],
                "needs_classification": [r["file_name"] for r in unclassified],
            }
        }

    def set_last_run_time(self):
        """Record current time as last run timestamp."""
        self._last_run_time = time.time()
        log("SCOUTER", f"Last run time set: {self._last_run_time}")


if __name__ == "__main__":
    import json
    scouter = FileScouter()
    report = scouter.scan_and_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))
