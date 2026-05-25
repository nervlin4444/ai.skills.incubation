"""
---
title: "Conversation Append Script"
name: "agent-conversation-mode"
description: "Passive real-time recording script for Agent Swarm conversation backup. Supports short content via CLI args and long content via JSON file transfer. v1.4.0."
version: "v1.4.0"
github_repository: "nervlin4444/ai.agent.harness"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/conversation_append.py"
    github_path: "/agent-conversation-mode/scripts/conversation_append.py"
---
"""

# conversation_append.py v1.4.0 - Passive Real-time Recording
# Passive trigger archiver, non-Daemon, zero privilege escalation
# Changes in v1.4.0:
#   - Added --from-file parameter for long content (bypasses command line length limit)
#   - --user-input / --agent-response retained for short content (< 500 chars)
#   - JSON format input file, cross-platform compatible
#   - No temp scripts needed, only temp JSON data files

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ============================================================
# CONFIGURATION
# ============================================================
DEFAULT_CONFIG = {
    "max_block_size": 1024 * 1024,
    "max_file_size": 500 * 1024 * 1024,
    "max_dir_size": 500 * 1024 * 1024,
    "cleanup_days": 0,
    "enabled": True,
    "sensitive_patterns": [
        r"(?i)(password|passwd|pwd)\s*[=:]\s*[^\s]+",
        r"(?i)(api[_-]?key|token|secret)\s*[=:]\s*[^\s]+",
        r"(?i)(credit[_-]?card|cc|card[_-]?number)\s*[=:]\s*\d+",
        r"(?i)sk-[a-zA-Z0-9]{48}",
        r"(?i)Bearer\s+[a-zA-Z0-9\-_]+",
    ],
    "allowed_block_types": [
        "tool_call", "process_msg", "table", "list",
        "final_response", "user_input", "error"
    ],
}

SCRIPT_VERSION = "v1.4.0"
SHORT_CONTENT_LIMIT = 500  # chars: below this use --user-input/--agent-response, above use --from-file

# ============================================================
# CORE FUNCTIONS
# ============================================================

def is_enabled() -> bool:
    env_val = os.getenv("CONVERSATION_REALTIME_RECORD", "true").lower()
    return env_val in ("true", "1", "yes", "enabled")

def filter_sensitive(content: str) -> str:
    for pattern in DEFAULT_CONFIG["sensitive_patterns"]:
        content = re.sub(pattern, "[REDACTED]", content)
    return content

def validate_block(block_type: str, content: str) -> Tuple[bool, str]:
    if block_type not in DEFAULT_CONFIG["allowed_block_types"]:
        return False, f"[BLOCK-REJECTED] Type '{block_type}' not allowed."
    content_bytes = content.encode("utf-8")
    if len(content_bytes) > DEFAULT_CONFIG["max_block_size"]:
        return False, f"[BLOCK-OVERSIZE] {len(content_bytes)} bytes > limit."
    return True, ""

def compute_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()[:8]

def get_conversation_path(skill_assets_dir: str, conversation_id: str, date_stamp: str) -> Path:
    base_dir = Path(skill_assets_dir)
    conv_dir = base_dir
    conv_dir.mkdir(parents=True, exist_ok=True)
    primary = conv_dir / "CONVERSATION.md"
    if primary.exists() and primary.stat().st_size > DEFAULT_CONFIG["max_file_size"]:
        idx = 1
        while (conv_dir / f"CONVERSATION.{idx}.md").exists():
            idx += 1
        primary = conv_dir / f"CONVERSATION.{idx}.md"
    return primary

def cleanup_old_files(conv_dir: Path) -> List[str]:
    return []

def check_dir_size(conv_dir: Path) -> Tuple[bool, str]:
    total = sum(f.stat().st_size for f in conv_dir.rglob("*") if f.is_file())
    if total > DEFAULT_CONFIG["max_dir_size"]:
        return False, f"[DIR-FULL] {total} bytes > limit."
    return True, ""

