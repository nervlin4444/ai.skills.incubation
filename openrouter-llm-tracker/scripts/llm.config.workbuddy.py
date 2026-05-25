"""
---
title: "llm.config.workbuddy.py"
name: "openrouter-llm-tracker"
description: "F-005: Generate WorkBuddy-compatible JSON config in official schema. Supports single model, batch top-N, or smart-merge into existing agent config."
version: "v1.2.2"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T11:58:00+08:00"
fixes: []
auth_config:
  provider: openrouter
  auth_method: token
  token_env_var: OPENROUTER_API_KEY
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/scripts/llm.config.workbuddy.py"
  github_path: "openrouter-llm-tracker/scripts/llm.config.workbuddy.py"
---
"""
# openrouter-llm-tracker/scripts/llm.config.workbuddy.py
# F-005: Generate WorkBuddy-compatible JSON config — single model, batch top-N, or smart-merge
# Output format matches ACTUAL ~/.workbuddy/models.json schema
# Version: 1.2.2 (2026-05-14) — Fixed output format to match models.json schema

import json
import os
import shutil
import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List

# WorkBuddy official default models.json path (cross-platform)
WORKBUDDY_DEFAULT_PATH = os.path.expanduser("~/.workbuddy/models.json")

# Script-relative default asset paths
_SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DATA_DIR = os.path.join(_SCRIPT_DIR, "..", "data")
DEFAULT_REGISTRY  = os.path.join(_DEFAULT_DATA_DIR, "llm.registry.json")
DEFAULT_SCORES   = os.path.join(_DEFAULT_DATA_DIR, "llm.scores.json")

# Runtime params profile by param_type
PROFILES = {
    "general":   {"temperature": 0.7,  "top_p": 0.9,  "presence_penalty": 0.0, "frequency_penalty": 0.0},
    "agentic":   {"temperature": 0.3,  "top_p": 0.95, "presence_penalty": 0.1, "frequency_penalty": 0.1},
    "vision":    {"temperature": 0.5,  "top_p": 0.9,  "presence_penalty": 0.0, "frequency_penalty": 0.0},
    "reasoning": {"temperature": 0.2,  "top_p": 0.95, "presence_penalty": 0.0, "frequency_penalty": 0.0},
    "coding":    {"temperature": 0.1,  "top_p": 0.95, "presence_penalty": 0.0, "frequency_penalty": 0.0},
}


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------------------------------------------------
# Field mappers — map OpenRouter registry fields → models.json fields
# -------------------------------------------------------------------------

def _map_region(vendor: str) -> str:
    mapping = {
        "NVIDIA": "United States",
        "OpenAI": "United States",
        "Google": "United States",
        "Anthropic": "United States",
        "Meta": "United States",
        "Microsoft": "United States",
        "Cohere": "Europe",
        "Mistralai": "Europe",
        "Poolside": "Europe",
        "Alibaba": "China",
        "Tencent": "China",
        "Baidu": "China",
        "DeepSeek": "China",
        "Moonshotai": "China",
        "MiniMax": "China",
        "Z.AI": "China",
    }
    return mapping.get(vendor, "Unknown")


def _map_reasoning_level(capabilities: Dict) -> str:
    r = capabilities.get("reasoning", "false")
    if isinstance(r, bool):
        return "high" if r else "false"
    return str(r)


def _map_type_from_model(model: Dict) -> str:
    lt = model.get("llm_type", "general")
    return {
        "general": "general",
        "coding": "coding",
        "ocr": "general",
        "vision": "general",
        "multimodal": "multimodal",
        "reasoning": "reasoning",
        "agentic": "general",
        "audio": "general",
    }.get(lt, "general")


def _map_tier(mid: str, scores: Dict, registry: Dict) -> str:
    rec = scores.get("models", {}).get(mid)
    if rec:
        return rec.get("current_tier", "domain_expert")
    model = next((m for m in registry.get("models", []) if m.get("id") == mid), {})
    return model.get("assignment_tier", "domain_expert")


