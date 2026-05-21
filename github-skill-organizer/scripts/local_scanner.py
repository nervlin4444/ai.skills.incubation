"""
---
title: Local File Scanner
name: github-skill-organizer
description: Scans DOWNLOAD_FOLDER for new files. Auto-extracts .zip archives under 100KB, forces current timestamp on extracted files. v1.0.6 adds force-scan mode for daemon first-cycle full scan, fixing the "files older than last_run" cold-start problem.
version: 1.0.6
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-21T17:45:00+08:00
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  - local_path: "{baseDir}/scripts/local_scanner.py"
    github_path: "github-skill-organizer/scripts/local_scanner.py"
---
"""

import os
import sys
import json
import re
import zipfile
from pathlib import Path
from datetime import datetime, timezone

try:
    from skill_organizer_config import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config


class LocalScanner:
    """
    Scans DOWNLOAD_FOLDER for new skill files.
    Auto-extracts .zip archives <= 100KB, forces current timestamp on extracted
    files so they are processed in the SAME daemon cycle.
    Renames processed .zip to .zip.moved to prevent reprocessing.

    v1.0.6 FIX: force=True skips mtime comparison. Used by daemon on its
    first cycle to catch files that existed BEFORE daemon started.
    """

    ZIP_SIZE_LIMIT = 100 * 1024  # 100 KB

    def __init__(self):
        self.cfg = load_config()
        self.download_path = Path(self.cfg.download_folder)
        self.state_file = self.cfg.get_state_file("last_run.json")

    def get_last_run_time(self):
        """
        Return timezone-aware datetime for safe comparison.
        Handles legacy state files that may have naive timestamps.
        """
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("last_run_timestamp")
            if ts:
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
        return datetime(1970, 1, 1, tzinfo=timezone.utc)

    def set_last_run_time(self, dt=None):
        if dt is None:
            dt = datetime.now(timezone.utc)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump({"last_run_timestamp": dt.isoformat()}, f, ensure_ascii=False)

    def _extract_zip(self, zip_path: Path) -> list:
        """
        Extract a .zip file into a subdirectory.
        Forces current timestamp on ALL extracted files so they are picked up
        in the SAME scan cycle.
        Renames the original .zip to .zip.moved.
        Returns list of extracted file paths.
        """
        extracted_files = []
        extract_dir = zip_path.parent / zip_path.stem
        now = datetime.now(timezone.utc).timestamp()

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                total_size = sum(info.file_size for info in zf.infolist())
                if total_size > self.ZIP_SIZE_LIMIT * 5:
                    print(f"[ZIP SKIP] {zip_path.name}: total content {total_size} bytes exceeds safety limit")
                    return extracted_files

                zf.extractall(path=extract_dir)

                for member in zf.namelist():
                    member_path = extract_dir / member
                    if member_path.is_file():
                        os.utime(member_path, (now, now))
                        extracted_files.append(member_path)

                moved_path = zip_path.with_suffix('.zip.moved')
                zip_path.rename(moved_path)
                print(f"[ZIP EXTRACT] {zip_path.name} -> {extract_dir} ({len(extracted_files)} files, timestamp forced)")
                print(f"[ZIP ARCHIVE] Original renamed to {moved_path.name}")

        except zipfile.BadZipFile:
            print(f"[ZIP ERROR] {zip_path.name}: Bad zip file")
        except Exception as e:
            print(f"[ZIP ERROR] {zip_path.name}: {e}")

        return extracted_files

    def scan(self, force=False):
        """
        Scan DOWNLOAD_FOLDER for new files.
        Auto-extracts .zip archives <= 100KB before processing.
        Skips .zip.moved files (already processed).

        Args:
            force: If True, skip mtime > last_run check. Used by daemon on
                   first cycle to catch pre-existing files.
        """
        last_run = self.get_last_run_time()
        new_files = []

        if not self.download_path.exists():
            return new_files

        # Phase 1: Handle .zip files first (extract them)
        for zip_file in self.download_path.rglob("*.zip"):
            if not zip_file.is_file():
                continue
            if zip_file.name.startswith("."):
                continue

            file_size = zip_file.stat().st_size
            if file_size > self.ZIP_SIZE_LIMIT:
                print(f"[ZIP SKIP] {zip_file.name}: {file_size} bytes > {self.ZIP_SIZE_LIMIT} bytes limit")
                continue

            extracted = self._extract_zip(zip_file)
            for extracted_path in extracted:
                meta = self._extract_frontmatter(extracted_path)
                new_files.append({
                    "path": str(extracted_path),
                    "relative_path": str(extracted_path.relative_to(self.download_path)),
                    "original_name": extracted_path.name,
                    "mtime": datetime.now(timezone.utc).isoformat(),
                    "frontmatter": meta,
                    "classified": meta is not None and "name" in meta,
                    "source": "zip_extracted",
                    "zip_source": zip_file.name,
                })

        # Phase 2: Scan regular files (non-zip, non-.moved)
        for file_path in self.download_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.name.startswith("."):
                continue
            if file_path.suffix == ".zip":
                continue
            if file_path.suffix == ".moved" and file_path.stem.endswith(".zip"):
                continue

            mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)

            # v1.0.6 FIX: force mode skips mtime check for daemon first cycle
            if not force and mtime <= last_run:
                continue

            meta = self._extract_frontmatter(file_path)
            new_files.append({
                "path": str(file_path),
                "relative_path": str(file_path.relative_to(self.download_path)),
                "original_name": file_path.name,
                "mtime": mtime.isoformat(),
                "frontmatter": meta,
                "classified": meta is not None and "name" in meta,
                "source": "direct",
            })

        return new_files

    def _extract_frontmatter(self, file_path):
        """Extract frontmatter without external YAML library."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        if file_path.suffix == ".md" and content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                return self._parse_simple_yaml(content[3:end])

        if file_path.suffix == ".py":
            match = re.search(r'"""\s*---\s*(.*?)\s*---\s*"""', content, re.DOTALL)
            if match:
                return self._parse_simple_yaml(match.group(1))

        if file_path.suffix == ".json":
            try:
                data = json.loads(content)
                if "_meta" in data:
                    return data["_meta"]
            except json.JSONDecodeError:
                pass

        return None

    def _parse_simple_yaml(self, yaml_text):
        """Parse a simple subset of YAML: key: value and basic nesting."""
        result = {}
        current_key = None
        current_dict = None

        for line in yaml_text.splitlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue

            match = re.match(r'^(\s*)([\w_]+):\s*(.*)$', line)
            if match:
                indent, key, value = match.groups()
                indent_level = len(indent)

                if indent_level == 0:
                    current_key = key
                    if not value:
                        result[key] = {}
                        current_dict = result[key]
                    else:
                        value = value.strip().strip('"').strip("'")
                        result[key] = value
                        current_dict = None
                elif current_dict is not None and indent_level > 0:
                    value = value.strip().strip('"').strip("'")
                    current_dict[key] = value

        return result if result else None


if __name__ == "__main__":
    scanner = LocalScanner()
    files = scanner.scan()
    print(json.dumps(files, indent=2, ensure_ascii=False, default=str))
    scanner.set_last_run_time()