def format_block_marker(block_type: str, timestamp: str, meta: Optional[Dict] = None) -> str:
    meta_str = json.dumps(meta, ensure_ascii=False) if meta else ""
    return f"## [BLOCK: {block_type}] {timestamp}{(' ' + meta_str) if meta_str else ''}"

def append_structured_block(
    conversation_path: str,
    block_type: str,
    content: str,
    metadata: Optional[Dict] = None,
    conversation_id: Optional[str] = None,
    date_stamp: Optional[str] = None,
) -> Dict:
    result = {
        "success": False,
        "bytes_written": 0,
        "warning": "",
        "hash": "",
        "path": "",
    }
    if not is_enabled():
        result["warning"] = "[RECORD-DISABLED] CONVERSATION_REALTIME_RECORD is false."
        return result
    cp = Path(conversation_path)
    if cp.is_dir():
        if not conversation_id or not date_stamp:
            result["warning"] = "[PATH-ERROR] conversation_id and date_stamp required."
            return result
        target = get_conversation_path(str(cp), conversation_id, date_stamp)
    else:
        target = cp
        target.parent.mkdir(parents=True, exist_ok=True)
    result["path"] = str(target)
    ok, warning = validate_block(block_type, content)
    if not ok:
        result["warning"] = warning
        if "OVERSIZE" in warning:
            content = content[:DEFAULT_CONFIG["max_block_size"]//4]
        else:
            return result
    content = filter_sensitive(content)
    h = compute_hash(content)
    result["hash"] = h
    dir_ok, dir_warn = check_dir_size(target.parent)
    if not dir_ok:
        result["warning"] = dir_warn
        return result
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta = metadata or {}
    meta["hash"] = h

    if not target.exists() or target.stat().st_size == 0:
        fm = {
            "id": conversation_id or "unknown",
            "date": date_stamp or datetime.now().strftime("%Y-%m-%d"),
            "status": "active",
            "realtime_record": "enabled" if is_enabled() else "disabled",
            "version": "v3.3.6",
        }
        frontmatter_lines = ["---"]
        for k, v in fm.items():
            frontmatter_lines.append(f'{k}: "{v}"')
        frontmatter_lines.extend(["---", ""])
        with open(target, "w", encoding="utf-8") as f:
            f.write("\n".join(frontmatter_lines))

    block_lines = [
        "",
        format_block_marker(block_type, ts, meta),
        content,
        f"<!-- END BLOCK: {block_type} hash={h} -->",
        "",
    ]
    block_text = "\n".join(block_lines)
    block_bytes = block_text.encode("utf-8")
    try:
        with open(target, "a", encoding="utf-8") as f:
            f.write(block_text)
        result["bytes_written"] = len(block_bytes)
        result["success"] = True
    except Exception as e:
        result["warning"] = f"[RECORD-FAILED] {type(e).__name__}: {e}"
        return result
    return result

def append_conversation(
    conversation_path: str,
    user_input: str,
    agent_response: str,
    conversation_id: Optional[str] = None,
    date_stamp: Optional[str] = None,
) -> Dict:
    results = []
    if user_input:
        r1 = append_structured_block(
            conversation_path, "user_input", user_input,
            conversation_id=conversation_id, date_stamp=date_stamp,
        )
        results.append(r1)
    if agent_response:
        r2 = append_structured_block(
            conversation_path, "final_response", agent_response,
            conversation_id=conversation_id, date_stamp=date_stamp,
        )
        results.append(r2)
    total_bytes = sum(r["bytes_written"] for r in results)
    warnings = " | ".join(r["warning"] for r in results if r["warning"])
    return {
        "success": all(r["success"] for r in results),
        "bytes_written": total_bytes,
        "warning": warnings,
        "blocks": len(results),
        "path": results[0]["path"] if results else "",
    }

def init_conversation_file(
    skill_assets_dir: str,
    conversation_id: str,
    date_stamp: str,
    frontmatter: Optional[Dict] = None,
) -> str:
    target = get_conversation_path(skill_assets_dir, conversation_id, date_stamp)
    fm = frontmatter or {}
    fm.setdefault("id", conversation_id)
    fm.setdefault("date", date_stamp)
    fm.setdefault("status", "active")
    fm.setdefault("realtime_record", "enabled" if is_enabled() else "disabled")
    fm.setdefault("version", "v3.3.6")
    lines = ["---"]
    for k, v in fm.items():
        lines.append(f'{k}: "{v}"')
    lines.extend(["---", ""])
    header = "\n".join(lines)
    if not target.exists():
        with open(target, "w", encoding="utf-8") as f:
            f.write(header)
    return str(target)

# ============================================================
# CLI - v1.4.0 enhanced for long content support
# ============================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Conversation Append Tool v1.4.0")
    parser.add_argument("--file", required=True, help="Path to CONVERSATION.md or skill assets directory")
    parser.add_argument("--type", default="final_response", help="Block type")
    parser.add_argument("--content", help="Content to append (not required when using --init or --user-input or --from-file)")
    parser.add_argument("--conv-id", help="Conversation ID")
    parser.add_argument("--date", help="Date stamp YYYY-MM-DD")
    parser.add_argument("--init", action="store_true", help="Initialize new conversation file")
    # v1.3.0 additions:
    parser.add_argument("--user-input", help="User message content (auto-formatted as user_input block). Use for short content (< 500 chars).")
    parser.add_argument("--agent-response", help="Agent response content (auto-formatted as final_response block). Use for short content (< 500 chars).")
    # v1.4.0 additions:
    parser.add_argument("--from-file", help="Path to JSON file containing backup data. Use for long content (> 500 chars) to bypass command line length limit.")
    parser.add_argument("--version", action="store_true", help="Show script version and exit")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    if args.version:
        print(f"[VERSION] {SCRIPT_VERSION}")
        exit(0)

    if args.init:
        if not args.conv_id or not args.date:
            print("[ERROR] --init requires --conv-id and --date")
            exit(1)
        path = init_conversation_file(args.file, args.conv_id, args.date)
        print(f"[INIT] Created: {path}")
    elif args.from_file:
        # v1.4.0: Long content mode via JSON file
        try:
            with open(args.from_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = append_conversation(
                args.file,
                user_input=data.get("user_input", ""),
                agent_response=data.get("agent_response", ""),
                conversation_id=args.conv_id,
                date_stamp=args.date,
            )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                status = "OK" if result["success"] else "FAILED"
                print(f"[{status}] Wrote {result['bytes_written']} bytes ({result['blocks']} blocks) to {result['path']}")
                if result["warning"]:
                    print(f"[WARNING] {result['warning']}")
        except Exception as e:
            print(f"[ERROR] Failed to read from-file: {type(e).__name__}: {e}")
            exit(1)
    elif args.user_input or args.agent_response:
        # v1.3.0: Short content mode via command line args
        result = append_conversation(
            args.file,
            user_input=args.user_input or "",
            agent_response=args.agent_response or "",
            conversation_id=args.conv_id,
            date_stamp=args.date,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            status = "OK" if result["success"] else "FAILED"
            print(f"[{status}] Wrote {result['bytes_written']} bytes ({result['blocks']} blocks) to {result['path']}")
            if result["warning"]:
                print(f"[WARNING] {result['warning']}")
    else:
        if not args.content:
            print("[ERROR] --content is required (unless using --init or --user-input/--agent-response or --from-file)")
            exit(1)
        result = append_structured_block(
            args.file, args.type, args.content,
            conversation_id=args.conv_id, date_stamp=args.date,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            status = "OK" if result["success"] else "FAILED"
            print(f"[{status}] Wrote {result['bytes_written']} bytes to {result['path']}")
            if result["warning"]:
                print(f"[WARNING] {result['warning']}")