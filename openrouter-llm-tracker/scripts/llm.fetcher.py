"""
---
title: "llm.fetcher.py"
name: "openrouter-llm-tracker"
description: "F-001: Fetch latest model list from OpenRouter API. Determine LLM type, reasoning level, and assignment tier from description and metadata."
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
  local_path: "{baseDir}/scripts/llm.fetcher.py"
  github_path: "openrouter-llm-tracker/scripts/llm.fetcher.py"
---
"""
# openrouter-llm-tracker/scripts/llm.fetcher.py
# F-001: Fetch latest model list from OpenRouter API

import json
import os
import time
import urllib.request
import urllib.error
from typing import Dict, List, Any
from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

OPENROUTER_MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models"

# LLM Type Enum keywords (fixed in script)
LLM_TYPE_KEYWORDS = {
    "coding": ["code", "coding", "programming", "software engineering", "swe-bench", "developer", "programmer"],
    "ocr": ["ocr", "optical character recognition", "text recognition"],
    "vision": ["vision", "visual", "image understanding", "image input", "image reasoning"],
    "multimodal": ["multimodal", "text, image, video", "text and image", "video understanding", "audio input"],
    "reasoning": ["reasoning", "thinking", "chain-of-thought", "cot", "deep reasoning", "logical reasoning"],
    "agentic": ["agent", "agentic", "tool use", "function calling", "workflow", "autonomous"],
    "audio": ["audio", "speech", "tts", "stt", "voice", "text-to-speech", "speech-to-text"],
    "general": [],
}

# Vendor display name mapping (fixed in script)
VENDOR_KEY_MAP = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "deepseek": "DeepSeek",
    "qwen": "Alibaba",
    "alibaba": "Alibaba",
    "baidu": "Baidu",
    "tencent": "Tencent",
    "google": "Google",
    "nvidia": "NVIDIA",
    "meta-llama": "Meta",
    "meta": "Meta",
    "minimax": "MiniMax",
    "z-ai": "Z.AI",
    "moonshot": "Moonshot",
    "xiaomi": "Xiaomi",
    "stepfun": "StepFun",
    "poolside": "Poolside",
    "inclusionai": "inclusionAI",
    "liquid": "LiquidAI",
    "nousresearch": "NousResearch",
    "cognitivecomputations": "CognitiveComputations",
    "openrouter": "OpenRouter",
}

# Vendor region mapping (fixed in script)
VENDOR_REGION_MAP = {
    "OpenAI": "United States",
    "Anthropic": "United States",
    "DeepSeek": "China",
    "Alibaba": "China",
    "Baidu": "China",
    "Tencent": "China",
    "Google": "United States",
    "NVIDIA": "United States",
    "Meta": "United States",
    "MiniMax": "China",
    "Z.AI": "China",
    "Moonshot": "China",
    "Xiaomi": "China",
    "StepFun": "China",
    "Poolside": "Europe",
    "inclusionAI": "Unknown",
    "LiquidAI": "United States",
    "NousResearch": "United States",
    "CognitiveComputations": "United States",
    "OpenRouter": "United States",
}

# Assignment tier defaults by vendor (fixed in script, overridable by references/MAPPING.md)
VENDOR_TIER_DEFAULTS = {
    "OpenAI": "c_level",
    "Anthropic": "c_level",
    "DeepSeek": "domain_expert",
    "Alibaba": "domain_expert",
    "Baidu": "domain_expert",
    "Tencent": "staff",
    "Google": "domain_expert",
    "NVIDIA": "domain_expert",
    "Meta": "supervisor",
    "MiniMax": "domain_expert",
    "Z.AI": "domain_expert",
    "Moonshot": "c_level",
    "Xiaomi": "domain_expert",
    "StepFun": "domain_expert",
    "Poolside": "domain_expert",
    "inclusionAI": "domain_expert",
    "LiquidAI": "staff",
    "NousResearch": "supervisor",
    "CognitiveComputations": "staff",
    "OpenRouter": "domain_expert",
}


