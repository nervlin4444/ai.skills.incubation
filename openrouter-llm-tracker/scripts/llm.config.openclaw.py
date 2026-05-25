"""
---
title: "llm.config.openclaw.py"
name: "openrouter-llm-tracker"
description: "F-004: Generate OpenClaw-compatible JSON config in official schema. Supports single model, batch top-N, or smart-merge into existing agent config."
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
  local_path: "{baseDir}/scripts/llm.config.openclaw.py"
  github_path: "openrouter-llm-tracker/scripts/llm.config.openclaw.py"
---
"""
# openrouter-llm-tracker/scripts/llm.config.openclaw.py
# F-004: Generate OpenClaw-compatible JSON config — single model, batch top-N, or smart-merge
# Output format matches OpenClaw official schema.

import json
import os
import shutil
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List

# OpenClaw official default config path (cross-platform)
OPENCLAW_DEFAULT_PATH = os.path.expanduser("~/.openclaw/config.json")

# Fixed OpenRouter endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Script-relative default asset paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DATA_DIR = os.path.join(_SCRIPT_DIR, "..", "data")
DEFAULT_REGISTRY = os.path.join(_DEFAULT_DATA_DIR, "llm.registry.json")
DEFAULT_SCORES = os.path.join(_DEFAULT_DATA_DIR, "llm.scores.json")

