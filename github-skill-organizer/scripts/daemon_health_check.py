"""
---
title: Daemon Health Check
name: github-skill-organizer
description: Quick diagnostic tool for daemon issues. Tests file_scouter frontmatter extraction, skill_installer filename cleaning, module cache status. Run after replacing any .py file to verify daemon will use the new version. v1.2.0 updated for v1.1.1 refactor.
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
  local_path: scripts/daemon_health_check.py
  github_path: github-skill-organizer/scripts/daemon_health_check.py
---
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone


def load_scouter_module():
    for key in list(sys.modules.keys()):
        if "file_scouter" in key or "skill_installer" in key:
            del sys.modules[key]
    scripts_dir = Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))
    try:
        from file_scouter import FileScouter
        from skill_installer import SkillInstaller
        return FileScouter(), SkillInstaller()
    except ImportError as e:
        print("[FAIL] Cannot import modules: " + str(e))
        sys.exit(1)


def test_frontmatter_extraction(scouter, test_cases):
    results = []
    for name, content, expected_name in test_cases:
        tmp = Path("/tmp/health_check_" + name)
        tmp.write_text(content, encoding="utf-8")
        fm = FrontmatterExtractor.extract(tmp)
        ok = fm is not None and "name" in fm and fm.get("name") == expected_name
        results.append({
            "test": name,
            "ok": ok,
            "extracted_name": fm.get("name") if fm else None,
            "expected": expected_name,
        })
        tmp.unlink(missing_ok=True)
    return results


def test_filename_cleaning(installer, test_cases):
    results = []
    for original, expected in test_cases:
        cleaned = installer._clean_downloaded_filename(original)
        ok = cleaned == expected
        results.append({
            "original": original,
            "cleaned": cleaned,
            "expected": expected,
            "ok": ok,
        })
    return results


def check_module_cache():
    cached = []
    for name, mod in sys.modules.items():
        if "file_scouter" in name or "skill_installer" in name:
            file_path = getattr(mod, "__file__", "unknown")
            cached.append({"module": name, "file": file_path})
    return cached


def check_daemon_process():
    import subprocess
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        lines = [l for l in result.stdout.splitlines() if "scheduler_daemon" in l and "grep" not in l]
        return lines
    except Exception as e:
        return ["Error checking daemon: " + str(e)]


def main():
    print("=" * 70)
    print("DAEMON HEALTH CHECK v1.2.0")
    print("Timestamp: " + datetime.now(timezone.utc).isoformat())
    print("=" * 70)

    print("[1/5] MODULE CACHE CHECK")
    print("-" * 40)
    cached = check_module_cache()
    if cached:
        print(" Found " + str(len(cached)) + " cached modules:")
        for c in cached:
            print(" - " + c["module"] + ": " + c["file"])
        print(" WARNING: If you replaced .py files but daemon is running,")
        print(" the cached modules may be OLD versions!")
    else:
        print(" No cached modules found (good - fresh import)")

    print("[2/5] LOADING MODULES (bypass cache)")
    print("-" * 40)
    scouter, installer = load_scouter_module()
    print(" file_scouter: loaded")
    print(" skill_installer: loaded")

    print("[3/5] FRONTMATTER EXTRACTION TEST")
    print("-" * 40)
    q = chr(39)
    dq = chr(34)
    nl = chr(10)
    test_cases = [
        ("md_standard.md", "---"+nl+"title: Test"+nl+"name: test-md"+nl+"---"+nl+"content", "test-md"),
        ("py_double_quote.py", dq+dq+dq+nl+"---"+nl+"title: Test"+nl+"name: test-py-dq"+nl+"---"+nl+dq+dq+dq+nl+"content", "test-py-dq"),
        ("py_single_quote.py", q+q+q+nl+"---"+nl+"title: Test"+nl+"name: test-py-sq"+nl+"---"+nl+q+q+q+nl+"content", "test-py-sq"),
    ]

    # Need to import FrontmatterExtractor for testing
    try:
        from core_frontmatter import FrontmatterExtractor
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.absolute()))
        from core_frontmatter import FrontmatterExtractor

    fm_results = test_frontmatter_extraction(scouter, test_cases)
    all_fm_ok = True
    for r in fm_results:
        status = "PASS" if r["ok"] else "FAIL"
        print(" [" + status + "] " + r["test"] + ": extracted=" + str(r["extracted_name"]) + ", expected=" + str(r["expected"]))
        if not r["ok"]:
            all_fm_ok = False

    print("[4/5] FILENAME CLEANING TEST")
    print("-" * 40)
    filename_cases = [
        ("skill_patch_validator_v1.3.0.20260523125716.py", "skill_patch_validator_v1.3.0.py"),
        ("github_repo_sync_v0.3.3.20260523125615.py", "github_repo_sync_v0.3.3.py"),
        ("SKILL_v1.3.1.20260523125716.md", "SKILL_v1.3.1.md"),
        ("normal_file.py", "normal_file.py"),
    ]
    fn_results = test_filename_cleaning(installer, filename_cases)
    all_fn_ok = True
    for r in fn_results:
        status = "PASS" if r["ok"] else "FAIL"
        print(" [" + status + "] " + r["original"] + " -> " + chr(39) + r["cleaned"] + chr(39) + " (expected: " + chr(39) + r["expected"] + chr(39) + ")")
        if not r["ok"]:
            all_fn_ok = False

    print("[5/5] DAEMON PROCESS CHECK")
    print("-" * 40)
    daemon_lines = check_daemon_process()
    if daemon_lines:
        print(" Daemon RUNNING:")
        for line in daemon_lines:
            print(" " + line.strip())
        print(" ACTION REQUIRED: If you replaced any .py files, restart daemon:")
        print(" pkill -f scheduler_daemon")
        print(" python3 scripts/scheduler_daemon.py --start")
    else:
        print(" Daemon NOT running")

    print("")
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    issues = []
    if cached:
        issues.append("Cached old modules detected - restart daemon if you updated files")
    if not all_fm_ok:
        issues.append("Frontmatter extraction FAILED - file_scouter/core_frontmatter needs fix")
    if not all_fn_ok:
        issues.append("Filename cleaning FAILED - skill_installer needs fix")
    if issues:
        print("ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(" " + str(i) + ". " + issue)
        print("")
        print("RECOMMENDED ACTIONS:")
        print(" 1. Stop daemon: pkill -f scheduler_daemon")
        print(" 2. Verify files in skills/github-skill-organizer/scripts/")
        print(" 3. Start daemon: python3 scripts/scheduler_daemon.py --start")
        print(" 4. Re-run this health check")
        return 1
    else:
        print("ALL CHECKS PASSED")
        print("Daemon should correctly classify new files.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
