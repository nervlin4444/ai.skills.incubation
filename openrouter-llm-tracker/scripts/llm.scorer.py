"""
---
title: "llm.scorer.py"
name: "openrouter-llm-tracker"
description: "F-003: Score calculation, tier adjustment, leaderboard, and batch scoring with 429-aware logic."
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
  local_path: "{baseDir}/scripts/llm.scorer.py"
  github_path: "openrouter-llm-tracker/scripts/llm.scorer.py"
---
"""
# openrouter-llm-tracker/scripts/llm.scorer.py
# F-003: Score calculation, tier adjustment, leaderboard, and batch scoring with 429-aware logic

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

DEFAULT_WEIGHTS = {
    "latency": 0.20,
    "accuracy": 0.30,
    "tool_reliability": 0.20,
    "cost_efficiency": 0.15,
    "context_stability": 0.15,
}

DEFAULT_TIER_THRESHOLDS = {
    "omnipotent": 95,
    "c_level": 90,
    "specialist_manager": 85,
    "strategic_expert": 80,
    "domain_expert": 70,
    "supervisor": 60,
    "staff": 0,
}

TIER_ORDER = ["staff", "supervisor", "domain_expert", "strategic_expert",
              "specialist_manager", "c_level", "omnipotent"]

VALID_DIMENSIONS = {"latency", "accuracy", "tool_reliability",
                    "cost_efficiency", "context_stability"}


def _load_ranking_config(data_dir: str) -> Dict[str, float]:
    ranking_path = os.path.join(os.path.dirname(data_dir), "references", "RANKING.md")
    if not os.path.exists(ranking_path):
        return DEFAULT_WEIGHTS
    return DEFAULT_WEIGHTS


def _load_mapping_config(data_dir: str) -> Dict[str, int]:
    mapping_path = os.path.join(os.path.dirname(data_dir), "references", "MAPPING.md")
    if not os.path.exists(mapping_path):
        return DEFAULT_TIER_THRESHOLDS
    return DEFAULT_TIER_THRESHOLDS


def _calculate_composite(dimensions: Dict[str, int], weights: Dict[str, float]) -> float:
    total = 0.0
    weight_sum = 0.0
    for dim, score in dimensions.items():
        w = weights.get(dim, 0.0)
        total += score * w
        weight_sum += w
    if weight_sum == 0:
        return 0.0
    return round(total / weight_sum, 1)


def _determine_tier(composite: float, thresholds: Dict[str, int]) -> str:
    for tier in reversed(TIER_ORDER):
        threshold = thresholds.get(tier, 0)
        if composite >= threshold:
            return tier
    return "staff"


def update_score(model_id: str, dimensions: Dict[str, int], data_dir: str,
                 force: bool = False) -> Dict[str, Any]:
    weights = _load_ranking_config(data_dir)
    thresholds = _load_mapping_config(data_dir)

    scores_path = os.path.join(data_dir, "llm.scores.json")
    scores = {"models": {}, "meta": {"updated_at": ""}}

    if os.path.exists(scores_path):
        with open(scores_path, "r", encoding="utf-8") as f:
            scores = json.load(f)

    for dim, score in dimensions.items():
        if dim not in VALID_DIMENSIONS:
            raise ValueError(f"Invalid dimension: {dim}")
        if not isinstance(score, int) or not (0 <= score <= 100):
            raise ValueError(f"Score must be 0-100 int, got {score}")

    new_composite = _calculate_composite(dimensions, weights)
    record = scores["models"].get(model_id, {
        "scores": [], "current_composite": 0.0,
        "current_tier": "staff", "history": [],
    })

    alpha = 0.3
    old_composite = record.get("current_composite", 0.0)
    scores_list = record.get("scores", [])

    if old_composite == 0.0 and len(scores_list) == 0:
        updated_composite = new_composite
    else:
        updated_composite = round(alpha * new_composite + (1 - alpha) * old_composite, 1)

    old_tier = record.get("current_tier", "staff")
    new_tier = _determine_tier(updated_composite, thresholds)

    if not force and len(scores_list) < 3:
        new_tier = old_tier

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record["scores"].append({
        "timestamp": timestamp,
        "dimensions": dimensions,
        "composite": new_composite,
    })
    record["current_composite"] = updated_composite
    record["current_tier"] = new_tier

    if new_tier != old_tier:
        record["history"].append({
            "timestamp": timestamp,
            "composite": updated_composite,
            "tier_before": old_tier,
            "tier_after": new_tier,
            "reason": f"Composite {updated_composite} crossed threshold for {new_tier}",
        })

    scores["models"][model_id] = record
    scores["meta"]["updated_at"] = timestamp

    os.makedirs(data_dir, exist_ok=True)
    with open(scores_path, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)

    return {
        "model_id": model_id,
        "composite": updated_composite,
        "tier_before": old_tier,
        "tier_after": new_tier,
        "dimensions": dimensions,
        "timestamp": timestamp,
    }


