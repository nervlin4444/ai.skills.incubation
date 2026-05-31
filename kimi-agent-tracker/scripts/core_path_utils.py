"""
---
title: "Core Path Utilities"
name: "kimi-agent-tracker"
description: "Shared path resolution utilities for cross-platform skill directory management. Resolves baseDir, expands home, ensures directories exist."
version: "v5.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-26T18:15:30.038+00:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{{baseDir}}/scripts/core_path_utils.py"
  github_path: "kimi-agent-tracker/scripts/core_path_utils.py"
---
"""

import os
import sys
from pathlib import Path


def get_skill_dir() -> Path:
    # Resolve skill root from this file location: scripts/ -> parent -> skill root
    return Path(__file__).resolve().parent.parent


def resolve_path(path_tpl: str, skill_dir: Path = None) -> Path:
    # Resolve path template with baseDir placeholder and home expansion
    if skill_dir is None:
        skill_dir = get_skill_dir()
    resolved = path_tpl.replace("{baseDir}", str(skill_dir))
    if resolved.startswith("~/"):
        resolved = os.path.expanduser(resolved)
    return Path(resolved)


def ensure_dir(path_tpl: str, skill_dir: Path = None) -> Path:
    # Ensure directory exists, create if missing
    p = resolve_path(path_tpl, skill_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_config_dir(skill_dir: Path = None) -> Path:
    return ensure_dir("{baseDir}/config", skill_dir)


def get_data_dir(skill_dir: Path = None) -> Path:
    return ensure_dir("{baseDir}/data", skill_dir)


def get_logs_dir(skill_dir: Path = None) -> Path:
    return ensure_dir("{baseDir}/logs", skill_dir)


def get_download_dir(skill_dir: Path = None) -> Path:
    # Download directory is OUTSIDE skill dir to avoid frontmatter upload conflicts
    # Controlled by tracker_config, default to ~/Downloads
    dl_path = Path.home() / "Downloads"
    dl_path.mkdir(parents=True, exist_ok=True)
    return dl_path


def get_conversations_json_path(skill_dir: Path = None) -> Path:
    return get_config_dir(skill_dir) / "conversations.json"


def get_tracker_config_path(skill_dir: Path = None) -> Path:
    return get_config_dir(skill_dir) / "tracker_config.json"


def get_download_state_path(skill_dir: Path = None) -> Path:
    return get_data_dir(skill_dir) / "download_state.json"


# =============================================================================
# TEST MODULE
# =============================================================================

def _run_tests():
    passed = 0
    failed = 0

    def _t(name, condition, ok_detail="", fail_reason=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name}: {ok_detail}" if ok_detail else f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}: {fail_reason}" if fail_reason else f"  [FAIL] {name}")

    print("=" * 60)
    print("  core_path_utils.py — UNIT TESTS (AST only)")
    print("=" * 60)

    # T1: get_skill_dir
    sd = get_skill_dir()
    _t("T1 test_get_skill_dir",
       isinstance(sd, Path) and sd.is_dir() and sd.name == "kimi-agent-tracker",
       str(sd))

    # T2: resolve_path with {baseDir}
    r2 = resolve_path("{baseDir}/config")
    _t("T2 test_resolve_base_dir",
       isinstance(r2, Path) and str(r2).endswith("kimi-agent-tracker/config"),
       str(r2))

    # T3: resolve_path with ~/
    r3 = resolve_path("~/test_xyz_path")
    home = str(Path.home())
    _t("T3 test_resolve_home",
       str(r3).startswith(home) and "test_xyz_path" in str(r3),
       f"resolved={r3}, home={home}")

    # T4: ensure_dir creates directory
    import tempfile
    import shutil
    tmpdir = Path(tempfile.gettempdir()) / f"kimi_test_ensure_{int(__import__('time').time())}"
    try:
        ensure_dir(str(tmpdir))
        _t("T4 test_ensure_dir_creates",
           tmpdir.exists() and tmpdir.is_dir(),
           str(tmpdir))
    finally:
        if tmpdir.exists():
            shutil.rmtree(tmpdir, ignore_errors=True)

    # T5: get_config_dir
    cd = get_config_dir()
    _t("T5 test_get_config_dir",
       cd.name == "config" and cd.is_dir(),
       str(cd))

    # T6: get_data_dir
    dd = get_data_dir()
    _t("T6 test_get_data_dir",
       dd.name == "data" and dd.is_dir(),
       str(dd))

    # T7: get_logs_dir
    ld = get_logs_dir()
    _t("T7 test_get_logs_dir",
       ld.name == "logs" and ld.is_dir(),
       str(ld))

    # T8: get_download_dir
    dld = get_download_dir()
    _t("T8 test_get_download_dir",
       dld.name == "Downloads" and dld.is_dir(),
       str(dld))

    # T9: get_conversations_json_path
    cjp = get_conversations_json_path()
    _t("T9 test_get_conversations_json",
       cjp.name == "conversations.json" and cjp.parent.name == "config",
       str(cjp))

    # T10: get_tracker_config_path + get_download_state_path
    tcp = get_tracker_config_path()
    dsp = get_download_state_path()
    t10_ok = (
        tcp.name == "tracker_config.json"
        and tcp.parent.name == "config"
        and dsp.name == "download_state.json"
        and dsp.parent.name == "data"
    )
    _t("T10 test_tracker_config_and_state",
       t10_ok,
       f"config={tcp.name}, state={dsp.name}")

    print()
    print("=" * 60)
    print(f"  TEST RESULTS: {passed}/{passed + failed} passed, {failed} failed")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Core Path Utils v5.0.0")
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    args = parser.parse_args()

    if args.test:
        _run_tests()
        sys.exit(0)

    sd = get_skill_dir()
    print(f"skill_dir: {sd}")
    print(f"config_dir: {get_config_dir(sd)}")
    print(f"data_dir: {get_data_dir(sd)}")
    print(f"logs_dir: {get_logs_dir(sd)}")
    print(f"download_dir: {get_download_dir(sd)}")
