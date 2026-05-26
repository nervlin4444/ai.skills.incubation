"""
---
title: "Skill Folder Designer - Initialize New Skill Directory Structure"
name: "agent-skill-improving"
description: "Bootstrap a new skill bundle with standard directory layout, all files pre-populated with unified frontmatter templates. Enforces naming conventions, generates placeholder content for README.md, SKILL.md, USAGE.md, scripts, and configuration files. Requires user confirmation before any disk write operation."
version: "1.3.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T17:07:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
fixes: []
file_mapping:
  local_path: "{baseDir}/skill_folder_designer.py"
  github_path: "agent-skill-improving/scripts/skill_folder_designer.py"
---
"""

import os
import sys
import re
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class SkillFolderDesigner:
    """Initialize new skill bundle with standard structure and unified frontmatter."""

    # LOCK-009: Agent禁止直接寫入文件，必須使用本工具或經主人確認
    # LOCK-010: 所有生成文件必須攜帶frontmatter身份證
    # LOCK-011: 修改後必須調用integrity_checker驗證
    # LOCK-012: 不得修改github_repository/target_branch預設值

    DEFAULT_REPO_OWNER = "nervlin4444"
    DEFAULT_REPO_NAME = "ai.skills.incubation"
    DEFAULT_BRANCH = "main"

    REQUIRED_FRONTMATTER_FIELDS = [
        "title", "name", "description", "version",
        "github_repository", "target_branch", "updated_at",
        "auth_config", "file_mapping"
    ]

    def __init__(self, skill_name: str, base_dir: str = ".", dry_run: bool = True):
        self.skill_name = self._validate_skill_name(skill_name)
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.dry_run = dry_run
        self.skill_dir = self.base_dir / self.skill_name
        self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        self.confirmation_items: List[Dict] = []

    def _validate_skill_name(self, name: str) -> str:
        """Validate skill name conforms to dot-separated convention (except .py files)."""
        name = name.strip().lower()
        if not name:
            raise ValueError("Skill name cannot be empty")
        # Allow dot-separated format like "agent-skill-improving" should be "agent.skill.improving"
        if "_" in name and "." not in name:
            # Auto-convert underscore to dot for non-py files
            converted = name.replace("_", ".")
            print(f"[INFO] Auto-converted skill name: {name} -> {converted}")
            name = converted
        # Validate: no leading/trailing dots, no consecutive dots
        if name.startswith(".") or name.endswith("."):
            raise ValueError("Skill name cannot start or end with dot")
        if ".." in name:
            raise ValueError("Skill name cannot contain consecutive dots")
        return name

    def _generate_frontmatter(self, title: str, description: str, version: str,
                             local_path: str, github_path: str,
                             file_type: str = "md") -> str:
        """Generate unified frontmatter block."""
        fm = f"""---
title: "{title}"
name: "{self.skill_name}"
description: "{description}"
version: "{version}"
github_repository: "{self.DEFAULT_REPO_OWNER}/{self.DEFAULT_REPO_NAME}"
target_branch: "{self.DEFAULT_BRANCH}"
updated_at: "{self.timestamp}"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
fixes: []
file_mapping:
  local_path: "{local_path}"
  github_path: "{github_path}"
---"""
        if file_type == "py":
            # For .py files, wrap in docstring
            q = chr(34) * 3
            return q + "\n" + fm + "\n---\n" + q
        return fm

    def _generate_py_docstring_frontmatter(self, title: str, description: str, version: str,
                                           local_path: str, github_path: str) -> str:
        """Generate frontmatter embedded in Python docstring."""
        q = chr(34) * 3
        lines = [q, "---"]
        lines.append("title: " + chr(34) + title + chr(34))
        lines.append("name: " + chr(34) + self.skill_name + chr(34))
        lines.append("description: " + chr(34) + description + chr(34))
        lines.append("version: " + chr(34) + version + chr(34))
        lines.append("github_repository: " + chr(34) + self.DEFAULT_REPO_OWNER + "/" + self.DEFAULT_REPO_NAME + chr(34))
        lines.append("target_branch: " + chr(34) + self.DEFAULT_BRANCH + chr(34))
        lines.append("updated_at: " + chr(34) + self.timestamp + chr(34))
        lines.append("fixes: []")
        lines.append("auth_config:")
        lines.append("  provider: " + chr(34) + "github" + chr(34))
        lines.append("  auth_method: " + chr(34) + "token" + chr(34))
        lines.append("  token_env_var: " + chr(34) + "GITHUB_TOKEN" + chr(34))
        lines.append("  env_file_path: " + chr(34) + ".env" + chr(34))
        lines.append("file_mapping:")
        lines.append("  local_path: " + chr(34) + local_path + chr(34))
        lines.append("  github_path: " + chr(34) + github_path + chr(34))
        lines.append("---")
        lines.append(q)
        return "\n".join(lines)

    def generate_readme_md(self, description: str = "") -> Tuple[str, str]:
        """Generate README.md content (human-readable guide)."""
        title = f"{self.skill_name} - Skill Bundle"
        desc = description or f"Human-readable guide for {self.skill_name} skill bundle."
        fm = self._generate_frontmatter(
            title=title,
            description=desc,
            version="1.0.0",
            local_path=f"{{baseDir}}/README.md",
            github_path=f"{self.skill_name}/README.md",
            file_type="md"
        )
        content = f"""{fm}

# {self.skill_name}

## Overview

{desc}

## Directory Structure

```
{self.skill_name}/
├── README.md          (This file - Human guide)
├── SKILL.md           (LLM execution instructions)
├── scripts/
│   ├── USAGE.md       (Script usage tutorial)
│   └── [skill_scripts].py
├── .env.example       (Configuration template)
└── .gitignore
```

## Quick Start

1. Copy `.env.example` to `.env` and fill in your credentials
2. Review `SKILL.md` for LLM execution context
3. See `scripts/USAGE.md` for detailed script usage

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0   | {self.timestamp[:10]} | Initial release |

## Contributing

Please refer to the main repository contributing guidelines.
"""
        return "README.md", content

    def generate_skill_md(self) -> Tuple[str, str]:
        """Generate SKILL.md content (LLM execution instructions)."""
        # SKILL.md must be at root directory, not LLM/SKILL.md (per memory #11)
        fm = self._generate_frontmatter(
            title=f"{self.skill_name} - LLM Execution Instructions",
            description=f"Direct execution instructions for LLM agents. This file is the primary entry point for AI agents to understand and execute this skill.",
            version="1.0.0",
            local_path=f"{{baseDir}}/SKILL.md",
            github_path=f"{self.skill_name}/SKILL.md",
            file_type="md"
        )
        content = f"""{fm}

# SKILL EXECUTION INSTRUCTIONS

## Identity

- **Skill Name**: `{self.skill_name}`
- **Version**: `1.0.0`
- **Repository**: `{self.DEFAULT_REPO_OWNER}/{self.DEFAULT_REPO_NAME}`

## Purpose

[LLM: Insert concise execution purpose here. Max 2 sentences.]

## Execution Flow

### Phase 1: Preparation
1. Read `.env` for configuration
2. Validate authentication tokens
3. Load required dependencies

### Phase 2: Core Execution
[LLM: Define step-by-step execution logic. Use numbered lists.]

### Phase 3: Validation
1. Run integrity checks
2. Verify output format compliance
3. Report completion status

## Input Requirements

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| [param_1] | str  | Yes      | [Description] |
| [param_2] | int  | No       | [Description] |

## Output Specification

[LLM: Define expected output format, file paths, naming conventions.]

## Error Handling

| Error Code | Condition | Resolution |
|------------|-----------|------------|
| ERR-001    | [Condition] | [Action] |

## Constraints

- LOCK-001: [Define operational constraints]
- All file operations must use skill_files_designer
- No direct `open()`/`write_text()` for .md/.py/.json/.html

## Dependencies

- Python 3.8+
- [List other dependencies]
"""
        return "SKILL.md", content

    def generate_usage_md(self) -> Tuple[str, str]:
        """Generate scripts/USAGE.md content (human tutorial)."""
        # USAGE.md must be at scripts/USAGE.md, not root (per memory #11)
        fm = self._generate_frontmatter(
            title=f"{self.skill_name} - Script Usage Tutorial",
            description=f"Human-readable tutorial for all scripts in the {self.skill_name} skill bundle. Includes installation, configuration, and usage examples.",
            version="1.0.0",
            local_path=f"{{baseDir}}/scripts/USAGE.md",
            github_path=f"{self.skill_name}/scripts/USAGE.md",
            file_type="md"
        )
        content = f"""{fm}

# Usage Guide: {self.skill_name}

## Installation

```bash
git clone https://github.com/{self.DEFAULT_REPO_OWNER}/{self.DEFAULT_REPO_NAME}.git
cd {self.skill_name}
cp .env.example .env
# Edit .env with your credentials
```

## Environment Setup

Required environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | `ghp_xxxxxxxxxxxx` |

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `[script_name].py` | [Description] | `python [script_name].py --help` |

## Common Operations

### Operation 1: [Name]

```bash
python scripts/[script_name].py [args]
```

Expected output: [Description]

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| [Symptom] | [Cause] | [Solution] |

## Support

For issues, please create a GitHub Issue with the standard format defined in CONTRIBUTING.md.
"""
        return "scripts/USAGE.md", content

    def generate_env_example(self) -> Tuple[str, str]:
        """Generate .env.example with frontmatter."""
        # .env.example must also carry frontmatter (per memory #27)
        fm = self._generate_frontmatter(
            title=f"{self.skill_name} - Environment Configuration Template",
            description=f"Environment variable template for {self.skill_name}. Copy to .env and fill in actual values.",
            version="1.0.0",
            local_path=f"{{baseDir}}/.env.example",
            github_path=f"{self.skill_name}/.env.example",
            file_type="md"
        )
        content = f"""{fm}

# GitHub Authentication
GITHUB_TOKEN=ghp_your_personal_access_token_here

# Repository Configuration (DO NOT MODIFY - use defaults)
GITHUB_OWNER={self.DEFAULT_REPO_OWNER}
GITHUB_REPO={self.DEFAULT_REPO_NAME}
TARGET_BRANCH={self.DEFAULT_BRANCH}

# Skill-specific Configuration
# [Add skill-specific variables below]
# EXAMPLE_API_KEY=your_key_here
# EXAMPLE_ENDPOINT=https://api.example.com/v1
"""
        return ".env.example", content

    def generate_gitignore(self) -> Tuple[str, str]:
        """Generate .gitignore."""
        # .gitignore does not need frontmatter as it's not a skill identity file
        content = """# Environment files
.env
.env.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Backup files
.backups/
*.backup
*.bak

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
"""
        return ".gitignore", content

    def generate_example_script(self) -> Tuple[str, str]:
        """Generate an example Python script with docstring frontmatter."""
        script_name = f"{self.skill_name.replace('.', '_')}_example.py"
        # Use underscore naming for .py (per memory #13: .py exempt from dot rule)
        fm = self._generate_py_docstring_frontmatter(
            title=f"{self.skill_name} - Example Script",
            description=f"Example script demonstrating standard structure and frontmatter conventions for {self.skill_name}.",
            version="1.0.0",
            local_path=f"{{baseDir}}/scripts/{script_name}",
            github_path=f"{self.skill_name}/scripts/{script_name}"
        )
        content = f"""{fm}

import os
import sys
from pathlib import Path


def main():
    '''Main entry point.'''
    print(f"[{self.skill_name}] Example script executed successfully")
    # TODO: Implement actual functionality
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""
        return f"scripts/{script_name}", content

    def build_confirmation_list(self, files_to_create: List[Tuple[str, str]]) -> str:
        """Build CONFIRMATION.md style checklist."""
        lines = [
            "# CONFIRMATION CHECKLIST - Skill Folder Designer",
            f"Generated at: {self.timestamp}",
            f"Skill Name: `{self.skill_name}`",
            f"Target Directory: `{self.skill_dir}`",
            f"Mode: {'DRY-RUN (Preview Only)' if self.dry_run else 'LIVE WRITE'}",
            "",
            "## Files to Create",
            "",
            "| # | File Path | Size (chars) | Frontmatter | Status |",
            "|---|-----------|--------------|-------------|--------|",
        ]
        for i, (path, content) in enumerate(files_to_create, 1):
            has_fm = "---" in content[:500]
            lines.append(f"| {i} | `{path}` | {len(content)} | {'Yes' if has_fm else 'No'} | Pending |")
        lines.extend([
            "",
            "## Directory Structure",
            "",
            f"```",
            f"{self.skill_name}/",
        ])
        for path, _ in sorted(files_to_create):
            parts = path.split("/")
            indent = "    " * (len(parts) - 1)
            lines.append(f"{indent}├── {parts[-1]}")
        lines.extend([
            "```",
            "",
            "## Action Required",
            "",
            "1. Review the file list above",
            "2. Verify skill name and paths are correct",
            "3. If satisfied, run with `--confirm` flag to execute",
            "4. After creation, run `skill_integrity_checker.py` to validate",
            "",
            "## Warnings",
            "",
            "- [ ] Skill name confirmed by owner",
            "- [ ] GitHub repository path verified (default: ai.skills.incubation)",
            "- [ ] No existing files will be overwritten without warning",
            "- [ ] All .py files use underscore naming (exempt from dot rule)",
        ])
        return "\n".join(lines)

    def create_structure(self, description: str = "", confirm: bool = False) -> List[Tuple[str, str]]:
        """Execute folder creation. Returns list of (relative_path, content)."""
        files = []
        files.append(self.generate_readme_md(description))
        files.append(self.generate_skill_md())
        files.append(self.generate_usage_md())
        files.append(self.generate_env_example())
        files.append(self.generate_gitignore())
        files.append(self.generate_example_script())

        # Print confirmation list
        confirmation = self.build_confirmation_list(files)
        print(confirmation)
        print("\n" + "="*60)

        if self.dry_run and not confirm:
            print("[DRY-RUN] No files written. Use --confirm to execute.")
            return files

        # Write files
        for rel_path, content in files:
            full_path = self.skill_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            print(f"[CREATED] {full_path}")

        print(f"\n[SUCCESS] Skill '{self.skill_name}' initialized at {self.skill_dir}")
        print("[NEXT] Run: python skill_integrity_checker.py --skill-dir " + str(self.skill_dir))
        return files


def main():
    parser = argparse.ArgumentParser(
        description="Initialize new skill bundle with standard structure and unified frontmatter"
    )
    parser.add_argument("--skill-name", required=True, help="Name of the new skill (dot-separated)")
    parser.add_argument("--base-dir", default=".", help="Base directory for skill creation (default: current)")
    parser.add_argument("--description", default="", help="Short description of the skill")
    parser.add_argument("--confirm", action="store_true", help="Confirm and execute file creation (default: dry-run)")
    parser.add_argument("--no-dry-run", action="store_true", help="Disable dry-run mode (legacy, use --confirm)")

    args = parser.parse_args()

    dry_run = not (args.confirm or args.no_dry_run)
    designer = SkillFolderDesigner(
        skill_name=args.skill_name,
        base_dir=args.base_dir,
        dry_run=dry_run
    )

    designer.create_structure(
        description=args.description,
        confirm=(args.confirm or args.no_dry_run)
    )


if __name__ == "__main__":
    main()
