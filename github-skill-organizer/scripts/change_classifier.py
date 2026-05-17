"""
---
title: Change Classifier
name: github-skill-organizer
description: Determines version bump type (patch/minor/major) and approval requirements based on deterministic rules.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/change_classifier.py"
  github_path: "github-skill-organizer/scripts/change_classifier.py"
---
"""

import sys
import json
import re
from pathlib import Path

try:
    from skill_organizer_config import load_config
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from skill_organizer_config import load_config


class ChangeClassifier:
    def __init__(self):
        self.cfg = load_config()
        self.rules = self.cfg.json_config.get("version_bump_rules", {})
        self.gate = self.cfg.json_config.get("upload_gate", {})

    def classify(self, skill_name, changed_files, diff_summary=""):
        patch_rules = self.rules.get("patch", {})
        max_files = patch_rules.get("max_files", 3)
        forbidden = patch_rules.get("forbidden_patterns", [])

        file_count = len(changed_files)
        has_forbidden = any(
            any(p in str(f) for p in forbidden)
            for f in changed_files
        )

        has_hardcode = False
        if self.gate.get("check_hardcoded_paths", True):
            patterns = self.gate.get("hardcoded_path_patterns", [])
            for f in changed_files:
                if Path(f).suffix in [".py", ".md", ".json", ".yaml", ".yml"]:
                    try:
                        content = Path(f).read_text(encoding="utf-8", errors="ignore")
                        for pat in patterns:
                            if pat in content:
                                has_hardcode = True
                                break
                    except Exception:
                        pass

        if file_count <= max_files and not has_forbidden and not has_hardcode:
            bump_type = "patch"
            approval_required = not self.cfg.auto_approve_patch
            reason = "Small fix within patch limits"
        elif not has_forbidden and file_count <= 5:
            bump_type = "minor"
            approval_required = True
            reason = "Multi-file change or new feature"
        else:
            bump_type = "major"
            approval_required = True
            reason = "Large change, forbidden file touched, or hardcoded paths detected"

        current_version = self._get_current_version(skill_name)
        new_version = self._bump_version(current_version, bump_type)

        return {
            "bump_type": bump_type,
            "current_version": current_version,
            "new_version": new_version,
            "approval_required": approval_required,
            "reason": reason,
            "file_count": file_count,
            "has_forbidden": has_forbidden,
            "has_hardcode": has_hardcode,
        }

    def _get_current_version(self, skill_name):
        skill_dir = Path(self.cfg.user_skills_folder) / skill_name
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            try:
                content = skill_md.read_text(encoding="utf-8", errors="ignore")
                match = re.search(r'version:\s*[\'"]?([\d.]+)[\'"]?', content)
                if match:
                    return match.group(1)
            except Exception:
                pass
        return "1.0.0"

    def _bump_version(self, version_str, bump_type):
        parts = version_str.strip().split(".")
        while len(parts) < 3:
            parts.append("0")
        try:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            return "1.0.0"

        if bump_type == "patch":
            patch += 1
        elif bump_type == "minor":
            minor += 1
            patch = 0
        else:
            major += 1
            minor = 0
            patch = 0

        return f"{major}.{minor}.{patch}"


if __name__ == "__main__":
    classifier = ChangeClassifier()
    result = classifier.classify("test-skill", ["test.py", "README.md"])
    print(json.dumps(result, indent=2, ensure_ascii=False))
