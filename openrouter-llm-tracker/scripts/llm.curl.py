"""
---
title: "llm.curl.py"
name: "openrouter-llm-tracker"
description: "F-006: API connectivity test and model setting validation. Test OpenRouter platform connection, verify API key and model configuration."
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
  local_path: "{baseDir}/scripts/llm.curl.py"
  github_path: "openrouter-llm-tracker/scripts/llm.curl.py"
---
"""
# openrouter-llm-tracker/scripts/llm.curl.py
# F-006 / S-004: API connectivity test

import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.error
from typing import Dict, Any, List

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

OPENROUTER_CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def test_model_connectivity(api_key: str, model_id: str,
                            test_prompt: str = "Say hello in one sentence.",
                            max_tokens: int = 64,
                            timeout_seconds: int = 30) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://openrouter.ai/",
    }
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": test_prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    start_time = time.monotonic()
    latency_ms = -1
    result: Dict[str, Any] = {
        "status": "error",
        "model_id": model_id,
        "latency_ms": -1,
        "response": "",
        "error_message": "",
        "input_tokens": None,
        "output_tokens": None,
    }

    try:
        if HAS_REQUESTS:
            resp = requests.post(
                OPENROUTER_CHAT_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=timeout_seconds,
            )
            latency_ms = round((time.monotonic() - start_time) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                result["status"] = "success"
                result["latency_ms"] = latency_ms
                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    result["response"] = msg.get("content", "")
                usage = data.get("usage", {})
                result["input_tokens"] = usage.get("prompt_tokens")
                result["output_tokens"] = usage.get("completion_tokens")
            elif resp.status_code == 401:
                result["status"] = "auth_failed"
                result["error_message"] = "HTTP 401 Unauthorized"
                result["latency_ms"] = latency_ms
            elif resp.status_code == 429:
                result["status"] = "rate_limited"
                result["error_message"] = "HTTP 429 Rate Limited"
                result["latency_ms"] = latency_ms
            else:
                result["status"] = "error"
                result["error_message"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
                result["latency_ms"] = latency_ms
        else:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                OPENROUTER_CHAT_ENDPOINT,
                data=data_bytes,
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                latency_ms = round((time.monotonic() - start_time) * 1000)
                body = json.loads(resp.read().decode("utf-8"))
                result["status"] = "success"
                result["latency_ms"] = latency_ms
                choices = body.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    result["response"] = msg.get("content", "")
                usage = body.get("usage", {})
                result["input_tokens"] = usage.get("prompt_tokens")
                result["output_tokens"] = usage.get("completion_tokens")

    except urllib.error.HTTPError as e:
        latency_ms = round((time.monotonic() - start_time) * 1000)
        result["latency_ms"] = latency_ms
        if e.code == 401:
            result["status"] = "auth_failed"
            result["error_message"] = "HTTP 401 Unauthorized"
        elif e.code == 429:
            result["status"] = "rate_limited"
            result["error_message"] = "HTTP 429 Rate Limited"
        else:
            result["status"] = "error"
            result["error_message"] = f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:500]}"

    except urllib.error.URLError as e:
        latency_ms = round((time.monotonic() - start_time) * 1000)
        result["latency_ms"] = latency_ms
        if isinstance(e.reason, TimeoutError):
            result["status"] = "timeout"
            result["error_message"] = f"Request timed out after {timeout_seconds}s"
        else:
            result["status"] = "error"
            result["error_message"] = f"URL Error: {e.reason}"

    except TimeoutError:
        result["status"] = "timeout"
        result["error_message"] = f"Request timed out after {timeout_seconds}s"

    except Exception as e:
        latency_ms = round((time.monotonic() - start_time) * 1000)
        result["latency_ms"] = latency_ms
        result["status"] = "error"
        result["error_message"] = f"{type(e).__name__}: {e}"

    return result


def test_batch_connectivity(api_key: str, model_ids: List[str],
                            test_prompt: str = "Say hello in one sentence.",
                            max_tokens: int = 64,
                            timeout_seconds: int = 30,
                            delay_ms: int = 500) -> List[Dict[str, Any]]:
    results = []
    for mid in model_ids:
        r = test_model_connectivity(api_key, mid, test_prompt, max_tokens, timeout_seconds)
        results.append(r)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
    return results


def test_registry_models(api_key: str, registry_path: str,
                         free_only: bool = False,
                         max_tokens: int = 64,
                         timeout_seconds: int = 30,
                         delay_ms: int = 500) -> List[Dict[str, Any]]:
    if not os.path.exists(registry_path):
        return [{"status": "error", "error_message": f"Registry not found: {registry_path}", "model_id": ""}]

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    models = registry.get("models", [])
    if not models:
        return [{"status": "error", "error_message": "No models in registry", "model_id": ""}]

    if free_only:
        models = [m for m in models
                  if m.get("pricing", {}).get("input_per_1m") == 0.0
                  and m.get("pricing", {}).get("output_per_1m") == 0.0]

    model_ids = [m["id"] for m in models]
    return test_batch_connectivity(api_key, model_ids, max_tokens=max_tokens,
                                   timeout_seconds=timeout_seconds, delay_ms=delay_ms)


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Connectivity Test")
    parser.add_argument("api_key", nargs="?", help="OpenRouter API key")
    parser.add_argument("model_id", nargs="?", default="openai/gpt-4o", help="Model to test")
    parser.add_argument("test_prompt", nargs="?", default="Say hello in one sentence.")
    parser.add_argument("max_tokens", nargs="?", type=int, default=64)
    parser.add_argument("--registry-test", action="store_true",
                        help="Test all models in registry (api_key required as first arg)")
    parser.add_argument("--free-only", action="store_true",
                        help="Only test free models (with --registry-test)")
    parser.add_argument("--output", help="Write batch results to JSON file")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per request")
    parser.add_argument("--delay", type=int, default=500, help="Delay between requests (ms)")

    args = parser.parse_args()

    if args.registry_test:
        if not args.api_key:
            parser.error("--registry-test requires api_key as first positional argument")
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        registry_path = os.path.join(base, "data", "llm.registry.json")
        results = test_registry_models(
            args.api_key, registry_path,
            free_only=args.free_only,
            timeout_seconds=args.timeout,
            delay_ms=args.delay,
        )
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Results written to: {args.output}")
        else:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    if not args.api_key:
        parser.print_help()
        sys.exit(1)

    result = test_model_connectivity(
        args.api_key, args.model_id, args.test_prompt,
        args.max_tokens, args.timeout,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