def _determine_llm_type(description: str, capabilities: Dict) -> str:
    """Determine LLM type from description keywords and capabilities."""
    if not description:
        desc_lower = ""
    else:
        desc_lower = description.lower()

    for llm_type, keywords in LLM_TYPE_KEYWORDS.items():
        if llm_type == "general":
            continue
        for kw in keywords:
            if kw.lower() in desc_lower:
                if llm_type == "vision" and not capabilities.get("vision", False):
                    continue
                return llm_type
    return "general"


def _determine_reasoning(description: str, model_data: Dict) -> str:
    """Determine reasoning level from description and metadata."""
    if not description:
        desc_lower = ""
    else:
        desc_lower = description.lower()

    if "adaptive reasoning" in desc_lower or "adaptive thinking" in desc_lower:
        return "adaptive"
    if "configurable reasoning" in desc_lower or "reasoning level" in desc_lower:
        return "adaptive"
    if "always-on chain of thought" in desc_lower or "always-on cot" in desc_lower:
        return "high"
    if "deep reasoning" in desc_lower or "high reasoning" in desc_lower:
        return "high"
    if "thinking mode" in desc_lower or "reasoning mode" in desc_lower:
        return "high"
    if "reasoning" in desc_lower or "thinking" in desc_lower or "chain-of-thought" in desc_lower:
        return "medium"

    # Check architecture metadata
    arch = model_data.get("architecture", {})
    if arch.get("instruct_type") == "reasoning":
        return "medium"

    return "false"


def _determine_assignment_tier(vendor: str, llm_type: str, reasoning: str, context_length: int, pricing: Dict) -> str:
    """Determine assignment tier based on vendor defaults and override rules."""
    tier = VENDOR_TIER_DEFAULTS.get(vendor, "domain_expert")

    # Override rule: OCR-only or audio-only -> staff
    if llm_type in ("ocr", "audio"):
        return "staff"

    # Override rule: Preview/experimental models -> staff max
    # (Cannot detect from API alone, rely on manual registry edits)

    return tier