def build_entry(model: Dict, param_type: str,
               scores: Dict, registry: Dict) -> Dict[str, Any]:
    """Build one model entry matching ~/.workbuddy/models.json format exactly."""
    mid      = model.get("id", "")
    vendor   = model.get("vendor", "")
    pricing  = model.get("pricing", {})
    caps     = model.get("capabilities", {})
    params   = PROFILES.get(param_type, PROFILES["agentic"])

    return {
        "key":               mid,
        "display_name":      model.get("name", mid),
        "vendor":            vendor,
        "region":            _map_region(vendor),
        "type":              _map_type_from_model(model),
        "tier":              _map_tier(mid, scores, registry),
        "context_window":    model.get("context", {}).get("max_input", 0),
        "max_output_tokens": model.get("context", {}).get("max_output", 0),
        "supports_tools":    caps.get("tools", False),
        "supports_vision":   caps.get("vision", False),
        "reasoning_level":   _map_reasoning_level(caps),
        "pricing": {
            "input_per_1m":  pricing.get("input_per_1m", 0.0),
            "output_per_1m": pricing.get("output_per_1m", 0.0),
        },
        "release_date":      model.get("release_date", ""),
        "runtime_params": {
            "temperature":       params["temperature"],
            "top_p":             params["top_p"],
            "presence_penalty":  params["presence_penalty"],
            "frequency_penalty": params["frequency_penalty"],
        },
    }


# -------------------------------------------------------------------------
# Core logic
# -------------------------------------------------------------------------

def _get_top_entries(registry_path: str, scores_path: str,
                     param_type: str, top_n: int,
                     free_only: bool) -> List[Dict[str, Any]]:
    """Return top-N model entries (models.json format)."""
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"Registry not found: {registry_path}")
    if not os.path.exists(scores_path):
        raise FileNotFoundError(f"Scores not found: {scores_path}")

    registry = _load_json(registry_path)
    scores  = _load_json(scores_path)

    scored = []
    for mid, rec in scores.get("models", {}).items():
        model = next((m for m in registry.get("models", []) if m.get("id") == mid), None)
        if not model:
            continue
        if free_only:
            p = model.get("pricing", {})
            if p.get("input_per_1m", 0) != 0 or p.get("output_per_1m", 0) != 0:
                continue
        scored.append({
            "model":      model,
            "composite":  rec.get("current_composite", 0),
            "tier":       rec.get("current_tier", "domain_expert"),
        })

    if not scored:
        return []

    scored.sort(key=lambda x: (-x["composite"], x["model"].get("id", "")))
    top = scored[:top_n]
    return [build_entry(item["model"], param_type, scores, registry) for item in top]


def generate_single_model(model_id: str, param_type: str,
                         registry_path: str = None) -> str:
    """Generate WorkBuddy-compatible JSON for a single model."""
    registry_path = registry_path or DEFAULT_REGISTRY
    if not os.path.exists(registry_path):
        return json.dumps({"error": f"Registry not found: {registry_path}"}, ensure_ascii=False)
    registry = _load_json(registry_path)
    model = next((m for m in registry.get("models", []) if m.get("id") == model_id), None)
    if not model:
        return json.dumps({"error": "Model ID not found in registry"}, ensure_ascii=False)
    scores = _load_json(DEFAULT_SCORES) if os.path.exists(DEFAULT_SCORES) else {}
    entry = build_entry(model, param_type, scores, registry)
    return json.dumps(entry, indent=2, ensure_ascii=False)


def generate_batch_config(registry_path: str = None,
                          scores_path: str = None, param_type: str = "agentic",
                          top_n: int = 10, free_only: bool = False) -> str:
    """Generate batch top-N config (standalone, not wrapped)."""
    registry_path = registry_path or DEFAULT_REGISTRY
    scores_path   = scores_path   or DEFAULT_SCORES
    entries = _get_top_entries(registry_path, scores_path, param_type, top_n, free_only)
    if not entries:
        return json.dumps({"error": "No scored models match criteria"}, ensure_ascii=False)
    return json.dumps(entries, indent=2, ensure_ascii=False)


