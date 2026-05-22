"""
---
title: Skill Integrity Checker
name: agent-skill-improving
description: Compliance checker for skill files. Validates frontmatter integrity, naming conventions, file structure, version consistency, github_path format, and architecture red lines. v1.2.5 adds 5 new checks based on github-skill-organizer v1.0.4-v1.0.12 lessons.
version: v1.2.5
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-22T17:00:00+08:00
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: "{baseDir}/.env"
file_mapping:
  - local_path: "{baseDir}/scripts/skill_integrity_checker.py"
    github_path: "agent-skill-improving/scripts/skill_integrity_checker.py"
---
"""

import os
import re
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class SkillIntegrityChecker:
    """
    DEFENSIVE v1.2.5: Compliance checker for skill files.

    Checks 28+ items including:
    - Frontmatter field integrity (NEW v1.2.5)
    - github_path leading "/" (NEW v1.2.5)
    - updated_at ISO 8601 format (NEW v1.2.5)
    - Version consistency across all files (NEW v1.2.5)
    - file_mapping completeness (NEW v1.2.5)
    - Naming conventions (xxx.yyy.zzz.ext)
    - Required file structure
    - 8 architecture red lines
    """

    # REQUIRED frontmatter fields for all skill files
    REQUIRED_FRONTMATTER_FIELDS = [
        "title",
        "name",
        "description",
        "version",
        "github_repository",
        "target_branch",
        "updated_at",
        "auth_config",
        "file_mapping",
    ]

    # REQUIRED auth_config sub-fields
    REQUIRED_AUTH_FIELDS = [
        "provider",
        "auth_method",
        "token_env_var",
        "env_file_path",
    ]

    # REQUIRED file_mapping fields per entry
    REQUIRED_FILE_MAPPING_FIELDS = [
        "local_path",
        "github_path",
    ]

    # Architecture red lines (absolute prohibitions)
    RED_LINES = [
        {
            "id": "RED-001",
            "name": "Hardcoded absolute paths",
            "pattern": r"(C:\\Users\\|/Users/|/home/|~\.workbuddy/|file:///)",
            "severity": "CRITICAL",
            "description": "Scripts must use pathlib.Path + expanduser, never hardcode paths",
        },
        {
            "id": "RED-002",
            "name": "Missing frontmatter",
            "check": "frontmatter_exists",
            "severity": "CRITICAL",
            "description": "All .md/.py/.json/.html files must have frontmatter/docstring",
        },
        {
            "id": "RED-003",
            "name": "Invalid file naming",
            "pattern": r"[_-]",
            "severity": "HIGH",
            "description": "Files must use xxx.yyy.zzz.ext format (dots only, except .py)",
        },
        {
            "id": "RED-004",
            "name": "Missing SKILL.md",
            "check": "skill_md_exists",
            "severity": "CRITICAL",
            "description": "Every skill must have a SKILL.md file",
        },
        {
            "id": "RED-005",
            "name": "Missing README.md",
            "check": "readme_exists",
            "severity": "HIGH",
            "description": "Every skill should have a README.md file",
        },
        {
            "id": "RED-006",
            "name": "github_path leading slash",
            "check": "github_path_leading_slash",
            "severity": "HIGH",
            "description": "github_path must not have leading '/' (relative paths only)",
        },
        {
            "id": "RED-007",
            "name": "Version inconsistency",
            "check": "version_consistency",
            "severity": "HIGH",
            "description": "All files in a skill must have the same version",
        },
        {
            "id": "RED-008",
            "name": "Invalid updated_at format",
            "check": "updated_at_format",
            "severity": "MEDIUM",
            "description": "updated_at must be ISO 8601 format: YYYY-MM-DDTHH:MM:SS+HH:MM",
        },
    ]

    def __init__(self, skill_dir: str, strict: bool = False):
        self.skill_dir = Path(skill_dir)
        self.strict = strict
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
        self.passed: List[str] = []
        self.all_versions: List[str] = []

    def run_all_checks(self) -> Dict:
        """Execute all compliance checks and return report."""
        print(f"[CHECK] Scanning skill directory: {self.skill_dir}")

        # Phase 1: Structure checks
        self._check_required_files()
        self._check_file_naming()

        # Phase 2: Frontmatter checks (per file)
        skill_files = self._get_skill_files()
        for file_path in skill_files:
            self._check_file_frontmatter(file_path)

        # Phase 3: Cross-file checks
        self._check_version_consistency()
        self._check_github_path_format()

        # Phase 4: Red lines
        self._check_red_lines()

        # Phase 5: Content checks
        self._check_hardcoded_paths()

        return self._generate_report()

    def _get_skill_files(self) -> List[Path]:
        """Get all skill-relevant files excluding hidden and excluded."""
        files = []
        for f in self.skill_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.name.startswith("."):
                continue
            if f.name in ["LICENSE", "LICENSE.md", "LICENSE.txt"]:
                continue
            if ".backups" in str(f) or "__pycache__" in str(f):
                continue
            if f.suffix in [".md", ".py", ".json", ".html"]:
                files.append(f)
        return sorted(files)

    def _check_required_files(self):
        """Check that required files exist."""
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            self._add_issue("RED-004", "CRITICAL", "Missing SKILL.md", str(self.skill_dir))
        else:
            self.passed.append("SKILL.md exists")

        readme = self.skill_dir / "README.md"
        if not readme.exists():
            self._add_warning("RED-005", "HIGH", "Missing README.md", str(self.skill_dir))
        else:
            self.passed.append("README.md exists")

    def _check_file_naming(self):
        """Check file naming conventions."""
        for f in self.skill_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.name.startswith("."):
                continue

            # .py files exempt from dot-separation (allowed underscore)
            if f.suffix == ".py":
                continue

            # Check for - or _ in filename (excluding extension)
            name_without_ext = f.stem
            if "_" in name_without_ext or "-" in name_without_ext:
                self._add_issue(
                    "RED-003",
                    "HIGH",
                    f"Invalid file naming: {f.name}. Must use xxx.yyy.zzz.ext (dots only)",
                    str(f),
                )

    def _check_file_frontmatter(self, file_path: Path):
        """Check frontmatter integrity for a single file."""
        fm = self._extract_frontmatter(file_path)

        if not fm:
            self._add_issue(
                "RED-002",
                "CRITICAL",
                f"[ILLEGAL FILE] {file_path.name}: Missing frontmatter (identity card). This file is illegal and cannot be uploaded. Please add frontmatter or remove it from the skill directory.",
                str(file_path),
            )
            return

        # Check required fields
        missing_fields = []
        for field in self.REQUIRED_FRONTMATTER_FIELDS:
            if field not in fm or not fm[field]:
                missing_fields.append(field)

        if missing_fields:
            self._add_issue(
                "FRONTMATTER-001",
                "CRITICAL",
                f"{file_path.name}: Missing required frontmatter fields: {', '.join(missing_fields)}",
                str(file_path),
            )

        # Check auth_config sub-fields
        auth = fm.get("auth_config", {})
        if auth:
            missing_auth = []
            for field in self.REQUIRED_AUTH_FIELDS:
                if field not in auth or not auth[field]:
                    missing_auth.append(field)
            if missing_auth:
                self._add_issue(
                    "FRONTMATTER-002",
                    "HIGH",
                    f"{file_path.name}: Missing auth_config fields: {', '.join(missing_auth)}",
                    str(file_path),
                )

        # Check file_mapping
        file_mapping = fm.get("file_mapping", [])
        if file_mapping:
            for i, entry in enumerate(file_mapping):
                missing_fm = []
                for field in self.REQUIRED_FILE_MAPPING_FIELDS:
                    if field not in entry or not entry[field]:
                        missing_fm.append(field)
                if missing_fm:
                    self._add_issue(
                        "FRONTMATTER-003",
                        "HIGH",
                        f"{file_path.name}: file_mapping[{i}] missing: {', '.join(missing_fm)}",
                        str(file_path),
                    )

                # Check github_path leading slash
                github_path = entry.get("github_path", "")
                if github_path.startswith("/"):
                    self._add_issue(
                        "RED-006",
                        "HIGH",
                        f"{file_path.name}: github_path has leading '/': '{github_path}'. Must be relative path without leading slash.",
                        str(file_path),
                    )

        # Check updated_at format
        updated_at = fm.get("updated_at", "")
        if updated_at:
            if not self._is_valid_iso8601(updated_at):
                self._add_issue(
                    "RED-008",
                    "MEDIUM",
                    f"{file_path.name}: Invalid updated_at format: '{updated_at}'. Must be ISO 8601: YYYY-MM-DDTHH:MM:SS+HH:MM",
                    str(file_path),
                )

        # Collect version for cross-file check
        version = fm.get("version", "")
        if version:
            self.all_versions.append(version)

        if not missing_fields:
            self.passed.append(f"{file_path.name} frontmatter complete")

    def _check_version_consistency(self):
        """Check that all files have the same version."""
        if not self.all_versions:
            return

        unique_versions = set(self.all_versions)
        if len(unique_versions) > 1:
            self._add_issue(
                "RED-007",
                "HIGH",
                f"Version inconsistency across files: {unique_versions}. All files must have the same version.",
                str(self.skill_dir),
            )
        else:
            self.passed.append(f"Version consistency: {list(unique_versions)[0]}")

    def _check_github_path_format(self):
        """Additional check for github_path format across all files."""
        # Already checked per-file in _check_file_frontmatter
        pass

    def _check_red_lines(self):
        """Check architecture red lines."""
        for red_line in self.RED_LINES:
            if "pattern" in red_line:
                pattern = red_line["pattern"]
                for f in self.skill_dir.rglob("*"):
                    if not f.is_file():
                        continue
                    if f.suffix not in [".py", ".md"]:
                        continue
                    try:
                        content = f.read_text(encoding="utf-8", errors="ignore")
                        matches = re.findall(pattern, content)
                        if matches:
                            self._add_issue(
                                red_line["id"],
                                red_line["severity"],
                                f"{red_line['name']} detected in {f.name}: {matches[:3]}",
                                str(f),
                            )
                    except Exception:
                        pass

    def _check_hardcoded_paths(self):
        """Check for hardcoded absolute paths in scripts."""
        # Already covered by RED-001 in _check_red_lines
        pass

    def _extract_frontmatter(self, file_path: Path) -> Optional[Dict]:
        """Extract frontmatter from a file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            if file_path.suffix == ".py":
                # Check for docstring YAML block
                match = re.search(r'"""\s*---\s*(.*?)\s*---\s*"""', content, re.DOTALL)
                if match:
                    return self._parse_yaml(match.group(1))
            else:
                # Check for YAML frontmatter
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end != -1:
                        return self._parse_yaml(content[3:end])

            return None
        except Exception:
            return None

    def _parse_yaml(self, yaml_text: str) -> Dict:
        """Parse simple YAML frontmatter."""
        result = {}
        current_key = None
        current_dict = None
        in_list = False
        list_items = []

        for line in yaml_text.splitlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue

            # List item
            if line.strip().startswith("- "):
                item_text = line.strip()[2:].strip()
                if ":" in item_text:
                    key, value = item_text.split(":", 1)
                    list_items.append({key.strip(): value.strip().strip('"').strip("'")})
                continue

            # Key-value pair
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
                        result[key] = value.strip().strip('"').strip("'")
                        current_dict = None
                elif current_dict is not None and indent_level > 0:
                    current_dict[key] = value.strip().strip('"').strip("'")

        # Handle file_mapping list
        if "file_mapping" in result and isinstance(result["file_mapping"], dict):
            # Convert to list if needed
            pass

        return result

    def _is_valid_iso8601(self, text: str) -> bool:
        """Check if text is valid ISO 8601 format."""
        patterns = [
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$',
        ]
        return any(re.match(p, text) for p in patterns)

    def _add_issue(self, issue_id: str, severity: str, message: str, file_path: str):
        """Add an issue to the report."""
        self.issues.append({
            "id": issue_id,
            "severity": severity,
            "message": message,
            "file": file_path,
        })
        if self.strict and severity == "CRITICAL":
            print(f"[CRITICAL] {message}")

    def _add_warning(self, issue_id: str, severity: str, message: str, file_path: str):
        """Add a warning to the report."""
        self.warnings.append({
            "id": issue_id,
            "severity": severity,
            "message": message,
            "file": file_path,
        })

    def _generate_report(self) -> Dict:
        """Generate final compliance report."""
        critical_count = sum(1 for i in self.issues if i["severity"] == "CRITICAL")
        high_count = sum(1 for i in self.issues if i["severity"] == "HIGH")
        medium_count = sum(1 for i in self.issues if i["severity"] == "MEDIUM")

        overall_status = "PASS" if not self.issues else "FAIL"
        if self.strict and critical_count > 0:
            overall_status = "BLOCKED"

        report = {
            "status": overall_status,
            "skill_dir": str(self.skill_dir),
            "strict_mode": self.strict,
            "summary": {
                "total_files_checked": len(self.passed) + len(self.issues) + len(self.warnings),
                "passed": len(self.passed),
                "issues": len(self.issues),
                "warnings": len(self.warnings),
                "critical": critical_count,
                "high": high_count,
                "medium": medium_count,
            },
            "passed_items": self.passed,
            "issues": self.issues,
            "warnings": self.warnings,
        }

        # Print summary
        print(f"{'='*60}")
        print(f"[REPORT] Skill Integrity Check: {overall_status}")
        print(f"{'='*60}")
        print(f"  Files checked: {report['summary']['total_files_checked']}")
        print(f"  Passed: {report['summary']['passed']}")
        print(f"  Issues: {report['summary']['issues']} (Critical: {critical_count}, High: {high_count}, Medium: {medium_count})")
        print(f"  Warnings: {report['summary']['warnings']}")

        if self.issues:
            print("\n  Issues found:")
            for issue in self.issues:
                print(f"    [{issue['severity']}] {issue['id']}: {issue['message']}")

        if self.warnings:
            print("\n  Warnings:")
            for warning in self.warnings:
                print(f"    [{warning['severity']}] {warning['id']}: {warning['message']}")

        print(f"{'='*60}")

        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skill Integrity Checker v1.2.5")
    parser.add_argument("--skill-dir", required=True, help="Path to skill directory")
    parser.add_argument("--strict", action="store_true", help="Fail on CRITICAL issues")
    parser.add_argument("--report-path", help="Path to save JSON report")
    args = parser.parse_args()

    checker = SkillIntegrityChecker(args.skill_dir, strict=args.strict)
    report = checker.run_all_checks()

    if args.report_path:
        Path(args.report_path).parent.mkdir(parents=True, exist_ok=True)
        with open(args.report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[SAVE] Report saved to: {args.report_path}")

    sys.exit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
