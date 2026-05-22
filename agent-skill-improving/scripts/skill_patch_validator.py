"""
---
title: "Skill Patch Validator - Post-Modification Improvement & Validation"
name: "agent-skill-improving"
description: "Analyzes existing skill bundles after modification, identifies deviations from established conventions, generates patch recommendations, and validates against known traps from v1.0.4-1.0.11 lessons. Integrates with integrity checker for comprehensive validation. Auto-classifies issues as [FRAMEWORK], [RUNTIME], or [AGENT-BUG]."
version: "1.2.5"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-22T18:26:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "{baseDir}/skill_patch_validator.py"
  github_path: "agent-skill-improving/scripts/skill_patch_validator.py"
---
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum


class IssueCategory(Enum):
    """Three-layer defense mechanism issue classification."""
    FRAMEWORK = "[FRAMEWORK]"      # Framework issues requiring owner decision
    RUNTIME = "[RUNTIME]"          # Runtime issues agent can handle
    AGENT_BUG = "[AGENT-BUG]"      # Agent violated known conventions


class Severity(Enum):
    CRITICAL = "CRITICAL"    # Blocks upload/execution
    HIGH = "HIGH"            # Must fix before release
    MEDIUM = "MEDIUM"        # Should fix, not blocking
    LOW = "LOW"              # Nice to have


@dataclass
class ValidationIssue:
    """Standard issue record for skill validation."""
    category: IssueCategory
    severity: Severity
    file_path: str
    check_id: str
    title: str
    description: str
    root_cause: str = ""
    attempted_fix: str = ""
    suggested_fix: str = ""
    line_number: int = 0
    snippet: str = ""

    def to_dict(self) -> Dict:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "check_id": self.check_id,
            "title": self.title,
            "description": self.description,
            "root_cause": self.root_cause,
            "attempted_fix": self.attempted_fix,
            "suggested_fix": self.suggested_fix,
            "line_number": self.line_number,
            "snippet": self.snippet,
        }


class SkillPatchValidator:
    """
    Post-modification validator for skill bundles.

    Implements three-layer defense:
    - Layer 1: Framework Guard (naming, frontmatter, path safety)
    - Layer 2: Self-Diagnosis (known traps from v1.0.4-1.0.11)
    - Layer 3: Issue Classifier (auto-tag FRAMEWORK/RUNTIME/AGENT-BUG)
    """

    # Known traps from v1.0.4 to v1.0.11 (per memory #34)
    KNOWN_TRAPS = {
        "TRAP-001": "compare_skill path prefix misalignment",
        "TRAP-002": "action判定遺漏local_only",
        "TRAP-003": "upload_skill frontmatter overwritten by files[0]",
        "TRAP-004": "API placeholder called without replacement",
        "TRAP-005": "skill_dir_name using temp directory name",
        "TRAP-006": "local_dir derived from files[0] pointing to parent",
        "TRAP-007": "expanduser(~) not expanded",
        "TRAP-008": "frontmatter validation too strict for all files",
        "TRAP-009": "semantic-release CHANGELOG.md missing frontmatter",
        "TRAP-010": "upload_skill not filtering files list",
        "TRAP-011": "github_path leading slash causing double slash",
        "TRAP-012": "missing _is_excluded_path check for parent dirs",
        "TRAP-013": "_create_clean_temp_dir not using exclusion filter",
        "TRAP-014": "CHANGELOG validation skipped incorrectly",
    }

    # Excluded paths (per memory #28)
    EXCLUDED_PATTERNS = [
        r"__pycache__",
        r"\.backups",
        r"\.git",
        r"\.env",
        r"\.env\.local",
        r"LICENSE$",
        r"\.pyc$",
        r"\.log$",
    ]

    REQUIRED_FRONTMATTER_FIELDS = [
        "title", "name", "description", "version",
        "github_repository", "target_branch", "updated_at",
        "auth_config", "file_mapping"
    ]

    def __init__(self, skill_dir: str, strict: bool = True):
        self.skill_dir = Path(skill_dir).expanduser().resolve()
        self.strict = strict
        self.issues: List[ValidationIssue] = []
        self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        self._file_cache: Dict[str, str] = {}  # path -> content cache

    def _is_excluded_path(self, path: Path) -> bool:
        """Check if path should be excluded from validation."""
        path_str = str(path)
        for pattern in self.EXCLUDED_PATTERNS:
            if re.search(pattern, path_str):
                return True
        return False

    def _load_file(self, file_path: Path) -> Optional[str]:
        """Load file content with caching."""
        key = str(file_path)
        if key not in self._file_cache:
            try:
                self._file_cache[key] = file_path.read_text(encoding="utf-8")
            except Exception as e:
                self._add_issue(
                    category=IssueCategory.RUNTIME,
                    severity=Severity.HIGH,
                    file_path=key,
                    check_id="FILE-001",
                    title="File read failure",
                    description=f"Cannot read file: {e}",
                )
                return None
        return self._file_cache[key]

    def _add_issue(self, **kwargs) -> None:
        """Add an issue to the collection."""
        self.issues.append(ValidationIssue(**kwargs))

    def _extract_frontmatter(self, content: str, file_path: Path) -> Optional[Dict]:
        """Extract frontmatter from .md (YAML) or .py (docstring YAML)."""
        ext = file_path.suffix.lower()

        if ext == ".md":
            # YAML frontmatter between ---
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if match:
                return self._parse_yaml_frontmatter(match.group(1), str(file_path))
        elif ext == ".py":
            # Docstring YAML block between """ and ---
            match = re.search(r'"""\s*\n---\s*\n(.*?)\n---\s*\n"""', content, re.DOTALL)
            if match:
                return self._parse_yaml_frontmatter(match.group(1), str(file_path))
        elif ext in [".json", ".html"]:
            # For files that don't support frontmatter natively,
            # check first comment block or directory-level mapping
            # (Simplified: check for YAML in first 500 chars)
            match = re.search(r"^\s*/*\s*---\s*\n(.*?)\n---", content, re.DOTALL)
            if match:
                return self._parse_yaml_frontmatter(match.group(1), str(file_path))

        return None

    def _parse_yaml_frontmatter(self, yaml_text: str, file_path: str) -> Optional[Dict]:
        """Parse simple YAML frontmatter (not full YAML parser)."""
        result = {}
        current_key = None
        current_dict = None

        for line in yaml_text.strip().split("\n"):
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue

            # Check for nested dict (2-space indent + key:)
            indent_match = re.match(r"^(\s+)(\w+):\s*(.*)$", line)
            if indent_match and current_key and isinstance(result.get(current_key), dict):
                indent, sub_key, sub_val = indent_match.groups()
                result[current_key][sub_key] = sub_val.strip().strip('"').strip("'")
                continue

            # Top-level key
            match = re.match(r"^(\w+):\s*(.*)$", line)
            if match:
                key, val = match.groups()
                val = val.strip().strip('"').strip("'")
                if val == "":
                    result[key] = {}  # Expect nested values
                    current_key = key
                else:
                    result[key] = val

        return result if result else None

    # ==================== CHECK METHODS ====================

    def check_frontmatter_completeness(self, file_path: Path, content: str) -> None:
        """CHECK-001: Verify all required frontmatter fields present."""
        fm = self._extract_frontmatter(content, file_path)
        file_str = str(file_path.relative_to(self.skill_dir))

        if fm is None:
            # Special case: CHANGELOG.md may be auto-generated (per memory #34)
            if file_path.name == "CHANGELOG.md":
                self._add_issue(
                    category=IssueCategory.AGENT_BUG,
                    severity=Severity.MEDIUM,
                    file_path=file_str,
                    check_id="CHECK-001A",
                    title="CHANGELOG.md missing frontmatter",
                    description="Auto-generated CHANGELOG.md lacks frontmatter. Run CI post-processing to inject identity block.",
                    suggested_fix="Add release_v2_dynamic.yml workflow to inject frontmatter after semantic-release generation.",
                )
                return

            self._add_issue(
                category=IssueCategory.AGENT_BUG,
                severity=Severity.CRITICAL,
                file_path=file_str,
                check_id="CHECK-001",
                title="Missing frontmatter identity block",
                description="File lacks required frontmatter/docstring YAML block. All skill files must carry identity card.",
                root_cause="Agent created file without using skill_files_designer or frontmatter_generator.",
                suggested_fix="Re-generate file using skill_files_designer.py or manually inject standard frontmatter.",
            )
            return

        missing = [f for f in self.REQUIRED_FRONTMATTER_FIELDS if f not in fm]
        if missing:
            self._add_issue(
                category=IssueCategory.AGENT_BUG,
                severity=Severity.CRITICAL,
                file_path=file_str,
                check_id="CHECK-001B",
                title="Incomplete frontmatter fields",
                description=f"Missing required fields: {', '.join(missing)}",
                suggested_fix=f"Add missing fields to frontmatter: {missing}",
            )

    def check_naming_convention(self, file_path: Path) -> None:
        """CHECK-002: Verify file naming conventions."""
        file_str = str(file_path.relative_to(self.skill_dir))
        name = file_path.name

        # .py files: underscore allowed (exempt from dot rule, per memory #13)
        if file_path.suffix == ".py":
            if "-" in name:
                self._add_issue(
                    category=IssueCategory.AGENT_BUG,
                    severity=Severity.HIGH,
                    file_path=file_str,
                    check_id="CHECK-002",
                    title="Python file uses hyphen",
                    description=".py files must use underscore separator, not hyphen.",
                    suggested_fix=f"Rename to {name.replace('-', '_')}",
                )
        else:
            # Non-.py files: dot-separated only, no underscore/hyphen (per memory #4)
            if "_" in name and "." not in name.replace(".", ""):
                # Exception: .backups, __pycache__ already excluded
                self._add_issue(
                    category=IssueCategory.AGENT_BUG,
                    severity=Severity.HIGH,
                    file_path=file_str,
                    check_id="CHECK-002B",
                    title="Non-Python file uses underscore",
                    description="Non-.py skill files must use dot-separated naming.",
                    suggested_fix=f"Rename to {name.replace('_', '.')}",
                )

    def check_github_path_leading_slash(self, file_path: Path, content: str) -> None:
        """CHECK-003: Detect github_path with leading slash (per memory #31)."""
        fm = self._extract_frontmatter(content, file_path)
        if not fm or "file_mapping" not in fm:
            return

        file_str = str(file_path.relative_to(self.skill_dir))
        fm_data = fm.get("file_mapping", {})
        github_path = fm_data.get("github_path", "") if isinstance(fm_data, dict) else ""

        if github_path.startswith("/"):
            self._add_issue(
                category=IssueCategory.AGENT_BUG,
                severity=Severity.CRITICAL,
                file_path=file_str,
                check_id="CHECK-003",
                title="github_path has leading slash",
                description=f"github_path '{github_path}' starts with '/'. This causes GitHub API double-slash, compare_skill mismatch, and upload path errors.",
                root_cause="Agent incorrectly prefixed github_path with '/'.",
                suggested_fix=f"Change to '{github_path.lstrip('/')}' (relative path, no leading slash).",
            )

    def check_version_consistency(self, all_files: List[Path]) -> None:
        """CHECK-004: All files in skill must share same version."""
        versions = {}
        for fp in all_files:
            content = self._load_file(fp)
            if not content:
                continue
            fm = self._extract_frontmatter(content, fp)
            if fm and "version" in fm:
                versions[str(fp.relative_to(self.skill_dir))] = fm["version"]

        if len(set(versions.values())) > 1:
            version_list = "\n".join([f"  {k}: {v}" for k, v in versions.items()])
            self._add_issue(
                category=IssueCategory.AGENT_BUG,
                severity=Severity.HIGH,
                file_path="SKILL_BUNDLE",
                check_id="CHECK-004",
                title="Version inconsistency across files",
                description=f"Files have different version values:\n{version_list}",
                root_cause="Agent modified some files without updating version across all files.",
                suggested_fix="Align all files to the same version number. Use semantic versioning.",
            )

    def check_deletion_safety(self, file_path: Path, content: str) -> None:
        """CHECK-005: Detect unsafe deletion operations (per memory #21)."""
        file_str = str(file_path.relative_to(self.skill_dir))

        # Dangerous patterns
        dangerous = [
            (r"shutil\.rmtree\s*\(", "shutil.rmtree() call detected"),
            (r"os\.remove\s*\(", "os.remove() call detected"),
            (r"os\.rmdir\s*\(", "os.rmdir() call detected"),
            (r"os\.unlink\s*\(", "os.unlink() call detected"),
            (r"\.write_text\s*\([^)]*", "Direct write_text() call"),
            (r"open\s*\([^)]*['"]w", "Direct file open() with write mode"),
        ]

        for pattern, desc in dangerous:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count("\n") + 1
                snippet = content[max(0, match.start()-30):match.end()+30]

                # Check if it's guarded by confirmation logic
                context = content[max(0, match.start()-200):match.start()]
                has_confirm = "confirm" in context.lower() or "user" in context.lower()

                severity = Severity.MEDIUM if has_confirm else Severity.CRITICAL

                self._add_issue(
                    category=IssueCategory.FRAMEWORK if not has_confirm else IssueCategory.RUNTIME,
                    severity=severity,
                    file_path=file_str,
                    check_id="CHECK-005",
                    title=f"Unsafe file operation: {desc}",
                    description=f"{desc} without explicit user confirmation mechanism.",
                    root_cause="Agent may delete/modify files without owner approval.",
                    suggested_fix="Add confirmation prompt or --confirm flag. Log to cleanup list for owner approval.",
                    line_number=line_num,
                    snippet=snippet.replace("\n", " ")[:100],
                )

    def check_path_safety(self, file_path: Path, content: str) -> None:
        """CHECK-006: Detect path traversal and unsafe path construction."""
        file_str = str(file_path.relative_to(self.skill_dir))

        # Check for path traversal patterns
        traversal_patterns = [
            r"\.\.[/\\]",  # ../ or ..\
            r"expanduser.*join.*\.\.",  # expanduser with parent reference
        ]

        for pattern in traversal_patterns:
            if re.search(pattern, content):
                self._add_issue(
                    category=IssueCategory.AGENT_BUG,
                    severity=Severity.HIGH,
                    file_path=file_str,
                    check_id="CHECK-006",
                    title="Potential path traversal vulnerability",
                    description="Code contains patterns that may allow directory traversal outside intended scope.",
                    suggested_fix="Use Path.resolve() and validate against allowed base directories.",
                )

    def check_api_placeholder(self, file_path: Path, content: str) -> None:
        """CHECK-007: Detect API placeholder not replaced (TRAP-004)."""
        file_str = str(file_path.relative_to(self.skill_dir))

        placeholder_patterns = [
            r"YOUR_API_KEY_HERE",
            r"placeholder",
            r"example\.com",
            r"xxxxxx",
            r"TODO.*API",
            r"FIXME.*API",
        ]

        for pattern in placeholder_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count("\n") + 1
                self._add_issue(
                    category=IssueCategory.AGENT_BUG,
                    severity=Severity.HIGH,
                    file_path=file_str,
                    check_id="CHECK-007",
                    title="API placeholder not replaced",
                    description=f"Found placeholder pattern '{pattern}' in code.",
                    root_cause="Agent failed to replace placeholder with actual implementation.",
                    suggested_fix="Replace with actual API endpoint or configuration variable.",
                    line_number=line_num,
                )

    def check_known_traps(self, file_path: Path, content: str) -> None:
        """CHECK-008: Check for known traps from v1.0.4-1.0.11."""
        file_str = str(file_path.relative_to(self.skill_dir))

        trap_signatures = {
            "TRAP-001": (r"compare_skill.*prefix", "compare_skill path prefix misalignment"),
            "TRAP-003": (r"upload_skill.*files\[0\].*frontmatter", "upload_skill frontmatter overwritten"),
            "TRAP-005": (r"skill_dir_name.*temp", "skill_dir_name using temp directory"),
            "TRAP-007": (r"expanduser.*~.*not", "expanduser not expanded"),
            "TRAP-011": (r"github_path.*=.*["']/", "github_path leading slash"),
        }

        for trap_id, (pattern, desc) in trap_signatures.items():
            if re.search(pattern, content, re.IGNORECASE):
                self._add_issue(
                    category=IssueCategory.AGENT_BUG,
                    severity=Severity.HIGH,
                    file_path=file_str,
                    check_id=f"CHECK-008-{trap_id}",
                    title=f"Known trap detected: {trap_id}",
                    description=f"{desc}. This was a confirmed bug in previous versions.",
                    root_cause=f"Agent reproduced known bug {trap_id}.",
                    suggested_fix=f"Refer to fix documentation for {trap_id}.",
                )

    def check_skill_md_location(self, all_files: List[Path]) -> None:
        """CHECK-009: SKILL.md must be at root, not LLM/SKILL.md (per memory #11)."""
        skill_md_paths = [f for f in all_files if f.name == "SKILL.md"]

        for fp in skill_md_paths:
            rel = str(fp.relative_to(self.skill_dir))
            if rel != "SKILL.md":
                self._add_issue(
                    category=IssueCategory.AGENT_BUG,
                    severity=Severity.HIGH,
                    file_path=rel,
                    check_id="CHECK-009",
                    title="SKILL.md not at root directory",
                    description=f"SKILL.md found at '{rel}', but must be at root directory per architecture rules.",
                    root_cause="Agent placed SKILL.md in subdirectory instead of root.",
                    suggested_fix="Move SKILL.md to root directory. USAGE.md goes to scripts/USAGE.md.",
                )

    def check_usage_md_location(self, all_files: List[Path]) -> None:
        """CHECK-010: USAGE.md must be at scripts/USAGE.md (per memory #11)."""
        usage_files = [f for f in all_files if f.name == "USAGE.md"]

        for fp in usage_files:
            rel = str(fp.relative_to(self.skill_dir))
            if rel != "scripts/USAGE.md":
                self._add_issue(
                    category=IssueCategory.AGENT_BUG,
                    severity=Severity.MEDIUM,
                    file_path=rel,
                    check_id="CHECK-010",
                    title="USAGE.md not in scripts directory",
                    description=f"USAGE.md found at '{rel}', but should be at scripts/USAGE.md.",
                    suggested_fix="Move USAGE.md to scripts/USAGE.md.",
                )

    def check_name_field_consistency(self, all_files: List[Path]) -> None:
        """CHECK-011: All files' name field must match skill directory name."""
        skill_name_from_dir = self.skill_dir.name

        for fp in all_files:
            content = self._load_file(fp)
            if not content:
                continue
            fm = self._extract_frontmatter(content, fp)
            if not fm or "name" not in fm:
                continue

            file_name = fm["name"]
            if file_name != skill_name_from_dir:
                rel = str(fp.relative_to(self.skill_dir))
                self._add_issue(
                    category=IssueCategory.AGENT_BUG,
                    severity=Severity.HIGH,
                    file_path=rel,
                    check_id="CHECK-011",
                    title="Name field mismatch",
                    description=f"File claims name='{file_name}' but directory is '{skill_name_from_dir}'.",
                    suggested_fix=f"Update name field to '{skill_name_from_dir}' or rename directory.",
                )

    def check_updated_at_format(self, file_path: Path, content: str) -> None:
        """CHECK-012: Verify updated_at is ISO 8601 format (per memory #19)."""
        fm = self._extract_frontmatter(content, file_path)
        if not fm or "updated_at" not in fm:
            return

        file_str = str(file_path.relative_to(self.skill_dir))
        updated_at = fm["updated_at"]

        # ISO 8601 pattern: YYYY-MM-DDTHH:MM:SS+HH:MM
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$"
        if not re.match(iso_pattern, updated_at):
            self._add_issue(
                category=IssueCategory.AGENT_BUG,
                severity=Severity.MEDIUM,
                file_path=file_str,
                check_id="CHECK-012",
                title="Invalid updated_at format",
                description=f"updated_at '{updated_at}' is not valid ISO 8601 format.",
                suggested_fix="Use format: YYYY-MM-DDTHH:MM:SS+HH:MM (e.g., 2026-05-22T18:26:00+08:00)",
            )

    # ==================== MAIN VALIDATION ====================

    def validate(self) -> List[ValidationIssue]:
        """Run full validation suite."""
        if not self.skill_dir.exists():
            self._add_issue(
                category=IssueCategory.RUNTIME,
                severity=Severity.CRITICAL,
                file_path=str(self.skill_dir),
                check_id="VAL-001",
                title="Skill directory not found",
                description=f"Directory does not exist: {self.skill_dir}",
            )
            return self.issues

        # Collect all relevant files
        all_files = []
        for fp in self.skill_dir.rglob("*"):
            if fp.is_file() and not self._is_excluded_path(fp):
                all_files.append(fp)

        if not all_files:
            self._add_issue(
                category=IssueCategory.RUNTIME,
                severity=Severity.CRITICAL,
                file_path=str(self.skill_dir),
                check_id="VAL-002",
                title="No valid files found in skill directory",
                description="Directory exists but contains no valid skill files after exclusion filtering.",
            )
            return self.issues

        # Run file-level checks
        for fp in all_files:
            content = self._load_file(fp)
            if not content:
                continue

            self.check_frontmatter_completeness(fp, content)
            self.check_naming_convention(fp)
            self.check_github_path_leading_slash(fp, content)
            self.check_deletion_safety(fp, content)
            self.check_path_safety(fp, content)
            self.check_api_placeholder(fp, content)
            self.check_known_traps(fp, content)
            self.check_updated_at_format(fp, content)

        # Run bundle-level checks
        self.check_version_consistency(all_files)
        self.check_skill_md_location(all_files)
        self.check_usage_md_location(all_files)
        self.check_name_field_consistency(all_files)

        return self.issues

    # ==================== REPORT GENERATION ====================

    def generate_report(self, output_format: str = "markdown") -> str:
        """Generate validation report in specified format."""
        if output_format == "json":
            return self._generate_json_report()
        return self._generate_markdown_report()

    def _generate_markdown_report(self) -> str:
        """Generate standard Markdown report (per memory #31 Issue format)."""
        lines = [
            f"# Skill Patch Validation Report",
            f"",
            f"**Skill Directory**: `{self.skill_dir}`",
            f"**Validation Time**: {self.timestamp}",
            f"**Total Issues**: {len(self.issues)}",
            f"**Strict Mode**: {'Yes' if self.strict else 'No'}",
            f"",
            f"## Summary by Severity",
            f"",
        ]

        # Severity summary
        severity_counts = {}
        for issue in self.issues:
            severity_counts[issue.severity.value] = severity_counts.get(issue.severity.value, 0) + 1

        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = severity_counts.get(sev, 0)
            emoji = "🔴" if sev == "CRITICAL" else "🟠" if sev == "HIGH" else "🟡" if sev == "MEDIUM" else "🟢"
            lines.append(f"| {emoji} {sev} | {count} |")

        lines.extend([
            "",
            "## Summary by Category",
            "",
        ])

        # Category summary
        cat_counts = {}
        for issue in self.issues:
            cat_counts[issue.category.value] = cat_counts.get(issue.category.value, 0) + 1

        for cat in ["[FRAMEWORK]", "[RUNTIME]", "[AGENT-BUG]"]:
            count = cat_counts.get(cat, 0)
            lines.append(f"| {cat} | {count} |")

        lines.extend([
            "",
            "---",
            "",
            "## Detailed Issues",
            "",
        ])

        # Group by category
        for category in IssueCategory:
            cat_issues = [i for i in self.issues if i.category == category]
            if not cat_issues:
                continue

            lines.extend([
                f"### {category.value} Issues ({len(cat_issues)})",
                "",
            ])

            for i, issue in enumerate(cat_issues, 1):
                lines.extend([
                    f"#### {i}. {issue.title}",
                    f"",
                    f"- **Check ID**: `{issue.check_id}`",
                    f"- **Severity**: {issue.severity.value}",
                    f"- **File**: `{issue.file_path}`",
                    f"- **Line**: {issue.line_number if issue.line_number else 'N/A'}",
                    f"",
                    f"**Description**:",
                    f"{issue.description}",
                    f"",
                ])
                if issue.root_cause:
                    lines.extend([
                        f"**Root Cause Analysis**:",
                        f"{issue.root_cause}",
                        f"",
                    ])
                if issue.attempted_fix:
                    lines.extend([
                        f"**Attempted Fix**:",
                        f"{issue.attempted_fix}",
                        f"",
                    ])
                lines.extend([
                    f"**Suggested Fix**:",
                    f"{issue.suggested_fix}",
                    f"",
                ])
                if issue.snippet:
                    lines.extend([
                        f"**Code Snippet**:",
                        f"```python",
                        f"{issue.snippet}",
                        f"```",
                        f"",
                    ])
                lines.append("---")
                lines.append("")

        # Standard Issue format footer (per memory #31)
        lines.extend([
            "",
            "## Standard Issue Format (For GitHub Issues)",
            "",
            "When creating GitHub Issues for [FRAMEWORK] items, use this structure:",
            "",
            "### 問題摘要",
            "[50+ characters minimum description]",
            "",
            "### 復現步驟",
            "1. [Step 1]",
            "2. [Step 2]",
            "",
            "### 根因分析",
            "[Detailed root cause, 50+ characters]",
            "",
            "### 已嘗試的修復",
            "[What has been tried, 50+ characters]",
            "",
            "### 建議修復方案",
            "[Proposed solution, 50+ characters]",
            "",
            "### 分類",
            "[FRAMEWORK] / [RUNTIME] / [AGENT-BUG]",
            "",
            "### 驗證結果",
            "[How to verify the fix works]",
            "",
        ])

        return "\n".join(lines)

    def _generate_json_report(self) -> str:
        """Generate JSON report for programmatic consumption."""
        report = {
            "meta": {
                "skill_dir": str(self.skill_dir),
                "timestamp": self.timestamp,
                "total_issues": len(self.issues),
                "strict_mode": self.strict,
            },
            "summary": {
                "by_severity": {},
                "by_category": {},
            },
            "issues": [asdict(i) for i in self.issues],
        }

        for issue in self.issues:
            sev = issue.severity.value
            cat = issue.category.value
            report["summary"]["by_severity"][sev] = report["summary"]["by_severity"].get(sev, 0) + 1
            report["summary"]["by_category"][cat] = report["summary"]["by_category"].get(cat, 0) + 1

        return json.dumps(report, indent=2, ensure_ascii=False)

    def generate_patch_script(self) -> Optional[str]:
        """Generate a patch script for auto-fixable issues."""
        # Identify auto-fixable issues
        fixable = [i for i in self.issues if i.check_id in ["CHECK-003", "CHECK-011", "CHECK-012"]]

        if not fixable:
            return None

        lines = [
            "#!/usr/bin/env python3",
            """"Auto-generated patch script for skill validation issues."""",
            "",
            "import re",
            "from pathlib import Path",
            "",
            f"SKILL_DIR = Path("{self.skill_dir}")",
            "",
            "def apply_patches():",
            "    patches_applied = 0",
            "",
        ]

        for issue in fixable:
            if issue.check_id == "CHECK-003":  # Leading slash
                lines.extend([
                    f"    # Fix {issue.check_id}: Remove leading slash from github_path",
                    f"    file_path = SKILL_DIR / "{issue.file_path}"",
                    f"    content = file_path.read_text(encoding='utf-8')",
                    f"    content = re.sub(r'github_path:\s*"/', 'github_path: "', content)",
                    f"    file_path.write_text(content, encoding='utf-8')",
                    f"    patches_applied += 1",
                    "",
                ])

        lines.extend([
            "    print(f"Applied {patches_applied} patches")",
            "",
            "if __name__ == '__main__':",
            "    apply_patches()",
            "",
        ])

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Validate and generate improvement patches for skill bundles"
    )
    parser.add_argument("--skill-dir", required=True, help="Path to skill directory to validate")
    parser.add_argument("--strict", action="store_true", default=True,
                       help="Strict mode: treat missing frontmatter as critical (default: True)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown",
                       help="Output report format")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--generate-patch", action="store_true",
                       help="Generate auto-fix patch script if fixable issues found")
    parser.add_argument("--patch-output", default="skill_auto_patch.py",
                       help="Patch script output path")

    args = parser.parse_args()

    validator = SkillPatchValidator(
        skill_dir=args.skill_dir,
        strict=args.strict
    )

    print(f"[INFO] Validating skill directory: {validator.skill_dir}")
    issues = validator.validate()

    # Generate report
    report = validator.generate_report(output_format=args.format)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(report, encoding="utf-8")
        print(f"[INFO] Report written to: {output_path}")
    else:
        print("\n" + "="*60)
        print(report)

    # Summary
    critical = sum(1 for i in issues if i.severity == Severity.CRITICAL)
    high = sum(1 for i in issues if i.severity == Severity.HIGH)

    print(f"\n[SUMMARY] Total: {len(issues)} | Critical: {critical} | High: {high}")

    if critical > 0:
        print("[RESULT] FAILED - Critical issues found. Must fix before upload.")
        sys.exit(1)
    elif high > 0:
        print("[RESULT] WARNING - High severity issues found. Recommend fixing before release.")
    else:
        print("[RESULT] PASSED - No critical or high severity issues.")

    # Generate patch script
    if args.generate_patch:
        patch = validator.generate_patch_script()
        if patch:
            patch_path = Path(args.patch_output)
            patch_path.write_text(patch, encoding="utf-8")
            print(f"[INFO] Auto-fix patch written to: {patch_path}")
        else:
            print("[INFO] No auto-fixable issues found.")


if __name__ == "__main__":
    main()