PROFILES = {
    "general":   {"temperature": 0.7, "top_p": 0.9,  "max_tokens": 4096},
    "agentic":   {"temperature": 0.3, "top_p": 0.95, "max_tokens": 8192},
    "vision":    {"temperature": 0.5, "top_p": 0.9,  "max_tokens": 4096},
    "reasoning": {"temperature": 0.2, "top_p": 0.95, "max_tokens": 16384},
    "coding":    {"temperature": 0.1, "top_p": 0.95, "max_tokens": 8192},
}


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_openclaw_models_map(models: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build OpenClaw models map: {model_id: {alias: name}}."""
    result = {}
    for m in models:
        mid = m.get("id")
        name = m.get("name", "")
        if mid:
            result[mid] = {"alias": name}
    return result


def _get_top_model_ids(registry_path: str, scores_path: str,
                       top_n: int, free_only: bool) -> List[Dict[str, Any]]:
    """Return top-N scored raw model records."""
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"Registry not found: {registry_path}")
    if not os.path.exists(scores_path):
        raise FileNotFoundError(f"Scores not found: {scores_path}")

    registry = _load_json(registry_path)
    scores = _load_json(scores_path)

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
            "model": model,
            "composite": rec.get("current_composite", 0),
            "tier": rec.get("current_tier", "staff"),
        })

    if not scored:
        return []

    scored.sort(key=lambda x: (-x["composite"], x["model"].get("id", "")))
    return [item["model"] for item in scored[:top_n]]


def generate_openclaw_config(model_id: str, param_type: str,
                             registry_path: str = None) -> str:
    """Generate OpenClaw-compatible JSON config for a single model."""
    registry_path = registry_path or DEFAULT_REGISTRY
    if not os.path.exists(registry_path):
        return json.dumps({"error": f"Registry not found: {registry_path}"}, ensure_ascii=False)
    registry = _load_json(registry_path)
    model = next((m for m in registry.get("models", []) if m.get("id") == model_id), None)
    if not model:
        return json.dumps({"error": "Model ID not found in registry"}, ensure_ascii=False)

    models_map = _build_openclaw_models_map([model])
    config = {
        "agents": {
            "defaults": {
                "model": {
                    "primary": model_id,
                    "fallbacks": [],
                },
                "models": models_map,
            },
        },
        "env": {
            "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}",
        },
    }
    return json.dumps(config, indent=2, ensure_ascii=False)


def generate_openclaw_batch_config(param_type: str, registry_path: str = None,
                                   scores_path: str = None, top_n: int = 10,
                                   free_only: bool = False) -> str:
    """Generate OpenClaw-compatible JSON config with top-N scored models."""
    registry_path = registry_path or DEFAULT_REGISTRY
    scores_path = scores_path or DEFAULT_SCORES
    top_models = _get_top_model_ids(registry_path, scores_path, top_n, free_only)
    if not top_models:
        return json.dumps({"error": "No scored models match criteria"}, ensure_ascii=False)

    primary = top_models[0]["id"]
    fallbacks = [m["id"] for m in top_models[1:]]
    models_map = _build_openclaw_models_map(top_models)

    config = {
        "agents": {
            "defaults": {
                "model": {
                    "primary": primary,
                    "fallbacks": fallbacks,
                },
                "models": models_map,
            },
        },
        "env": {
            "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}",
        },
    }
    return json.dumps(config, indent=2, ensure_ascii=False)


def merge_into_openclaw_config(param_type: str, registry_path: str = None,
                               scores_path: str = None, top_n: int = 10,
                               free_only: bool = False,
                               target_path: str = None, dry_run: bool = False) -> str:
    """Smart-merge top-N models into existing OpenClaw config."""
    registry_path = registry_path or DEFAULT_REGISTRY
    scores_path = scores_path or DEFAULT_SCORES
    target_path = target_path or OPENCLAW_DEFAULT_PATH

    if not os.path.exists(target_path):
        return json.dumps(
            {"error": f"OpenClaw config not found: {target_path}. "
                      f"Create it first or use --merge-into with a custom path."},
            ensure_ascii=False
        )

    existing = _load_json(target_path)
    top_models = _get_top_model_ids(registry_path, scores_path, top_n, free_only)
    if not top_models:
        return json.dumps({"error": "No scored models match criteria"}, ensure_ascii=False)

    primary = top_models[0]["id"]
    fallbacks = [m["id"] for m in top_models[1:]]
    models_map = _build_openclaw_models_map(top_models)

    if "agents" not in existing:
        existing["agents"] = {}
    if "defaults" not in existing["agents"]:
        existing["agents"]["defaults"] = {}
    if "model" not in existing["agents"]["defaults"]:
        existing["agents"]["defaults"]["model"] = {}

    existing["agents"]["defaults"]["model"]["primary"] = primary
    existing["agents"]["defaults"]["model"]["fallbacks"] = fallbacks
    existing["agents"]["defaults"]["models"] = models_map

    if "env" not in existing:
        existing["env"] = {}
    if "OPENROUTER_API_KEY" not in existing["env"]:
        existing["env"]["OPENROUTER_API_KEY"] = "${OPENROUTER_API_KEY}"

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
        "models_merged": len(top_models),
        "primary": primary,
    }, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenClaw Config Generator (agents.defaults.model format)"
    )
    # Flags (not positionals) to avoid ambiguity
    parser.add_argument(
        "--model-id", default=None,
        help="Model ID for single-model mode (omit for batch/merge mode)"
    )
    parser.add_argument(
        "--param-type", default="agentic",
        help="Parameter profile: general / agentic / vision / reasoning / coding (default: agentic)"
    )
    parser.add_argument(
        "--registry", default=None,
        help=f"Path to registry JSON (default: {DEFAULT_REGISTRY})"
    )
    parser.add_argument(
        "--scores", default=None,
        help=f"Path to scores JSON (default: {DEFAULT_SCORES})"
    )
    parser.add_argument(
        "--top", type=int, default=10,
        help="Top N models for batch/merge mode (default: 10)"
    )
    parser.add_argument(
        "--free-only", action="store_true",
        help="Only include free models"
    )
    parser.add_argument(
        "--merge-into", nargs="?", const=OPENCLAW_DEFAULT_PATH, default=None,
        help="Merge into existing OpenClaw config. Use default path if no value provided."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview merge result without writing. Recommended before actual merge."
    )
    parser.add_argument(
        "--output", default=None,
        help="Write standalone config to file instead of stdout"
    )

    args = parser.parse_args()

    registry_path = args.registry or DEFAULT_REGISTRY
    scores_path  = args.scores  or DEFAULT_SCORES

    # Merge mode
    if args.merge_into is not None:
        result = merge_into_openclaw_config(
            param_type   = args.param_type,
            registry_path = registry_path,
            scores_path  = scores_path,
            top_n        = args.top,
            free_only    = args.free_only,
            target_path  = args.merge_into,
            dry_run      = args.dry_run,
        )
        print(result)
        return

    # Single model mode
    if args.model_id:
        result = generate_openclaw_config(
            model_id      = args.model_id,
            param_type    = args.param_type,
            registry_path = registry_path,
        )
    else:
        # Batch mode
        result = generate_openclaw_batch_config(
            param_type    = args.param_type,
            registry_path = registry_path,
            scores_path  = scores_path,
            top_n        = args.top,
            free_only    = args.free_only,
        )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Config written to: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
