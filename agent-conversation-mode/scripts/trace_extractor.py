"""
---
title: "Trace Extractor"
name: agent-conversation-mode
description: "Platform trace file extraction with minimal parsing. Reads header metadata, copies full JSON verbatim."
version: "v6.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T20:57:00+08:00"
fixes: []
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  - local_path: "{baseDir}/scripts/trace_extractor.py"
    github_path: "agent-conversation-mode/scripts/trace_extractor.py"
---
"""

# trace_extractor.py v6.0.0
# Design: Minimal parsing. Read header for metadata, copy full JSON verbatim.
# No deep span analysis. No content filtering. Fast and simple.
# State file (last_processed.json) includes _meta frontmatter per spec.

import os
import json
import glob
from pathlib import Path
from datetime import datetime


class TraceExtractor:
    def __init__(self, traces_dir=None, data_dir=None, state_dir=None):
        self.traces_dir = Path(traces_dir) if traces_dir else Path.home() / ".workbuddy" / "traces"
        base = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base / "data"
        self.state_dir = Path(state_dir) if state_dir else base / "state"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.conversation_path = self.data_dir / "CONVERSATION.md"
        self.state_path = self.state_dir / "last_processed.json"
        self.header_size = 2048  # Bytes to read for metadata extraction

    def _init_state(self):
        return {
            "_meta": {
                "title": "Last Processed Traces",
                "name": "agent-conversation-mode",
                "description": "State tracking for processed trace files.",
                "version": "v6.0.0",
                "github_repository": "nervlin4444/ai.skills.incubation",
                "target_branch": "main",
                "updated_at": datetime.now().isoformat(),
                "fixes": [],
                "auth_config": {
                    "provider": "github",
                    "auth_method": "token",
                    "token_env_var": "GITHUB_TOKEN",
                    "env_file_path": "{baseDir}/.env"
                },
                "file_mapping": {
                    "local_path": "{baseDir}/state/last_processed.json",
                    "github_path": "agent-conversation-mode/state/last_processed.json"
                }
            },
            "processed_traces": {},
            "schema_version": "1.0.0"
        }

    def _load_state(self):
        if not self.state_path.exists():
            state = self._init_state()
            self._save_state(state)
            return state
        with open(self.state_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_state(self, state):
        if "_meta" in state:
            state["_meta"]["updated_at"] = datetime.now().isoformat()
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def _extract_header(self, trace_path):
        """Read first 2KB to extract metadata without loading full JSON."""
        with open(trace_path, "r", encoding="utf-8") as f:
            header = f.read(self.header_size)
        try:
            data = json.loads(header)
            trace = data.get("trace", {})
            return {
                "trace_id": trace.get("traceId", "unknown"),
                "session_id": trace.get("sessionId", "unknown"),
                "agent_name": trace.get("agentName", "unknown"),
                "platform": trace.get("agentName", "unknown").lower(),
                "model": ",".join(trace.get("modelInfo", {}).get("models", ["unknown"])),
                "started_at": trace.get("startedAt", ""),
                "ended_at": trace.get("endedAt", ""),
                "duration_ms": trace.get("duration", 0),
                "total_tokens": trace.get("totalTokens", 0),
                "span_count": trace.get("spanCount", 0),
            }
        except (json.JSONDecodeError, AttributeError):
            return None

    def _format_entry(self, meta, raw_json):
        """Format a single trace entry for CONVERSATION.md."""
        ts = meta.get("started_at", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts_local = dt.strftime("%Y-%m-%d %H:%M:%S%z")
            except ValueError:
                ts_local = ts
        else:
            ts_local = "unknown"

        lines = [
            "",
            "## [TRACE] " + meta.get("trace_id", "unknown") + " | " + ts_local,
            "### Meta",
            "- Platform: " + meta.get("platform", "unknown"),
            "- Agent: " + meta.get("agent_name", "unknown"),
            "- Model: " + meta.get("model", "unknown"),
            "- Session: " + meta.get("session_id", "unknown"),
            "- Duration: " + str(meta.get("duration_ms", 0)) + "ms | Tokens: " + str(meta.get("total_tokens", 0)) + " | Spans: " + str(meta.get("span_count", 0)),
            "",
            "### Raw Trace",
            "```json",
            raw_json,
            "```",
            "",
            "---",
        ]
        return "\n".join(lines)

    def _find_trace_files(self):
        """Find all trace files sorted by modification time (newest first)."""
        pattern = str(self.traces_dir / "*" / "trace_*.json")
        files = glob.glob(pattern)
        files.sort(key=os.path.getmtime, reverse=True)
        return [Path(f) for f in files]

    def process_new_traces(self):
        """Main entry: find new traces, extract metadata, append full JSON."""
        state = self._load_state()
        processed = state.get("processed_traces", {})
        trace_files = self._find_trace_files()

        new_count = 0
        for trace_path in trace_files:
            meta = self._extract_header(trace_path)
            if not meta:
                continue

            trace_id = meta["trace_id"]
            if trace_id in processed:
                continue  # Already processed

            # Read full JSON content
            with open(trace_path, "r", encoding="utf-8") as f:
                raw_json = f.read()

            # Append to CONVERSATION.md
            entry = self._format_entry(meta, raw_json)
            with open(self.conversation_path, "a", encoding="utf-8") as f:
                f.write(entry)

            # Mark as processed
            processed[trace_id] = {
                "processed_at": datetime.now().isoformat(),
                "file_path": str(trace_path),
                "started_at": meta.get("started_at", ""),
            }
            new_count += 1

        if new_count > 0:
            state["processed_traces"] = processed
            self._save_state(state)

        return {"processed": new_count, "total_traces": len(trace_files)}
