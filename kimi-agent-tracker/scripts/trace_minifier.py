
"""
---
title: "Playwright Trace Minifier"
name: "kimi-agent-tracker"
description: "Compresses bulky Playwright trace files into lightweight structural summaries. Extracts DOM classes, IDs, conversation-related elements, and network calls for rapid selector debugging without context explosion."
version: "5.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-28T10:30:00Z"
auth_config:
  provider: "none"
  auth_method: "none"
  token_env_var: "NONE"
  env_file_path: "none"
file_mapping:
  local_path: "{baseDir}/scripts/trace_minifier.py"
  github_path: "kimi-agent-tracker/scripts/trace_minifier.py"
---
"""

import argparse
import json
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path
from html.parser import HTMLParser
from typing import List, Dict, Any, Optional, Set
from datetime import datetime


# =============================================================================
# DOM Summary Extractor
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
# Main
# =============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Playwright Trace Minifier v5.0.0"
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

    args = parser.parse_args()

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
        "generator": "trace_minifier.py",
        "version": "5.0.0",
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


if __name__ == "__main__":
    main()