def merge_into_workbuddy(param_type: str = "agentic",
                         registry_path: str = None,
                         scores_path: str = None, top_n: int = 10,
                         free_only: bool = False,
                         target_path: str = None, dry_run: bool = False) -> str:
    """Smart-merge top-N models into existing ~/.workbuddy/models.json."""
    registry_path = registry_path or DEFAULT_REGISTRY
    scores_path   = scores_path   or DEFAULT_SCORES
    target_path   = target_path   or WORKBUDDY_DEFAULT_PATH

    if not os.path.exists(target_path):
        return json.dumps(
            {"error": f"WorkBuddy config not found: {target_path}. "
                      f"Create it first or use --merge-into with a custom path."},
            ensure_ascii=False
        )

    existing = _load_json(target_path)
    entries  = _get_top_entries(registry_path, scores_path, param_type, top_n, free_only)
    if not entries:
        return json.dumps({"error": "No scored models match criteria"}, ensure_ascii=False)

    # Ensure structure
    if "workbuddy" not in existing:
        existing["workbuddy"] = {"models": [], "routing": {}, "meta": {}}
    if "models" not in existing["workbuddy"]:
        existing["workbuddy"]["models"] = []
    if "routing" not in existing["workbuddy"]:
        existing["workbuddy"]["routing"] = {}
    if "meta" not in existing["workbuddy"]:
        existing["workbuddy"]["meta"] = {}

    existing["workbuddy"]["models"] = entries
    existing["workbuddy"]["routing"]["enabled"]          = True
    existing["workbuddy"]["routing"]["primary_model"]    = entries[0]["key"]
    existing["workbuddy"]["routing"]["fallback_models"]   = [e["key"] for e in entries[1:]]
    existing["workbuddy"]["routing"].setdefault("max_retries", 3)
    existing["workbuddy"]["routing"].setdefault("timeout_seconds", 30)
    existing["workbuddy"]["routing"].setdefault("retry_delay_ms", 500)
    existing["workbuddy"]["meta"]["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    existing["workbuddy"]["meta"]["source"]       = "openrouter-llm-tracker"
    existing["workbuddy"]["meta"]["count"]        = len(entries)

    backup_path = target_path + ".backup"

    if dry_run:
        output = {
            "_dry_run": True,
            "target_path": target_path,
            "backup_path": backup_path,
            "merged_config": existing,
        }
        return json.dumps(output, indent=2, ensure_ascii=False)

    if os.path.exists(backup_path):
        os.remove(backup_path)
    shutil.copy2(target_path, backup_path)

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return json.dumps({
        "status": "success",
        "target_path": target_path,
        "backup_path": backup_path,
        "models_merged": len(entries),
        "primary": entries[0]["key"],
    }, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="WorkBuddy Config Generator (models.json format)")
    parser.add_argument("--model-id", default=None,
                        help="Model ID for single-model mode (omit for batch/merge mode)")
    parser.add_argument("--param-type", default="agentic",
                        help="Parameter profile: general / agentic / vision / reasoning / coding (default: agentic)")
    parser.add_argument("--registry", default=None,
                        help=f"Path to registry JSON (default: {DEFAULT_REGISTRY})")
    parser.add_argument("--scores", default=None,
                        help=f"Path to scores JSON (default: {DEFAULT_SCORES})")
    parser.add_argument("--top", type=int, default=10,
                        help="Top N models for batch/merge mode (default: 10)")
    parser.add_argument("--free-only", action="store_true",
                        help="Only include free models")
    parser.add_argument("--merge-into", nargs="?", const=WORKBUDDY_DEFAULT_PATH, default=None,
                        help="Merge into existing models.json. Use default path if no value provided.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview merge result without writing. Recommended before actual merge.")
    parser.add_argument("--output", default=None,
                        help="Write standalone config to file instead of stdout")

    args = parser.parse_args()

    registry_path = args.registry or DEFAULT_REGISTRY
    scores_path  = args.scores   or DEFAULT_SCORES

    # Merge mode: --merge-into present (with or without value)
    if args.merge_into is not None:
        target = args.merge_into
        result = merge_into_workbuddy(
            param_type   = args.param_type,
            registry_path = registry_path,
            scores_path  = scores_path,
            top_n        = args.top,
            free_only    = args.free_only,
            target_path  = target,
            dry_run      = args.dry_run,
        )
        print(result)
        return

    # Single model mode
    if args.model_id:
        result = generate_single_model(args.model_id, args.param_type, registry_path)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"Config written to: {args.output}")
        else:
            print(result)
        return

    # Batch mode
    result = generate_batch_config(
        registry_path, scores_path, args.param_type, args.top, args.free_only
    )
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Config written to: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