def get_model_score(model_id: str, data_dir: str) -> Optional[Dict[str, Any]]:
    scores_path = os.path.join(data_dir, "llm.scores.json")
    if not os.path.exists(scores_path):
        return None
    with open(scores_path, "r", encoding="utf-8") as f:
        scores = json.load(f)
    return scores["models"].get(model_id)


def _score_from_status(status: str, latency_ms: int, min_lat: float) -> Dict[str, int]:
    """Calculate dimension scores based on connectivity test status.

    Status-aware scoring rules:
      - success:     latency-based score, all dimensions derived from latency
      - rate_limited: model is reachable but throttled. latency gets partial
                      credit (35) but reliability/stability are heavily penalized.
                      cost_efficiency gets 20 (free but unusable when throttled).
      - timeout:      model is too slow/unstable. all dimensions = 0.
      - auth_failed:  configuration issue. all dimensions = 0.
      - error:        model unavailable or provider error. all dimensions = 0.
    """
    if status == "success" and latency_ms > 0:
        raw = round(100 * min_lat / latency_ms)
        lat_score = max(10, min(100, raw))
        return {
            "latency": lat_score,
            "accuracy": lat_score,
            "tool_reliability": lat_score,
            "cost_efficiency": 80,
            "context_stability": lat_score,
        }

    if status == "rate_limited":
        # Model exists and is reachable, but provider throttles free tier.
        # Partial credit for reachability, heavy penalty for reliability.
        return {
            "latency": 35,
            "accuracy": 0,
            "tool_reliability": 15,
            "cost_efficiency": 20,
            "context_stability": 20,
        }

    if status == "timeout":
        return {
            "latency": 0,
            "accuracy": 0,
            "tool_reliability": 0,
            "cost_efficiency": 0,
            "context_stability": 0,
        }

    if status == "auth_failed":
        return {
            "latency": 0,
            "accuracy": 0,
            "tool_reliability": 0,
            "cost_efficiency": 0,
            "context_stability": 0,
        }

    # Default: error / unknown
    return {
        "latency": 0,
        "accuracy": 0,
        "tool_reliability": 0,
        "cost_efficiency": 0,
        "context_stability": 0,
    }


