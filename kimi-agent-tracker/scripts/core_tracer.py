"""
---
title: "Core Tracer"
name: "kimi-agent-tracker"
description: "Lightweight event tracer for Kimi agent operations. Records UI events, computes paired timings, exports JSON summaries, and merges trace_minifier.py DOM extraction for backward compatibility."
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-31T12:00:00Z"
auth_config:
  provider: "none"
  auth_method: "none"
  token_env_var: "NONE"
  env_file_path: "none"
file_mapping:
  local_path: "{baseDir}/scripts/core_tracer.py"
  github_path: "kimi-agent-tracker/scripts/core_tracer.py"
---
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tempfile
import shutil
import zipfile
from pathlib import Path
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Set, Union, Callable
from datetime import datetime


# =============================================================================
# Tracer — lightweight event recorder
# =============================================================================

class Tracer:
    """Records timestamped events with arbitrary data for agent operations.

    Supports:
      - record(event, **data): append an event
      - get_summary(): aggregate statistics
      - get_timing(tag): compute elapsed between {tag}.start and {tag}.done
      - export_json(path): dump all events to JSON
      - clear(): reset internal state

    Safe to use with None (no-op), callable proxies, and exception-throwing
    backends — _trace() wrappers should handle all edge cases silently.
    """

    def __init__(self, name: str = "tracer") -> None:
        self._name = name
        self._events: List[Dict[str, Any]] = []
        self._start_time = time.time()

    # ── record ────────────────────────────────────────────────────
    def record(self, event: str, **data: Any) -> None:
        """Append a timestamped event with arbitrary keyword data."""
        self._events.append({
            "event": event,
            "timestamp": time.time(),
            "data": data,
        })

    # ── get_summary ────────────────────────────────────────────────
    def get_summary(self) -> Dict[str, Any]:
        """Return aggregate statistics from all recorded events."""
        event_types: Set[str] = set()
        for e in self._events:
            event_types.add(e["event"])

        paired_tags: Set[str] = set()
        for e in self._events:
            evt = e["event"]
            if evt.endswith(".start") or evt.endswith(".done"):
                tag = evt.rsplit(".", 1)[0]
                paired_tags.add(tag)

        timings: Dict[str, Optional[float]] = {}
        for tag in sorted(paired_tags):
            timings[tag] = self.get_timing(tag)

        return {
            "name": self._name,
            "total_events": len(self._events),
            "unique_event_types": sorted(event_types),
            "elapsed_total": time.time() - self._start_time,
            "paired_timings": timings,
        }

    # ── get_timing ─────────────────────────────────────────────────
    def get_timing(self, tag: str) -> Optional[float]:
        """Return elapsed seconds between {tag}.start and {tag}.done.

        Returns None if either event is missing.
        """
        start_ts: Optional[float] = None
        done_ts: Optional[float] = None
        for e in self._events:
            if e["event"] == f"{tag}.start":
                start_ts = e["timestamp"]
            elif e["event"] == f"{tag}.done":
                done_ts = e["timestamp"]
        if start_ts is not None and done_ts is not None:
            return done_ts - start_ts
        return None

    # ── export_json ────────────────────────────────────────────────
    def export_json(self, path: Path) -> Path:
        """Dump all events to a JSON file. Returns the output path."""
        payload = {
            "generated_at": datetime.now().isoformat(),
            "generator": "core_tracer.py",
            "version": "1.0.0",
            "name": self._name,
            "summary": self.get_summary(),
            "events": self._events,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    # ── clear ──────────────────────────────────────────────────────
    def clear(self) -> None:
        """Reset internal event list and start time."""
        self._events.clear()
        self._start_time = time.time()


# =============================================================================
# DOMSummaryExtractor — kept from trace_minifier.py for backward compat
# =============================================================================

class DOMSummaryExtractor(HTMLParser):
    """Extracts lightweight DOM summary from Playwright snapshot HTML."""

    def __init__(self, max_elements: int = 400) -> None:
        super().__init__()
        self.max_elements = max_elements
        self.stack: List[str] = []
        self.elements: List[Dict[str, Any]] = []
        self.all_classes: Set[str] = set()
        self.all_ids: Set[str] = set()
        self.in_skip = 0

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        if tag in ("script", "style", "noscript", "iframe"):
            self.in_skip += 1
            return

        if len(self.elements) >= self.max_elements:
            self.stack.append(tag)
            return

        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "")
        id_val = attrs_dict.get("id", "")
        href = attrs_dict.get("href", "")

        if classes:
            for c in classes.split():
                c = c.strip()
                if c:
                    self.all_classes.add(c)
        if id_val:
            self.all_ids.add(id_val.strip())

        meaningful = (
            id_val
            or classes
            or href
            or tag in (
                "a", "button", "input", "nav", "aside", "main",
                "header", "section", "article", "li", "ul", "ol",
            )
        )

        if meaningful:
            el: Dict[str, Any] = {
                "tag": tag,
                "depth": len(self.stack),
                "id": id_val[:60] if id_val else None,
                "classes": classes[:100] if classes else None,
                "href": href[:200] if href else None,
            }
            self.elements.append(el)

        self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        if tag in ("script", "style", "noscript", "iframe"):
            self.in_skip -= 1

    def handle_data(self, data: str) -> None:
        if self.in_skip > 0 or not self.elements:
            return
        text = data.strip()
        if text and len(text) < 120:
            last = self.elements[-1]
            if "text_preview" not in last:
                last["text_preview"] = text[:80]


# =============================================================================
# Trace Event Parser
# =============================================================================

def parse_trace_events(trace_file: Path) -> Dict[str, Any]:
    """Parse trace.trace JSON lines and extract key events."""
    actions: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    network_calls: List[Dict[str, Any]] = []
    page_info: Dict[str, Any] = {}

    total_lines = 0
    with open(trace_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total_lines += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = event.get("type", "")

            if etype == "context-options":
                page_info["viewport"] = (
                    event.get("options", {}).get("viewport", {})
                )

            elif etype == "frame-attached" and not event.get("parentFrameId"):
                page_info["url"] = event.get("url", "")
                page_info["title"] = event.get("title", "")

            elif etype == "action":
                params = event.get("params", {})
                actions.append({
                    "action": event.get("action", ""),
                    "params": {
                        k: v for k, v in params.items()
                        if k in ("url", "selector", "key", "text", "value")
                    },
                })

            elif etype == "event":
                method = event.get("method", "")
                if "error" in method.lower() or "exception" in method.lower():
                    errors.append({
                        "class": event.get("class", ""),
                        "method": method,
                        "params": event.get("params", {}),
                    })

            elif etype == "resource":
                url = event.get("url", "")
                if "kimi" in url or "moonshot" in url:
                    network_calls.append({
                        "url": url[:200],
                        "method": event.get("method", "GET"),
                        "status": event.get("responseStatus"),
                        "type": event.get("type", ""),
                    })

    return {
        "page_info": page_info,
        "actions_sample": actions[-20:],
        "errors": errors,
        "network_calls_sample": network_calls[-30:],
        "total_trace_lines": total_lines,
    }


# =============================================================================
# Snapshot Analyzer
# =============================================================================

def analyze_snapshots(resources_dir: Path) -> Dict[str, Any]:
    """Analyze all snapshot HTMLs in resources directory."""
    html_files = list(resources_dir.glob("*.html"))
    if not html_files:
        return {"error": "No snapshot HTML files found in resources/"}

    latest = max(html_files, key=lambda p: p.stat().st_size)

    with open(latest, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    extractor = DOMSummaryExtractor(max_elements=300)
    extractor.feed(html)

    keywords = [
        "chat", "conversation", "history", "talk", "session",
        "dialog", "message", "list", "item", "nav", "side",
    ]
    conv_elements = [
        el for el in extractor.elements
        if any(
            k in (
                (el.get("classes") or "")
                + " "
                + (el.get("id") or "")
            ).lower()
            for k in keywords
        )
    ]

    chat_links = [
        el for el in extractor.elements
        if el.get("tag") == "a"
        and el.get("href")
        and "/chat/" in el.get("href", "")
    ]

    return {
        "snapshot_file": latest.name,
        "snapshot_size_kb": round(latest.stat().st_size / 1024, 1),
        "total_elements_extracted": len(extractor.elements),
        "all_classes_sample": sorted(extractor.all_classes)[:100],
        "all_ids_sample": sorted(extractor.all_ids)[:50],
        "conversation_related_elements": conv_elements[:30],
        "chat_links": chat_links[:20],
    }


# =============================================================================
# Minify trace (backward-compatible entry point)
# =============================================================================

def minify_trace(trace_zip: Path, output: Optional[Path] = None) -> Dict[str, Any]:
    """Extract and minify a Playwright trace.zip into a structural summary.

    Args:
        trace_zip: Path to trace.zip file.
        output: Optional output JSON path. Defaults to trace_summary.json in cwd.

    Returns:
        Dict with page_info, actions, errors, network_calls, dom_summary.
    """
    trace_dir = Path(tempfile.mkdtemp(prefix="trace_"))
    try:
        with zipfile.ZipFile(trace_zip, "r") as zf:
            zf.extractall(trace_dir)

        trace_file = trace_dir / "trace.trace"
        resources_dir = trace_dir / "resources"

        if not trace_file.exists():
            return {"error": f"trace.trace not found in extracted {trace_dir}"}

        events_summary = parse_trace_events(trace_file)
        dom_summary = (
            analyze_snapshots(resources_dir)
            if resources_dir.exists()
            else {"error": "No resources directory"}
        )

        result: Dict[str, Any] = {
            "generated_at": datetime.now().isoformat(),
            "generator": "core_tracer.py (minify_trace)",
            "version": "1.0.0",
            "trace_source": str(trace_zip),
            "events_summary": events_summary,
            "dom_summary": dom_summary,
        }

        out_path = output or Path("trace_summary.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result
    finally:
        shutil.rmtree(trace_dir, ignore_errors=True)


# =============================================================================
# CLI main (backward compat with trace_minifier.py)
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Core Tracer v1.0.0 (includes trace_minifier v5.0.0 compat)"
    )
    parser.add_argument(
        "--trace-dir",
        type=str,
        default=None,
        help="Path to unzipped trace/ directory",
    )
    parser.add_argument(
        "--trace-zip",
        type=str,
        default=None,
        help="Path to trace.zip (will be auto-extracted)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="trace_summary.json",
        help="Output JSON filename",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run unit tests (no browser required)",
    )

    args = parser.parse_args()

    if args.test:
        _run_tests()
        return

    if not args.trace_dir and not args.trace_zip:
        print("[ERROR] Provide --trace-dir or --trace-zip")
        sys.exit(1)

    trace_dir: Optional[Path] = None
    cleanup = False

    if args.trace_zip:
        zip_path = Path(args.trace_zip)
        trace_dir = Path(tempfile.mkdtemp(prefix="trace_"))
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(trace_dir)
        print(f"[EXTRACT] Unzipped to: {trace_dir}")
        cleanup = True
    else:
        trace_dir = Path(args.trace_dir)

    trace_file = trace_dir / "trace.trace"
    resources_dir = trace_dir / "resources"

    if not trace_file.exists():
        print(f"[ERROR] trace.trace not found in {trace_dir}")
        sys.exit(1)

    original_kb = trace_file.stat().st_size / 1024
    print(f"[PARSE] Processing {original_kb:.0f} KB trace file...")

    events_summary = parse_trace_events(trace_file)
    dom_summary = (
        analyze_snapshots(resources_dir)
        if resources_dir.exists()
        else {"error": "No resources directory"}
    )

    result = {
        "generated_at": datetime.now().isoformat(),
        "generator": "core_tracer.py",
        "version": "1.0.0",
        "trace_source": str(trace_dir),
        "events_summary": events_summary,
        "dom_summary": dom_summary,
    }

    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    summary_kb = output_path.stat().st_size / 1024
    ratio = original_kb / summary_kb if summary_kb > 0 else 0

    print(f"[DONE] Summary: {output_path} ({summary_kb:.1f} KB)")
    print(f"[INFO] Compressed {original_kb:.0f} KB -> {summary_kb:.1f} KB ({ratio:.0f}x)")
    print(f"[HINT] Upload {output_path} to AI for selector analysis")

    if cleanup and trace_dir:
        shutil.rmtree(trace_dir, ignore_errors=True)


# =============================================================================
# TEST MODULE — python3 core_tracer.py --test
# =============================================================================

def _ok(name: str, detail: str = "") -> None:
    if detail:
        print(f"  [PASS] {name}: {detail}")
    else:
        print(f"  [PASS] {name}")


def _fail(name: str, reason: str) -> None:
    print(f"  [FAIL] {name}: {reason}")


def _run_tests() -> None:
    failed = 0
    passed = 0

    def _t(name: str, condition: bool, ok_detail: str = "", fail_reason: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            _ok(name, ok_detail)
        else:
            failed += 1
            _fail(name, fail_reason)

    print("=" * 60)
    print("  core_tracer.py — UNIT TESTS (AST only, no browser)")
    print("=" * 60)

    # ── T1: test_record_stores_event ───────────────────────────────
    t1 = Tracer("t1")
    t1.record("navigate.start", url="https://kimi.com/chat/history")
    _t("T1 test_record_stores_event",
       len(t1._events) == 1 and "timestamp" in t1._events[0],
       f"event={t1._events[0]['event']}, has_timestamp={'timestamp' in t1._events[0]}")

    # ── T2: test_record_preserves_data ─────────────────────────────
    t2 = Tracer("t2")
    t2.record("click", selector="a.chat-link", count=3)
    data = t2._events[0]["data"]
    _t("T2 test_record_preserves_data",
       data == {"selector": "a.chat-link", "count": 3},
       f"data={json.dumps(data)}")

    # ── T3: test_get_summary_structure ─────────────────────────────
    t3 = Tracer("t3")
    t3.record("scroll.done")
    t3.record("extract.done", count=5)
    t3.record("scroll.done")
    summary = t3.get_summary()
    has_fields = all(
        k in summary
        for k in ("name", "total_events", "unique_event_types", "elapsed_total", "paired_timings")
    )
    _t("T3 test_get_summary_structure",
       has_fields and summary["total_events"] == 3,
       json.dumps(summary, ensure_ascii=False))

    # ── T4: test_get_timing_paired ─────────────────────────────────
    t4 = Tracer("t4")
    t4.record("lister.scroll.start")
    time.sleep(0.05)
    t4.record("lister.scroll.done")
    timing = t4.get_timing("lister.scroll")
    _t("T4 test_get_timing_paired",
       timing is not None and timing > 0,
       f"paired timing={timing:.4f}s")

    # ── T5: test_get_timing_unpaired ───────────────────────────────
    t5 = Tracer("t5")
    t5.record("lister.scroll.start")
    timing5 = t5.get_timing("lister.scroll")
    _t("T5 test_get_timing_unpaired",
       timing5 is None,
       f"unpaired timing=None ✓")

    # ── T6: test_export_json_valid ─────────────────────────────────
    t6 = Tracer("t6")
    t6.record("test.begin")
    t6.record("test.end")
    out6 = Path(tempfile.gettempdir()) / "core_tracer_test_t6.json"
    t6.export_json(out6)
    with open(out6, "r", encoding="utf-8") as f:
        exported = json.load(f)
    _t("T6 test_export_json_valid",
       exported.get("name") == "t6" and len(exported.get("events", [])) == 2,
       f"name={exported.get('name')}, events={len(exported.get('events', []))}")
    out6.unlink(missing_ok=True)

    # ── T7: test_export_json_roundtrip ─────────────────────────────
    t7 = Tracer("t7")
    t7.record("event.one", a=1)
    t7.record("event.two", b=2, c="hello")
    out7 = Path(tempfile.gettempdir()) / "core_tracer_test_t7.json"
    t7.export_json(out7)
    with open(out7, "r", encoding="utf-8") as f:
        rt = json.load(f)
    rt_events = rt.get("events", [])
    rt_ok = (
        len(rt_events) == 2
        and rt_events[0]["event"] == "event.one"
        and rt_events[0]["data"] == {"a": 1}
        and rt_events[1]["event"] == "event.two"
        and rt_events[1]["data"] == {"b": 2, "c": "hello"}
    )
    _t("T7 test_export_json_roundtrip",
       rt_ok,
       f"events={json.dumps(rt_events, ensure_ascii=False)}")
    out7.unlink(missing_ok=True)

    # ── T8: test_dom_extractor_elements ────────────────────────────
    ex8 = DOMSummaryExtractor(max_elements=50)
    ex8.feed('<a href="/chat/1">Chat 1</a><a href="/chat/2">Chat 2</a>')
    links = [e for e in ex8.elements if e.get("tag") == "a"]
    _t("T8 test_dom_extractor_elements",
       len(links) == 2
       and links[0]["href"] == "/chat/1"
       and links[1]["href"] == "/chat/2",
       f"links={json.dumps(links, ensure_ascii=False)}")

    # ── T9: test_dom_extractor_classes_ids ─────────────────────────
    ex9 = DOMSummaryExtractor(max_elements=50)
    ex9.feed('<div class="chat-card active" id="msg-1">Hello</div>')
    _t("T9 test_dom_extractor_classes_ids",
       "chat-card" in ex9.all_classes
       and "active" in ex9.all_classes
       and "msg-1" in ex9.all_ids,
       f"classes={sorted(ex9.all_classes)}, ids={sorted(ex9.all_ids)}")

    # ── T10: test_clear_resets ─────────────────────────────────────
    t10 = Tracer("t10")
    t10.record("event.a", x=1)
    t10.record("event.b", y=2)
    t10.clear()
    _t("T10 test_clear_resets",
       len(t10._events) == 0 and t10.get_summary()["total_events"] == 0,
       f"events_after_clear={len(t10._events)}, summary_events={t10.get_summary()['total_events']}")

    # ── result ─────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"  TEST RESULTS: {passed}/{passed + failed} passed, {failed} failed")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
