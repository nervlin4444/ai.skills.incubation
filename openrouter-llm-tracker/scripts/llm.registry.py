"""
---
title: "llm.registry.py"
name: "openrouter-llm-tracker"
description: "F-002: Registry read/write, daily snapshot, and CLI queries. Save model list to master registry and daily snapshot."
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
  local_path: "{baseDir}/scripts/llm.registry.py"
  github_path: "openrouter-llm-tracker/scripts/llm.registry.py"
---
"""
# openrouter-llm-tracker/scripts/llm.registry.py
# F-002: Registry read/write, daily snapshot, and CLI queries

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any


def save_registry(models: List[Dict[str, Any]], data_dir: str) -> None:
    """Save model list to master registry and daily snapshot."""
    os.makedirs(data_dir, exist_ok=True)
    history_dir = os.path.join(data_dir, "llm.history")
    os.makedirs(history_dir, exist_ok=True)

    registry = {
        "models": models,
        "meta": {
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": len(models),
        }
    }

    registry_path = os.path.join(data_dir, "llm.registry.json")
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot_path = os.path.join(history_dir, f"{today}.json")
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"Registry saved: {registry_path} ({len(models)} models)")
    print(f"Snapshot saved: {snapshot_path}")


def load_registry(data_dir: str) -> Dict[str, Any]:
    """Load master registry from assets directory."""
    registry_path = os.path.join(data_dir, "llm.registry.json")
    if not os.path.exists(registry_path):
        return {"models": [], "meta": {"updated_at": "", "count": 0}}

    with open(registry_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_snapshot(data_dir: str, date_str: str) -> Dict[str, Any]:
    """Load daily snapshot by date string (YYYY-MM-DD)."""
    snapshot_path = os.path.join(data_dir, "llm.history", f"{date_str}.json")
    if not os.path.exists(snapshot_path):
        return {"models": [], "meta": {"updated_at": "", "count": 0}}

    with open(snapshot_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _list_models(registry: Dict[str, Any], free_only: bool = False,
                 tier: str = None, llm_type: str = None,
                 search: str = None) -> List[Dict[str, Any]]:
    """Filter and return models matching criteria."""
    models = registry.get("models", [])
    result = []
    for m in models:
        if free_only:
            pricing = m.get("pricing", {})
            if pricing.get("input_per_1m", 0) != 0 or pricing.get("output_per_1m", 0) != 0:
                continue
        if tier and m.get("assignment_tier") != tier:
            continue
        if llm_type and m.get("llm_type") != llm_type:
            continue
        if search:
            keyword = search.lower()
            name = (m.get("name") or "").lower()
            model_id = (m.get("id") or "").lower()
            if keyword not in name and keyword not in model_id:
                continue
        result.append(m)
    return result


def _print_table(models: List[Dict[str, Any]]) -> None:
    """Print models as a compact table."""
    if not models:
        print("No models found.")
        return
    header = f"{'ID':<45} {'Name':<30} {'Tier':<20} {'Type':<12} {'Input':>8} {'Output':>8}"
    print(header)
    print("-" * len(header))
    for m in models:
        p = m.get("pricing", {})
        print(f"{m.get('id','')[:44]:<45} {m.get('name','')[:29]:<30} "
              f"{m.get('assignment_tier',''):<20} {m.get('llm_type',''):<12} "
              f"{p.get('input_per_1m',0):>8.4f} {p.get('output_per_1m',0):>8.4f}")


def _print_count(registry: Dict[str, Any]) -> None:
    """Print statistics grouped by vendor, tier, and type."""
    models = registry.get("models", [])
    if not models:
        print("Registry empty.")
        return

    from collections import Counter
    vendors = Counter(m.get("vendor", "Unknown") for m in models)
    tiers = Counter(m.get("assignment_tier", "Unknown") for m in models)
    types = Counter(m.get("llm_type", "Unknown") for m in models)

    print(f"Total models: {len(models)}")
    print(f"\nBy Vendor ({len(vendors)}):\n" + "\n".join(f"  {k}: {v}" for k, v in vendors.most_common()))
    print(f"\nBy Tier ({len(tiers)}):\n" + "\n".join(f"  {k}: {v}" for k, v in tiers.most_common()))
    print(f"\nBy Type ({len(types)}):\n" + "\n".join(f"  {k}: {v}" for k, v in types.most_common()))


def _get_model(registry: Dict[str, Any], model_id: str) -> None:
    """Print single model details as JSON."""
    for m in registry.get("models", []):
        if m.get("id") == model_id:
            print(json.dumps(m, indent=2, ensure_ascii=False))
            return
    print(json.dumps({"error": f"Model not found: {model_id}"}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Registry Manager")
    parser.add_argument("data_dir", help="Path to assets directory (supports spaces, wrap in quotes)")
    parser.add_argument("--list", action="store_true", help="List all models")
    parser.add_argument("--free-only", action="store_true", help="List only free models (pricing=0)")
    parser.add_argument("--filter-tier", dest="tier", help="Filter by assignment tier")
    parser.add_argument("--filter-type", dest="llm_type", help="Filter by LLM type")
    parser.add_argument("--search", help="Search by name or ID keyword")
    parser.add_argument("--get", dest="model_id", help="Get single model JSON by ID")
    parser.add_argument("--count", action="store_true", help="Show statistics")
    parser.add_argument("--snapshot", dest="date_str", help="Load snapshot YYYY-MM-DD instead of master")

    args = parser.parse_args()

    if args.date_str:
        registry = load_snapshot(args.data_dir, args.date_str)
    else:
        registry = load_registry(args.data_dir)

    if args.list or args.free_only or args.tier or args.llm_type or args.search:
        models = _list_models(registry, free_only=args.free_only, tier=args.tier,
                              llm_type=args.llm_type, search=args.search)
        _print_table(models)
    elif args.model_id:
        _get_model(registry, args.model_id)
    elif args.count:
        _print_count(registry)
    else:
        print(json.dumps(registry.get("meta", {}), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
