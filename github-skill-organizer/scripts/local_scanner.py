"""
---
title: Local File Scanner
name: github-skill-organizer
description: Scans DOWNLOAD_FOLDER for new files and extracts frontmatter metadata. Handles Kimi-downloaded files with generic names by reading internal frontmatter.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/local_scanner.py"
  github_path: "github-skill-organizer/scripts/local_scanner.py"
---
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

try:
    from skill_organizer_config import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config


class LocalScanner:
    def __init__(self):
        self.cfg = load_config()
        self.download_path = Path(self.cfg.download_folder)
        self.state_file = self.cfg.get_state_file("last_run.json")

    def get_last_run_time(self):
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                ts = data.get("last_run_timestamp")
                if ts:
                    return datetime.fromisoformat(ts)
        return datetime.min

    def set_last_run_time(self, dt=None):
        if dt is None:
            dt = datetime.utcnow()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump({"last_run_timestamp": dt.isoformat()}, f, ensure_ascii=False)

    def scan(self):
        last_run = self.get_last_run_time()
        new_files = []

        if not self.download_path.exists():
            return new_files

        for file_path in self.download_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.name.startswith("."):
                continue

            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime > last_run:
                meta = self._extract_frontmatter(file_path)
                new_files.append({
                    "path": str(file_path),
                    "relative_path": str(file_path.relative_to(self.download_path)),
                    "original_name": file_path.name,
                    "mtime": mtime.isoformat(),
                    "frontmatter": meta,
                    "classified": meta is not None and "name" in meta,
                })

        return new_files

    def _extract_frontmatter(self, file_path):
        """Extract frontmatter without external YAML library."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        # For .md files: look for --- ... ---
        if file_path.suffix == ".md" and content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                return self._parse_simple_yaml(content[3:end])

        # For .py files: look for """ --- ... --- """
        if file_path.suffix == ".py":
            match = re.search('"""\s*---\s*(.*?)\s*---\s*"""', content, re.DOTALL)
            if match:
                return self._parse_simple_yaml(match.group(1))

        # For .json files: look for _meta field
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

            match = re.match('^(\s*)([\w_]+):\s*(.*)$', line)
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
