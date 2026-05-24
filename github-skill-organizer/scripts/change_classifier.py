"""
---
title: Change Classifier
name: github-skill-organizer
description: Determines version bump type (patch/minor/major) and approval requirements based on deterministic rules. v1.0.1 adds classify_change() wrapper for backward compatibility (Issue #16).
version: 1.0.1
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-23T13:45:00+08:00
fixes: [16]
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: scripts/change_classifier.py
  github_path: github-skill-organizer/scripts/change_classifier.py
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


def classify_change(comparison):
    """
    Wrapper function for backward compatibility (Issue #16).
    Extracts parameters from comparison dict and calls ChangeClassifier.classify().
    Merges result with original comparison to preserve all fields.

    Args:
        comparison: dict returned by compare_skill()

    Returns:
        dict: merged comparison + classification fields
    """
    local_dir = comparison.get("local_dir", "")
    skill_name = Path(local_dir).name if local_dir else "unknown-skill"

    changed_files = (
        comparison.get("modified_files", [])
        + comparison.get("local_only_files", [])
    )

    diff_summary = (
        f"action={comparison.get('action', 'unknown')}, "
        f"modified={comparison.get('modified_count', 0)}, "
        f"local_only={comparison.get('local_only_count', 0)}"
    )

    classifier = ChangeClassifier()
    classification = classifier.classify(skill_name, changed_files, diff_summary)

    # Merge: original comparison fields + new classification fields
    # Classification fields take precedence on overlap
    return {**comparison, **classification}


if __name__ == "__main__":
    # Test 1: direct classify()
    classifier = ChangeClassifier()
    result = classifier.classify("test-skill", ["test.py", "README.md"])
    print("=== classify() ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Test 2: wrapper classify_change()
    comparison = {
        "status": "ok",
        "action": "local_ahead",
        "local_dir": "/tmp/test-skill",
        "modified_files": ["test.py"],
        "local_only_files": ["README.md"],
        "modified_count": 1,
        "local_only_count": 1,
    }
    result2 = classify_change(comparison)
    print("\n=== classify_change() ===")
    print(json.dumps(result2, indent=2, ensure_ascii=False))