def fetch_models(api_key: str) -> List[Dict[str, Any]]:
    """Fetch model list from OpenRouter API and return structured metadata.

    Args:
        api_key: OpenRouter API Key (required string)

    Returns:
        List of model dicts conforming to schema in LLM/SKILL.md section 2.

    Raises:
        ConnectionError: On network failure or API error.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        if HAS_REQUESTS:
            resp = requests.get(OPENROUTER_MODELS_ENDPOINT, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        else:
            req = urllib.request.Request(OPENROUTER_MODELS_ENDPOINT, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        raise ConnectionError(f"Failed to fetch models from OpenRouter: {e}")

    raw_models = data.get("data", [])
    models = []

    for m in raw_models:
        model_id = m.get("id", "")
        name = m.get("name", "")
        description = m.get("description", "")
        created_ts = m.get("created", 0)

        # Strip leading "~" from model_id (OpenRouter uses ~ for latest aliases)
        clean_id = model_id.lstrip("~")

        # Extract vendor from model_id namespace
        vendor = "Unknown"
        if "/" in clean_id:
            vendor_key = clean_id.split("/")[0]
            vendor = VENDOR_KEY_MAP.get(vendor_key.lower(), vendor_key.capitalize())

        # Determine capabilities from description and metadata
        capabilities = {
            "tools": False,
            "vision": False,
        }
        desc_lower = description.lower() if description else ""
        if "tool" in desc_lower or "function calling" in desc_lower or "agent" in desc_lower:
            capabilities["tools"] = True
        if "image" in desc_lower or "vision" in desc_lower or "multimodal" in desc_lower or "ocr" in desc_lower or "video" in desc_lower:
            capabilities["vision"] = True

        # Also check architecture metadata
        arch = m.get("architecture", {})
        if arch.get("instruct_type") == "tool_use":
            capabilities["tools"] = True
        if arch.get("modality") in ("text+image", "text+image+audio", "multimodal"):
            capabilities["vision"] = True

        # Pricing (OpenRouter returns per-token as string, convert to per-1M)
        pricing = m.get("pricing", {})
        try:
            input_price = float(pricing.get("prompt", 0) or 0) * 1000000
        except (ValueError, TypeError):
            input_price = 0.0
        try:
            output_price = float(pricing.get("completion", 0) or 0) * 1000000
        except (ValueError, TypeError):
            output_price = 0.0

        context_length = m.get("context_length", 0) or 0

        # Max output tokens from top_provider
        top_provider = m.get("top_provider", {})
        max_output = top_provider.get("max_completion_tokens", 0) or 0

        llm_type = _determine_llm_type(description, capabilities)
        reasoning = _determine_reasoning(description, m)

        tier = _determine_assignment_tier(
            vendor, llm_type, reasoning, context_length,
            {"input_per_1m": input_price, "output_per_1m": output_price}
        )

        model_record = {
            "id": clean_id,
            "name": name,
            "name_zh": "",
            "vendor": vendor,
            "region": VENDOR_REGION_MAP.get(vendor, "Unknown"),
            "llm_type": llm_type,
            "assignment_tier": tier,
            "release_date": "",
            "created": created_ts,
            "pricing": {
                "input_per_1m": round(input_price, 4),
                "output_per_1m": round(output_price, 4),
            },
            "context": {
                "max_input": context_length,
                "max_output": max_output,
            },
            "capabilities": {
                "tools": capabilities["tools"],
                "vision": capabilities["vision"],
                "reasoning": reasoning,
            },
        }
        models.append(model_record)

    return models


def fetch_models_delta(api_key: str, registry_path: str, days: int = 14) -> Dict[str, Any]:
    """Fetch models and return a change log of models created/modified in the last N days.

    Compares the freshly fetched model list against the local registry file.
    Returns every model within the N-day window with a _status tag.

    Args:
        api_key: OpenRouter API Key
        registry_path: Path to the local llm.registry.json
        days: Lookback window in days (default: 14)

    Returns:
        Dict with keys:
          - 'changes': list of models in the window, each with an extra '_status' key
                        ('new' | 'updated' | 'unchanged')
          - 'summary': { 'total_fetched', 'in_window', 'new', 'updated', 'unchanged', 'cutoff_date' }
    """
    import time
    from datetime import datetime, timezone

    # Fetch all models
    all_models = fetch_models(api_key)

    # Load existing registry
    existing = {"models": []}
    if os.path.exists(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {"models": []}

    existing_map = {m["id"]: m for m in existing.get("models", [])}

    # Cutoff: N days ago as unix timestamp
    cutoff_ts = int(time.time()) - (days * 24 * 60 * 60)
    cutoff_date = datetime.fromtimestamp(cutoff_ts, tz=timezone.utc).strftime("%Y-%m-%d")

    FIELDS_TO_CHECK = ["name", "description", "pricing", "context", "capabilities", "architecture"]

    changes = []
    count_new = 0
    count_updated = 0
    count_unchanged = 0

    for model in all_models:
        created_ts = model.get("created", 0)

        # Skip if model was created before the cutoff
        if created_ts and created_ts < cutoff_ts:
            continue

        model_id = model["id"]
        entry = dict(model)  # shallow copy so we can add _status

        if model_id not in existing_map:
            entry["_status"] = "new"
            count_new += 1
        else:
            old = existing_map[model_id]
            is_changed = any(old.get(f) != model.get(f) for f in FIELDS_TO_CHECK)
            entry["_status"] = "updated" if is_changed else "unchanged"
            if is_changed:
                count_updated += 1
            else:
                count_unchanged += 1

        changes.append(entry)

    # Sort: newest first
    changes.sort(key=lambda m: m.get("created", 0), reverse=True)

    return {
        "changes": changes,
        "summary": {
            "total_fetched": len(all_models),
            "in_window": len(changes),
            "new": count_new,
            "updated": count_updated,
            "unchanged": count_unchanged,
            "cutoff_date": cutoff_date,
            "cutoff_ts": cutoff_ts,
        },
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python llm.fetcher.py <API_KEY> [registry_path] [days]")
        print("  API_KEY: OpenRouter API key (empty string for no auth)")
        print("  registry_path: path to llm.registry.json (default: ../data/llm.registry.json)")
        print("  days: lookback window in days (default: 14)")
        sys.exit(1)

    api_key = sys.argv[1]
    registry_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "llm.registry.json"
    )
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 14

    result = fetch_models_delta(api_key, registry_path, days)
    print(json.dumps(result, indent=2, ensure_ascii=False))