def score_from_batch_results(
    batch_results_path: str,
    registry_path: str,
    data_dir: str,
    min_latency_override: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate scores from batch connectivity test results.

    Reads f006_batch_results.json, maps each status to dimension scores,
    writes to llm.scores.json.
    """
    with open(batch_results_path, "r", encoding="utf-8") as f:
        batch = json.load(f)
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    free_ids = set(
        m["id"] for m in registry["models"]
        if m.get("pricing", {}).get("input_per_1m") == 0.0
        and m.get("pricing", {}).get("output_per_1m") == 0.0
    )

    success_lats = [
        r["latency_ms"] for r in batch
        if r["status"] == "success" and r["model_id"] in free_ids and r["latency_ms"] > 0
    ]
    min_lat = min_latency_override if min_latency_override else (min(success_lats) if success_lats else 1)

    scores_path = os.path.join(data_dir, "llm.scores.json")
    scores_data = {"models": {}, "meta": {"updated_at": ""}}
    if os.path.exists(scores_path):
        with open(scores_path, "r", encoding="utf-8") as f:
            scores_data = json.load(f)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated = 0

    for r in batch:
        mid = r["model_id"]
        if mid not in free_ids:
            continue

        status = r.get("status", "error")
        latency_ms = r.get("latency_ms", -1)
        dims = _score_from_status(status, latency_ms, min_lat)

        composite = round(sum(dims.values()) / len(dims), 1)
        tier = _determine_tier(composite, _load_mapping_config(data_dir))

        scores_data["models"][mid] = {
            "scores": [{"timestamp": now, "dimensions": dims, "composite": composite}],
            "current_composite": composite,
            "current_tier": tier,
            "history": [],
            "metadata": {
                "status": status,
                "latency_ms": latency_ms,
                "error_message": r.get("error_message", ""),
            },
        }
        updated += 1

    scores_data["meta"]["updated_at"] = now

    os.makedirs(data_dir, exist_ok=True)
    with open(scores_path, "w", encoding="utf-8") as f:
        json.dump(scores_data, f, indent=2, ensure_ascii=False)

    success_count = sum(
        1 for m in scores_data["models"].values()
        if m["metadata"]["status"] == "success"
    )
    rate_limited_count = sum(
        1 for m in scores_data["models"].values()
        if m["metadata"]["status"] == "rate_limited"
    )

    ranked = sorted(
        scores_data["models"].items(),
        key=lambda x: (-x[1]["current_composite"], x[1]["metadata"]["latency_ms"])
    )
    top = [
        [mid, data["current_composite"], data["metadata"]["latency_ms"], data["metadata"]["status"]]
        for mid, data in ranked[:5]
    ]

    return {
        "total": len(scores_data["models"]),
        "success": success_count,
        "rate_limited": rate_limited_count,
        "failed": len(scores_data["models"]) - success_count - rate_limited_count,
        "min_latency": min_lat,
        "scores_updated": updated,
        "top": top,
    }


def _print_leaderboard(data_dir: str, top_n: int = 20) -> None:
    scores_path = os.path.join(data_dir, "llm.scores.json")
    if not os.path.exists(scores_path):
        print(json.dumps({"error": "Scores file not found"}, ensure_ascii=False))
        return

    with open(scores_path, "r", encoding="utf-8") as f:
        scores = json.load(f)

    models = scores.get("models", {})
    if not models:
        print("No scores recorded.")
        return

    items = []
    for mid, data in models.items():
        meta = data.get("metadata", {})
        items.append({
            "model_id": mid,
            "composite": data.get("current_composite", 0),
            "tier": data.get("current_tier", "staff"),
            "samples": len(data.get("scores", [])),
            "status": meta.get("status", "unknown"),
        })

    items.sort(key=lambda x: (-x["composite"], x["model_id"]))
    items = items[:top_n]

    header = f"{'Rank':<6} {'Model ID':<45} {'Score':<8} {'Tier':<20} {'Status':<16} {'Samples':>8}"
    print(header)
    print("-" * len(header))
    for i, it in enumerate(items, 1):
        print(f"{i:<6} {it['model_id'][:44]:<45} {it['composite']:<8} "
              f"{it['tier']:<20} {it['status']:<16} {it['samples']:>8}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Scorer")
    parser.add_argument("data_dir", nargs="?", help="Path to assets directory")
    parser.add_argument("--batch", action="store_true", help="Batch mode from F-006 results")
    parser.add_argument("--leaderboard", type=int, nargs="?", const=20, metavar="N",
                        help="Print top-N leaderboard (default 20)")
    parser.add_argument("--min-latency", type=float, help="Override min latency for batch")

    args, unknown = parser.parse_known_args()

    if args.leaderboard is not None:
        if not args.data_dir:
            parser.error("--leaderboard requires data_dir")
        _print_leaderboard(args.data_dir, args.leaderboard)
        return

    if args.batch:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        batch_path = os.path.join(base, "data", "f006_batch_results.json")
        registry_path = os.path.join(base, "data", "llm.registry.json")
        data_dir = os.path.join(base, "data")
        result = score_from_batch_results(batch_path, registry_path, data_dir,
                                          min_latency_override=args.min_latency)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if not args.data_dir or not unknown:
        parser.print_help()
        sys.exit(1)

    model_id = unknown[0]
    dimensions = {}
    for arg in unknown[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            dimensions[k] = int(v)

    result = update_score(model_id, dimensions, args.data_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
