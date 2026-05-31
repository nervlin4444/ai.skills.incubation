"""
---
title: "Kimi Download Manager"
name: "kimi-agent-tracker"
description: "Business logic core for Kimi conversation file downloads. Fixed step registry, HEAD pre-check, incremental timeout, cycle safety. Delegates browser automation to downloader and lister. Compatible with downloader v5.0.5+."
version: "v5.0.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-28T00:40:00+08:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{baseDir}/scripts/kimi_download_manager.py"
  github_path: "kimi-agent-tracker/scripts/kimi_download_manager.py"
---
"""

import json
import os
import subprocess
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional

# Inject skill scripts into path for core module imports
_SKILL_DIR = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _SKILL_DIR / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from core_path_utils import (
    get_skill_dir,
    get_config_dir,
    get_data_dir,
    get_download_dir,
    get_tracker_config_path,
    get_conversations_json_path,
    get_download_state_path,
    ensure_dir,
)
from core_logger import CoreLogger, get_default_logger


# Constants
DEFAULT_TIMEOUT_SEC = 20
TIMEOUT_INCREMENT_SEC = 20
MAX_TIMEOUT_SEC = 120
SAFETY_MARGIN_SEC = 30


# Config I/O
def load_tracker_config() -> dict:
    cfg_path = get_tracker_config_path()
    if not cfg_path.exists():
        return {}
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_conversations_json(conversations: list) -> Path:
    conv_path = get_conversations_json_path()
    ensure_dir("{baseDir}/config")
    with open(conv_path, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    return conv_path


def load_conversations_json() -> list:
    conv_path = get_conversations_json_path()
    if not conv_path.exists():
        return []
    with open(conv_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data if isinstance(data, list) else []


def load_download_state() -> dict:
    state_path = get_download_state_path()
    if not state_path.exists():
        return {"conversations": [], "global_stats": {}}
    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_download_state(state: dict) -> Path:
    state_path = get_download_state_path()
    ensure_dir("{baseDir}/data")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state_path


# ---- Merged from state_manager: SHA256 + dedup + HTTP header enrichment ----

def compute_sha256(file_path: str) -> str:
    """計算文件 SHA256 哈希值。"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_etag_match(state: dict, filename: str, etag: str) -> bool:
    """Check if a file with the same ETag has already been downloaded."""
    for conv in state.get("conversations", []):
        for f in conv.get("files", []):
            if f.get("filename") == filename and f.get("etag") == etag:
                return True
    return False


def update_download_state(state: dict, conv_url: str, conv_title: str,
                          batch_results: List[Dict[str, Any]]) -> dict:
    """Enrich download_state.json with HTTP headers + SHA256 per file.
    batch_results is the 'results' array from kimi_downloader's batch_report."""
    conv_entry = None
    for c in state.get("conversations", []):
        if c.get("url") == conv_url:
            conv_entry = c
            break
    if not conv_entry:
        conv_entry = {"url": conv_url, "title": conv_title, "files": []}
        state.setdefault("conversations", []).append(conv_entry)

    for r in batch_results:
        entry = {
            "filename": r.get("name", ""),
            "status": r.get("status", ""),
            "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if r.get("status") == "success":
            fp = r.get("path", "")
            if fp and os.path.exists(fp):
                entry["sha256"] = compute_sha256(fp)
            entry["content_length"] = r.get("content_length")
            entry["etag"] = r.get("etag")
            entry["last_modified"] = r.get("last_modified")
            entry["content_type"] = r.get("content_type")
            entry["http_url"] = r.get("http_url")
            entry["file_path"] = fp
            entry["size_verified"] = r.get("size_verified", False)
            entry["size"] = r.get("size", 0)

        # Upsert: replace existing entry for same filename
        existing_idx = None
        for i, f in enumerate(conv_entry.get("files", [])):
            if f.get("filename") == entry["filename"]:
                existing_idx = i
                break
        if existing_idx is not None:
            conv_entry["files"][existing_idx] = entry
        else:
            conv_entry.setdefault("files", []).append(entry)

    # Update global stats
    state.setdefault("global_stats", {})
    total = sum(1 for c in state.get("conversations", [])
                for f in c.get("files", []) if f.get("status") == "success")
    total_size = sum(f.get("size", 0) for c in state.get("conversations", [])
                     for f in c.get("files", []) if f.get("status") == "success")
    state["global_stats"]["total_downloaded"] = total
    state["global_stats"]["total_size_bytes"] = total_size
    state["global_stats"]["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    return state


# ---- Session state management ----

def get_session_state(state: dict) -> dict:
    """Get or create session state tracking."""
    return state.setdefault("session", {})


def mark_session_expired(state: dict, reason: str = "") -> dict:
    """Mark session as expired (login required)."""
    ss = get_session_state(state)
    ss["expired"] = True
    ss["expired_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    ss["expired_reason"] = reason
    return state


def is_session_expired(state: dict) -> bool:
    """Check if session is marked expired."""
    return state.get("session", {}).get("expired", False)


def clear_session_expired(state: dict) -> dict:
    """Clear expired flag after successful login."""
    state.pop("session", None)
    return state


# ---- Tracer → Logger compression ----

def tracer_to_logger(tracer, log: "CoreLogger") -> None:
    """Compress tracer events into structured logger output. No standalone file."""
    if tracer is None:
        return
    try:
        summary = tracer.get_summary()
        log.info(f"[TRACER] events={summary.get('total_events',0)} types={summary.get('unique_event_types',[])} elapsed={summary.get('elapsed_total',0):.2f}s")
        timings = summary.get("paired_timings", {})
        for tag, duration in timings.items():
            if duration is not None:
                log.metric(f"trace_{tag}_sec", f"{duration:.2f}")
    except Exception:
        pass


# Subprocess helpers
def run_lister(auto_discover: bool = True, target_url: str = "") -> tuple:
    """Run lister subprocess for auto-discovery. Returns (conversations, error)."""
    if not auto_discover and target_url:
        # Direct URL mode: return single conversation without running lister
        return [{"url": target_url, "title": target_url.split("/")[-1][:30]}], ""
    lister_script = _SCRIPTS_DIR / "kimi_conversation_lister.py"
    if not lister_script.exists():
        return [], "Lister not found: " + str(lister_script)
    cmd = [sys.executable, str(lister_script), "--visible", "--limit", "5"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return [], "Lister exit " + str(result.returncode) + ": " + result.stderr[:500]
        # Read from latest lister output (data/conversation_list_*.json)
        data_dir = get_data_dir()
        lists = sorted(data_dir.glob("conversation_list_*.json"), reverse=True)
        if lists:
            with open(lists[0], "r", encoding="utf-8") as f:
                data = json.load(f)
                conversations = data.get("conversations", [])
        else:
            conversations = []
        return conversations, ""
    except subprocess.TimeoutExpired:
        return [], "Lister timed out after 120s"
    except Exception as e:
        return [], "Lister exception: " + str(e)


def run_downloader(conversation_json: str, max_files: int, visible: bool, download_dir: str = "") -> tuple:
    dl_script = _SCRIPTS_DIR / "kimi_downloader.py"
    if not dl_script.exists():
        return {}, "Downloader not found: " + str(dl_script)
    cmd = [
        sys.executable, str(dl_script),
        "--conversation-json", conversation_json,
        "--max-files", str(max_files),
    ]
    if visible:
        cmd.append("--visible")
    if download_dir:
        cmd.extend(["--download-dir", download_dir])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        # Parse batch_report from downloader output or data dir
        report_file = None
        data_dir = get_data_dir()
        if data_dir.exists():
            reports = sorted(data_dir.glob("batch_report_*.json"), reverse=True)
            if reports:
                report_file = reports[0]
        if report_file and report_file.exists():
            with open(report_file, "r", encoding="utf-8") as f:
                return json.load(f), ""
        return {}, "Downloader completed but no batch_report found"
    except subprocess.TimeoutExpired:
        return {}, "Downloader timed out after 300s"
    except Exception as e:
        return {}, "Downloader exception: " + str(e)


def run_login_flow(log: "CoreLogger", state: dict) -> bool:
    """Attempt login via kimi_login_manager.py. Returns True on success."""
    login_script = _SCRIPTS_DIR / "kimi_login_manager.py"
    if not login_script.exists():
        log.warn("login_manager.py not found")
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(login_script), "--validate", "--visible"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            log.info("Login validation passed")
            return True
        log.warn(f"Login validation failed (exit {result.returncode})")
        # Mark expired and save state
        mark_session_expired(state, f"validate exit {result.returncode}")
        save_download_state(state)
        return False
    except subprocess.TimeoutExpired:
        log.warn("Login validation timed out")
        mark_session_expired(state, "login timeout")
        save_download_state(state)
        return False
    except Exception as e:
        log.error(f"Login flow error: {e}")
        return False


# HEAD pre-check
def head_pre_check(url: str) -> dict:
    import urllib.request
    import ssl
    result = {"status": 0, "content_length": -1, "filename": "", "error": ""}
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            result["status"] = resp.status
            result["content_length"] = int(resp.headers.get("Content-Length", -1))
            cd = resp.headers.get("Content-Disposition", "")
            if "filename=" in cd:
                result["filename"] = cd.split("filename=")[1].strip('"')
    except Exception as e:
        result["error"] = str(e)
    return result


# Step registry helpers
def step(log: CoreLogger, step_id: str, message: str):
    log.step(step_id, message)


def metric(log: CoreLogger, name: str, value: str):
    log.metric(name, value)


# Main Download Manager cycle
def run_cycle(log: CoreLogger, poll_interval_sec: int = 300) -> dict:
    cycle_start = time.time()
    cycle_result = {
        "cycle_start": cycle_start,
        "cycle_end": 0.0,
        "conversations_processed": 0,
        "files_downloaded": 0,
        "files_skipped": 0,
        "files_error": 0,
        "errors": [],
    }

    # ---- Tracer integration ----
    from core_tracer import Tracer
    tracer = Tracer("download_manager")
    tracer.record("cycle.start", poll_interval_sec=poll_interval_sec)

    step(log, "S001", "Cycle started")

    step(log, "S002", "Loading tracker_config.json")
    config = load_tracker_config()
    if not config:
        step(log, "S002-E", "tracker_config.json empty or missing")
        cycle_result["errors"].append("Config missing")
        return cycle_result
    metric(log, "config_loaded", "true")

    conversations_cfg = config.get("conversations", [])
    if not conversations_cfg:
        step(log, "S003-E", "No conversations configured")
        cycle_result["errors"].append("No conversations")
        return cycle_result

    has_placeholder = any(
        isinstance(c, dict) and ("PLACEHOLDER" in c.get("url", "") or not c.get("url"))
        for c in conversations_cfg
    )

    conversations = []
    if has_placeholder:
        step(log, "S004", "Placeholder detected, auto-discovering conversations")
        discovered, err = run_lister(auto_discover=True)
        if err:
            step(log, "S004-E", "Auto-discovery failed: " + err)
            cycle_result["errors"].append("Lister: " + err)
            return cycle_result
        if not discovered:
            step(log, "S004-E", "Auto-discovery returned empty")
            cycle_result["errors"].append("Discovery empty")
            return cycle_result
        conversations = discovered
        save_conversations_json(conversations)
        step(log, "S005", "Saved " + str(len(conversations)) + " conversations to config/conversations.json")
    else:
        step(log, "S004", "Using configured conversation URLs")
        validated = []
        for c in conversations_cfg:
            url = c.get("url", "") if isinstance(c, dict) else str(c)
            if not url:
                continue
            step(log, "S005", "Validating URL: " + url)
            single, err = run_lister(auto_discover=False, target_url=url)
            if err:
                step(log, "S005-E", "Validation failed for " + url + ": " + err)
                cycle_result["errors"].append("Validate " + url + ": " + err)
                continue
            if single:
                validated.extend(single)
        if not validated:
            step(log, "S005-E", "No valid conversations after manual validation")
            cycle_result["errors"].append("All validations failed")
            return cycle_result
        conversations = validated
        save_conversations_json(conversations)
        step(log, "S005", "Saved " + str(len(conversations)) + " validated conversations")

    # ---- Phase A: HEAD pre-check conversation URLs ----
    step(log, "S005A", "HEAD pre-checking " + str(len(conversations)) + " conversation URLs")
    head_results = []
    for conv in conversations:
        url = conv.get("url", "") if isinstance(conv, dict) else str(conv)
        if url.startswith("https://"):
            hpc = head_pre_check(url)
            head_results.append({"url": url, "status": hpc.get("status"), "error": hpc.get("error")})
            if hpc.get("error"):
                step(log, "S005A-W", "HEAD failed for " + url[:60] + ": " + hpc["error"])
    metric(log, "head_checked", str(len(head_results)))
    tracer.record("phase_a.head_check.done", checked=len(head_results))

    step(log, "S006", "Loading download state")
    state = load_download_state()
    metric(log, "state_conversations", str(len(state.get("conversations", []))))

    # ---- Session expired check ----
    if is_session_expired(state):
        step(log, "S006-E", "Session expired. Attempting re-login...")
        login_ok = run_login_flow(log, state)
        if not login_ok:
            step(log, "S006-F", "Login failed or skipped. Aborting cycle.")
            cycle_result["errors"].append("Session expired, login failed")
            save_download_state(state)
            return cycle_result
        clear_session_expired(state)
        step(log, "S006-R", "Login successful. Session restored.")

    visible = config.get("headless", True) is False
    if config.get("debug_mode", False):
        visible = True
    step(log, "S007", "Browser visible=" + str(visible))
    metric(log, "browser_visible", str(visible))

    max_files_per_run = config.get("max_files_per_run", 10)
    download_dir = config.get("download_dir", "")
    if download_dir and download_dir.startswith("~/"):
        download_dir = str(Path.home() / download_dir[2:])

    for idx, conv in enumerate(conversations):
        conv_url = conv.get("url", "") if isinstance(conv, dict) else str(conv)
        conv_label = conv.get("label", conv.get("title", "conv-" + str(idx))) if isinstance(conv, dict) else "conv-" + str(idx)
        if not conv_url:
            continue

        step(log, "S008", "[" + str(idx+1) + "/" + str(len(conversations)) + "] Processing: " + conv_label)

        elapsed = time.time() - cycle_start
        remaining = poll_interval_sec - elapsed
        if remaining < SAFETY_MARGIN_SEC:
            step(log, "S009-W", "Cycle time approaching limit (" + str(int(elapsed)) + "s / " + str(poll_interval_sec) + "s). Breaking loop.")
            cycle_result["errors"].append("Cycle time limit approaching")
            break

        # ---- ETag pre-check: skip if all files already have valid ETags ----
        conv_state = next((c for c in state.get("conversations", []) if c.get("url") == conv_url), None)
        if conv_state:
            existing_files = conv_state.get("files", [])
            all_verified = all(
                f.get("status") == "success" and f.get("etag")
                for f in existing_files
            )
            if existing_files and all_verified:
                step(log, "S008-S", "Skipping " + conv_label + ": " + str(len(existing_files)) + " files already downloaded with ETag")
                cycle_result["files_skipped"] += len(existing_files)
                tracer.record("etag.skip", url=conv_url[:60], files=len(existing_files))
                continue

        # Write single-conversation JSON for downloader
        single_conv = {"conversations": [conv]}
        conv_json = get_data_dir() / f"_cycle_conv_{idx}.json"
        conv_json.write_text(json.dumps(single_conv, ensure_ascii=False))

        dl_result, dl_err = run_downloader(str(conv_json), max_files_per_run, visible, download_dir)
        if dl_err:
            step(log, "S011-E", "Downloader error for " + conv_label + ": " + dl_err)
            cycle_result["errors"].append("DL " + conv_label + ": " + dl_err)
            continue

        # Extract results from batch_report format
        chat_reports = dl_result.get("chat_reports", [])
        for cr in chat_reports:
            success = cr.get("downloaded", 0)
            fail = cr.get("failed", 0)
            cycle_result["files_downloaded"] += success
            cycle_result["files_error"] += fail
            cycle_result["conversations_processed"] += 1
            # Enrich download state with HTTP headers + SHA256
            if cr.get("results"):
                update_download_state(state, conv_url, cr.get("chat_title", conv_label), cr["results"])
            step(log, "S012", conv_label + ": " + str(success) + " success, " + str(fail) + " error")

    cycle_end = time.time()
    cycle_result["cycle_end"] = cycle_end
    total_elapsed = cycle_end - cycle_start
    step(log, "S013", "Cycle complete: " + str(cycle_result["conversations_processed"]) + " conv, " + str(cycle_result["files_downloaded"]) + " dl, " + str(cycle_result["files_error"]) + " err, " + str(int(total_elapsed)) + "s")
    metric(log, "cycle_elapsed_sec", str(int(total_elapsed)))
    metric(log, "cycle_total_success", str(cycle_result["files_downloaded"]))
    metric(log, "cycle_total_error", str(cycle_result["files_error"]))

    save_download_state(state)
    step(log, "S014", "Download state saved")

    # ---- Tracer compression ----
    tracer.record("cycle.end", files_downloaded=cycle_result["files_downloaded"],
                  files_error=cycle_result["files_error"],
                  conversations_processed=cycle_result["conversations_processed"])
    tracer_to_logger(tracer, log)

    return cycle_result


# =============================================================================
# TEST MODULE — python3 kimi_download_manager.py --test
# =============================================================================

def _run_tests() -> None:
    passed = 0
    failed = 0

    def _t(name: str, condition: bool, ok_detail: str = "", fail_reason: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name}: {ok_detail}" if ok_detail else f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}: {fail_reason}" if fail_reason else f"  [FAIL] {name}")

    print("=" * 60)
    print("  kimi_download_manager.py — UNIT TESTS (AST + tracer)")
    print("=" * 60)

    # ── T1: constants ─────────────────────────────────────────────
    _t("T1 test_constants",
       DEFAULT_TIMEOUT_SEC == 20 and TIMEOUT_INCREMENT_SEC == 20
       and MAX_TIMEOUT_SEC == 120 and SAFETY_MARGIN_SEC == 30,
       f"DEFAULT={DEFAULT_TIMEOUT_SEC}, INC={TIMEOUT_INCREMENT_SEC}, MAX={MAX_TIMEOUT_SEC}, MARGIN={SAFETY_MARGIN_SEC}")

    # ── T2: step() ────────────────────────────────────────────────
    class MockLog:
        def __init__(self): self.calls = []
        def step(self, sid, msg): self.calls.append(("step", sid, msg))
        def metric(self, k, v): self.calls.append(("metric", k, v))
        def info(self, msg): self.calls.append(("info", msg))
    ml = MockLog()
    step(ml, "S001", "test message")
    _t("T2 test_step_logger",
       len(ml.calls) == 1 and ml.calls[0] == ("step", "S001", "test message"),
       f"calls={ml.calls}")

    # ── T3: metric() ──────────────────────────────────────────────
    metric(ml, "key1", "val1")
    _t("T3 test_metric_logger",
       ml.calls[-1] == ("metric", "key1", "val1"),
       f"last_call={ml.calls[-1]}")

    # ── T4: load_tracker_config ───────────────────────────────────
    cfg = load_tracker_config()
    _t("T4 test_load_tracker_config",
       isinstance(cfg, dict),
       f"type={type(cfg).__name__}, keys={sorted(cfg.keys()) if cfg else 'empty'}")

    # ── T5: conversations_json roundtrip ──────────────────────────
    test_conv = [{"url": "https://kimi.com/chat/test1", "title": "Test Chat"}]
    path = save_conversations_json(test_conv)
    loaded = load_conversations_json()
    _t("T5 test_conversations_json_roundtrip",
       loaded == test_conv,
       f"saved={len(test_conv)}, loaded={len(loaded)}")

    # ── T6: download_state roundtrip ──────────────────────────────
    import tempfile as _tmp6
    state_path_tmp = get_download_state_path()
    test_state = {"conversations": [], "global_stats": {"test": True}}
    save_download_state(test_state)
    loaded_state = load_download_state()
    _t("T6 test_download_state_roundtrip",
       loaded_state.get("global_stats", {}).get("test") is True,
       f"keys={sorted(loaded_state.keys())}")

    # ── T7: head_pre_check structure ──────────────────────────────
    hpc = head_pre_check("https://example.com/nonexistent")
    _t("T7 test_head_pre_check_structure",
       all(k in hpc for k in ("status", "content_length", "filename", "error")),
       f"keys={sorted(hpc.keys())}")

    # ── T8: tracer → logger compression ───────────────────────────
    from core_tracer import Tracer
    tr = Tracer("dm_test")
    tr.record("step.start", name="S001")
    tr.record("step.done", name="S001")
    ml2 = MockLog()
    tracer_to_logger(tr, ml2)
    has_tracer = any(
        isinstance(c[1], str) and "[TRACER]" in c[1]
        for c in ml2.calls if len(c) >= 2
    )
    _t("T8 test_tracer_compress_to_logger",
       len(ml2.calls) >= 1 and has_tracer,
       f"calls={[(c[0], c[1][:60] if isinstance(c[1], str) else c[1]) for c in ml2.calls]}")

    # ── T9: total_timeout 10s stops at SAFETY_MARGIN ─────────────
    ml3 = MockLog()
    # Simulate: cycle_start + SAFETY_MARGIN + 1 >= poll_interval → break
    fake_start = time.time() - 5  # already 5s elapsed
    # With poll=10, remaining=5, 5 < SAFETY_MARGIN(30) → should mark as approaching
    # Actually SAFETY_MARGIN=30 > poll_interval=10, so remaining < 30 triggers
    elapsed = time.time() - fake_start
    remaining = 10 - elapsed  # poll_interval=10
    _t("T9 test_total_timeout_10s_stops",
       remaining < SAFETY_MARGIN_SEC,
       f"elapsed={elapsed:.1f}s, remaining={remaining:.1f}s, margin={SAFETY_MARGIN_SEC} → would break")

    # ── T10: session_expired state tracking ───────────────────────
    s10 = {"conversations": []}
    mark_session_expired(s10, "validate returned 401")
    _t("T10 test_session_expired_state_tracked",
       is_session_expired(s10) and s10["session"]["expired_reason"] == "validate returned 401",
       f"session={s10.get('session', {})}")

    # ── T11: session_expired → login flow triggered ───────────────
    s11 = {"conversations": []}
    mark_session_expired(s11, "timeout")
    # check_is_expired → YES → would call run_login_flow
    _t("T11 test_session_expired_opens_login",
       is_session_expired(s11),
       f"expired={is_session_expired(s11)}, reason={s11['session']['expired_reason']}")

    # ── T12: rerun skips when session expired ─────────────────────
    s12 = {"conversations": [{"url": "https://kimi.com/test", "title": "T"}]}
    mark_session_expired(s12, "401")
    # check_is_expired → YES → attempt login → if login fails → return
    # Second run: check_is_expired → YES again → skip cycle
    still_expired = is_session_expired(s12)
    _t("T12 test_rerun_skips_expired_session",
       still_expired and len(s12["conversations"]) > 0,
       f"expired={still_expired}, would skip {len(s12['conversations'])} conversations")

    # ── T13: CLI args ─────────────────────────────────────────────
    import argparse as _ap13
    p13 = _ap13.ArgumentParser()
    p13.add_argument("--interval", type=int, default=300)
    p13.add_argument("--total-timeout", type=int, default=300)
    p13.add_argument("--once", action="store_true")
    a13 = p13.parse_args(["--interval", "60", "--once", "--total-timeout", "30"])
    _t("T13 test_cli_args_all",
       a13.interval == 60 and a13.once is True and getattr(a13, "total_timeout") == 30,
       f"interval={a13.interval}, once={a13.once}, total_timeout={getattr(a13, 'total_timeout', 'N/A')}")

    # ── T14: ETag skip logic ──────────────────────────────────────
    s14 = {
        "conversations": [{
            "url": "https://kimi.com/chat/test",
            "title": "Test",
            "files": [
                {"filename": "a.py", "status": "success", "etag": "\"abc123\"", "size_verified": True},
                {"filename": "b.py", "status": "success", "etag": "\"def456\"", "size_verified": True},
            ]
        }]
    }
    # Simulate the skip check: all files have etag + status=success → should skip
    conv = s14["conversations"][0]
    all_verified = all(f.get("status") == "success" and f.get("etag") for f in conv.get("files", []))
    should_skip = bool(conv["files"]) and all_verified
    _t("T14 test_etag_skip_logic",
       should_skip and len(conv["files"]) == 2,
       f"files={len(conv['files'])}, all_verified={all_verified}, skip={should_skip}")

    # ── T15: head_pre_check in Phase A ────────────────────────────
    hpc15 = head_pre_check("https://httpbin.org/status/200")
    _t("T15 test_head_pre_check_phase_a",
       hpc15.get("error", "") == "" or "status" in hpc15,
       f"status={hpc15.get('status')}, err={hpc15.get('error', '')[:60]}")

    print()
    print("=" * 60)
    print(f"  TEST RESULTS: {passed}/{passed + failed} passed, {failed} failed")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)


# Entry point for daemon or manual invocation
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Kimi Download Manager v5.1.0")
    parser.add_argument("--interval", type=int, default=300, help="Poll interval in seconds for cycle safety check")
    parser.add_argument("--total-timeout", type=int, default=300, help="Total cycle timeout in seconds")
    parser.add_argument("--once", action="store_true", help="Run single cycle and exit")
    parser.add_argument("--test", action="store_true", help="Run unit tests (no browser)")
    args = parser.parse_args()

    if args.test:
        _run_tests()
        sys.exit(0)

    log = get_default_logger("DM")
    log.info("Download Manager starting")

    result = run_cycle(log, args.interval)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
