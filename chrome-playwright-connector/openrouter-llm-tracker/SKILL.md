---
skill_id: "openrouter.llm.tracker"
skill_bundle: "openrouter-llm-tracker"
version: "1.2.1"
author: "Kevin Lin"
description: "Agent execution instructions for OpenRouter LLM Tracker. Fetch model registry, score models, test connectivity, generate official-format configs for OpenClaw and WorkBuddy, and smart-merge into existing agent configs."
language: "zh-HK"
---

# OpenRouter LLM Tracker — Agent Execution Instructions

## 0. Activation Rule

When receiving a task related to OpenRouter model management, registry maintenance, scoring, connectivity testing, config generation, config merging, or registry querying, execute the following steps in order. Do not skip steps. Do not assume. If a required parameter is missing, ask the user before proceeding.

## 1. Skill Scope

This skill manages the lifecycle of LLM models available on OpenRouter:

| Step | Action | Script | Output |
|------|--------|--------|--------|
| S-001 | Fetch model list + Delta change log (last N days) | scripts/llm.fetcher.py | Python dict list |
| S-002 | Save registry and daily snapshot | scripts/llm.registry.py | JSON files in assets/ |
| S-003 | Update model scores and assignment tiers | scripts/llm.scorer.py | JSON file in assets/ |
| S-004 | Test API connectivity for a model | scripts/llm.curl.py | Python dict |
| S-005 | Generate or merge OpenClaw config (official format) | scripts/llm.config.openclaw.py | JSON string / file write |
| S-006 | Generate or merge WorkBuddy config (official format) | scripts/llm.config.workbuddy.py | JSON string / file write |
| S-007 | Query registry (list, filter, search, count) | scripts/llm.registry.py CLI | Printed table / JSON |
| S-008 | View score leaderboard | scripts/llm.scorer.py CLI | Printed table |
| S-009 | Batch test registry models | scripts/llm.curl.py CLI | JSON list |

## 2. Data Schema

All model records follow this exact schema. Fields must not be invented or omitted.

| Field | JSON Path | Type | Required | Source |
|-------|-----------|------|----------|--------|
| id | models.id / agents.models.key | string | Yes | OpenRouter API model id |
| name | models.name / models.alias | string | Yes | OpenRouter API name |
| name_zh | models.name_zh | string | No | Manual or translated |
| vendor | models.vendor | string | Yes | OpenRouter API provider name |
| region | models.region | string | No | Manual mapping (references/vendor_regions.json) |
| llm_type | models.llm_type | enum | Yes | Derived from capabilities |
| assignment_tier | models.assignment_tier | enum | Yes | Derived from references/MAPPING.md rules |
| release_date | models.release_date | string | No | OpenRouter changelog or manual |
| pricing.input_per_1m | models.pricing.input_per_1m | number | Yes | OpenRouter API pricing |
| pricing.output_per_1m | models.pricing.output_per_1m | number | Yes | OpenRouter API pricing |
| context.max_input | models.context.max_input | integer | Yes | OpenRouter API context length |
| context.max_output | models.context.max_output | integer | Yes | OpenRouter API or freellm.net |
| capabilities.tools | models.capabilities.tools | boolean | Yes | OpenRouter API features |
| capabilities.vision | models.capabilities.vision | boolean | Yes | OpenRouter API features |
| capabilities.reasoning | models.capabilities.reasoning | enum | Yes | OpenRouter API or manual |

### 2.1 LLM Type Enum (fixed in scripts)

general / coding / ocr / vision / multimodal / reasoning / agentic / audio

### 2.2 Reasoning Level Enum (fixed in scripts)

false / low / medium / high / adaptive

### 2.3 Assignment Tier Enum (defined in references/MAPPING.md)

Main Agent: omnipotent / c_level / specialist_manager / strategic_expert
Sub Agent: domain_expert / supervisor / staff

## 3. Execution Steps

### 3.1 S-001: Fetch Model List

1. Accept api_key as mandatory string parameter from caller.
2. Call OpenRouter API: GET https://openrouter.ai/api/v1/models
3. Parse response. Extract fields per schema in section 2.
4. For each model, determine llm_type by checking model description keywords:
   - Contains "code", "coding", "programming" -> coding
   - Contains "ocr", "vision", "multimodal", "image", "video" -> check vision flag
   - Contains "reasoning", "thinking", "chain-of-thought" -> reasoning
   - Contains "agent", "agentic", "tool" -> agentic
   - Contains "audio", "speech", "tts", "stt" -> audio
   - Default -> general
5. For each model, determine assignment_tier by applying rules from references/MAPPING.md. If MAPPING.md is not yet populated, default to domain_expert for all models.
6. Return list of dicts.

### 3.2 S-002: Save Registry

1. Accept models list from S-001 and assets_dir path.
2. Write llm.registry.json to assets_dir with structure: {"models": [...], "meta": {"updated_at": "ISO-8601", "count": N}}
3. Write daily snapshot to assets/llm.history/YYYY-MM-DD.json with identical structure.
4. If file already exists for today, overwrite.

### 3.3 S-003: Update Scores

1. Accept model_id, dimensions dict, and assets_dir.
2. dimensions dict keys must be one of: latency / accuracy / tool_reliability / cost_efficiency / context_stability. Values are 0-100 integers.
3. Load llm.scores.json from assets_dir.
4. Calculate weighted average using weights from references/RANKING.md. If RANKING.md is not yet populated, use equal weights (0.2 each).
5. Update model score record. Append to history array with timestamp.
6. Check if score crosses assignment tier thresholds from MAPPING.md. If yes, update assignment_tier and log the change.
7. Write updated llm.scores.json back to assets_dir.

### 3.4 S-004: Test Connectivity

1. Accept api_key (mandatory string), model_id (mandatory string), optional test_prompt / max_tokens / timeout_seconds.
2. Call scripts/llm.curl.py test_model_connectivity().
3. Return result dict directly to caller. Do not modify or filter the dict.
4. If status is not "success", include the full error_message in the response to caller.

### 3.5 S-005: Generate or Merge OpenClaw Config (Official Format)

Output format matches OpenClaw official schema:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "nvidia/nemotron-3-nano-30b-a3b:free",
        "fallbacks": ["arcee-ai/trinity-large-thinking:free", "..."]
      },
      "models": {
        "nvidia/nemotron-3-nano-30b-a3b:free": {"alias": "Nemotron 3 Nano 30B A3B (free)"},
        "arcee-ai/trinity-large-thinking:free": {"alias": "Trinity Large Thinking (free)"}
      }
    }
  },
  "env": {
    "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}"
  }
}
```

Notes:
- agents.defaults.model.primary is the Top-1 scored model.
- agents.defaults.model.fallbacks is an array of remaining model IDs.
- agents.defaults.models is a map: model_id -> { alias: display_name }.
- env.OPENROUTER_API_KEY uses placeholder ${OPENROUTER_API_KEY}.
- The actual API key should be set in the .env file at skill root or in the agent's environment.

#### 3.5.1 Single Model Mode

1. Accept --model-id (model ID string), --param-type (profile string), --registry (optional).
2. Load registry. Find model by id.
3. If model not found, return error string: {"error": "Model ID not found in registry"}
4. Generate JSON string matching OpenClaw official schema.
5. Return JSON string. Do not write to file.

CLI: `python scripts/llm.config.openclaw.py --model-id <model_id> [--param-type agentic]`

#### 3.5.2 Standalone Batch Top-N Mode

For generating a new standalone config with top-N scored models, use CLI. Do NOT write new scripts.

| Task | CLI Command |
|------|-------------|
| Top 10 scored models | `python scripts/llm.config.openclaw.py --param-type agentic` |
| Top N models | `python scripts/llm.config.openclaw.py --param-type agentic --top N` |
| Free only | `python scripts/llm.config.openclaw.py --param-type agentic --free-only --top 10` |
| Write to file | `python scripts/llm.config.openclaw.py --param-type agentic --output openclaw.config.json` |

#### 3.5.3 Smart-Merge Mode (Recommended for Production)

Merge top-N scored models into the existing OpenClaw agent config. The script handles backup, replacement, and routing auto-update.

**Official default path**: ~/.openclaw/config.json (cross-platform). If this file does not exist, the script errors and stops. Use --merge-into with a custom path, or create the default path first.

**--merge-into syntax**:
- --merge-into alone: uses default path ~/.openclaw/config.json
- --merge-into "custom/path": uses the specified path

**Recommended workflow (always dry-run first)**:

| Step | CLI Command | Purpose |
|------|-------------|---------|
| 1. Preview | `python scripts/llm.config.openclaw.py --merge-into --dry-run` | Show merged result at default path without writing |
| 2. Confirm | (Wait for user approval) | Ensure user reviews the preview |
| 3. Execute | `python scripts/llm.config.openclaw.py --merge-into` | Actual merge at default path with backup |

**Full CLI for merge mode**:

| Task | CLI Command |
|------|-------------|
| Dry-run at default path | `python scripts/llm.config.openclaw.py --merge-into --dry-run` |
| Dry-run at custom path | `python scripts/llm.config.openclaw.py --merge-into "C:/path/config.json" --dry-run` |
| Actual merge at default path | `python scripts/llm.config.openclaw.py --merge-into` |
| Actual merge at custom path | `python scripts/llm.config.openclaw.py --merge-into "C:/path/config.json"` |
| Free only merge | `python scripts/llm.config.openclaw.py --merge-into --free-only` |
| Top 5 merge | `python scripts/llm.config.openclaw.py --merge-into --top 5` |

**Merge behavior**:
- If target_path.backup exists, it is removed first.
- Current config is copied to target_path.backup.
- agents.defaults.model.primary is replaced with Top-1 model ID.
- agents.defaults.model.fallbacks is replaced with remaining model IDs.
- agents.defaults.models map is replaced with new aliases.
- env.OPENROUTER_API_KEY is ensured to exist (set to ${OPENROUTER_API_KEY} if missing).
- All other fields are preserved unchanged.

### 3.6 S-006: Generate or Merge WorkBuddy Config (~/.workbuddy/models.json format)

Output format matches ACTUAL ~/.workbuddy/models.json schema (workbuddy.models[].key / display_name / supports_tools / supports_vision / ...):

```json
{
  "workbuddy": {
    "models": [
      {
        "key": "nvidia/nemotron-3-nano-30b-a3b:free",
        "display_name": "NVIDIA: Nemotron 3 Nano 30B A3B (free)",
        "vendor": "NVIDIA",
        "region": "United States",
        "type": "coding",
        "tier": "omnipotent",
        "context_window": 256000,
        "max_output_tokens": 0,
        "supports_tools": true,
        "supports_vision": false,
        "reasoning_level": "false",
        "pricing": {
          "input_per_1m": 0.0,
          "output_per_1m": 0.0
        },
        "release_date": "",
        "runtime_params": {
          "temperature": 0.3,
          "top_p": 0.95,
          "presence_penalty": 0.1,
          "frequency_penalty": 0.1
        }
      }
    ],
    "routing": {
      "enabled": true,
      "primary_model": "nvidia/nemotron-3-nano-30b-a3b:free",
      "fallback_models": [],
      "max_retries": 3,
      "timeout_seconds": 30,
      "retry_delay_ms": 500
    },
    "meta": {
      "generated_at": "2026-05-14T16:00:00Z",
      "source": "openrouter-llm-tracker",
      "count": 1
    }
  }
}
```

Notes:
- "key" (not "id") is the model identifier used by WorkBuddy.
- "supports_tools" / "supports_vision" (snake_case, not camelCase).
- "context_window" / "max_output_tokens" match models.json field names.
- routing.primary_model and routing.fallback_models are auto-updated.
- apiKey is referenced via ${OPENROUTER_API_KEY} in the environment, not embedded in models.json.

#### 3.6.1 Single Model Mode

1. Accept --model-id (model ID string), --param-type (profile string), --registry (optional).
2. Load registry. Find model by id.
3. If model not found, return error string: {"error": "Model ID not found in registry"}
4. Generate JSON string matching ~/.workbuddy/models.json format.
5. Return JSON string. Do not write to file.

CLI: `python scripts/llm.config.workbuddy.py --model-id <model_id> [--param-type agentic]`

#### 3.6.2 Standalone Batch Top-N Mode

For generating a new standalone config with top-N scored models, use CLI. Do NOT write new scripts.

| Task | CLI Command |
|------|-------------|
| Top 10 scored models | `python scripts/llm.config.workbuddy.py --param-type agentic` |
| Top N models | `python scripts/llm.config.workbuddy.py --param-type agentic --top N` |
| Free only | `python scripts/llm.config.workbuddy.py --param-type agentic --free-only --top 10` |
| Write to file | `python scripts/llm.config.workbuddy.py --param-type agentic --output workbuddy.config.json` |

#### 3.6.3 Smart-Merge Mode (Recommended for Production)

Merge top-N scored models into the existing ~/.workbuddy/models.json. The script handles backup, replacement, and routing auto-update.

**Official default path**: ~/.workbuddy/models.json (cross-platform). If this file does not exist, the script errors and stops. Use --merge-into with a custom path, or create the default path first.

**--merge-into syntax**:
- --merge-into alone: uses default path ~/.workbuddy/models.json
- --merge-into "custom/path": uses the specified path

**Recommended workflow (always dry-run first)**:

| Step | CLI Command | Purpose |
|------|-------------|---------|
| 1. Preview | `python scripts/llm.config.workbuddy.py --merge-into --dry-run` | Show merged result at default path without writing |
| 2. Confirm | (Wait for user approval) | Ensure user reviews the preview |
| 3. Execute | `python scripts/llm.config.workbuddy.py --merge-into` | Actual merge at default path with backup |

**Full CLI for merge mode**:

| Task | CLI Command |
|------|-------------|
| Dry-run at default path | `python scripts/llm.config.workbuddy.py --merge-into --dry-run` |
| Dry-run at custom path | `python scripts/llm.config.workbuddy.py --merge-into "C:/path/models.json" --dry-run` |
| Actual merge at default path | `python scripts/llm.config.workbuddy.py --merge-into` |
| Actual merge at custom path | `python scripts/llm.config.workbuddy.py --merge-into "C:/path/models.json"` |
| Free only merge | `python scripts/llm.config.workbuddy.py --merge-into --free-only` |
| Top 5 merge | `python scripts/llm.config.workbuddy.py --merge-into --top 5` |

**Merge behavior**:
- If target_path.backup exists, it is removed first.
- Current config is copied to target_path.backup.
- workbuddy.models is replaced entirely with the new top-N model entries.
- workbuddy.routing.primary_model is replaced with Top-1 model key.
- workbuddy.routing.fallback_models is replaced with remaining model keys.
- workbuddy.meta is updated (generated_at, source, count).
- All other fields are preserved unchanged.

### 3.7 Environment Setup (.env)

The skill root directory contains a .env template file:

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Copy this file to .env and replace the placeholder with your actual OpenRouter API key. Both OpenClaw and WorkBuddy configs reference this key via ${OPENROUTER_API_KEY}.

### 3.8 S-007: Query Registry (CLI Mode — No Script Writing)

For all query tasks, use the built-in CLI of llm.registry.py. Do NOT write new scripts.

| Task | CLI Command | Example |
|------|-------------|---------|
| List all models | python scripts/llm.registry.py "<assets_dir>" --list | python scripts/llm.registry.py "openrouter-llm-tracker/assets" --list |
| List free models only | python scripts/llm.registry.py "<assets_dir>" --free-only | python scripts/llm.registry.py "openrouter-llm-tracker/assets" --free-only |
| Filter by tier | python scripts/llm.registry.py "<assets_dir>" --filter-tier <tier> | python scripts/llm.registry.py "openrouter-llm-tracker/assets" --filter-tier domain_expert |
| Filter by type | python scripts/llm.registry.py "<assets_dir>" --filter-type <type> | python scripts/llm.registry.py "openrouter-llm-tracker/assets" --filter-type coding |
| Search by keyword | python scripts/llm.registry.py "<assets_dir>" --search <keyword> | python scripts/llm.registry.py "openrouter-llm-tracker/assets" --search gemini |
| Get single model | python scripts/llm.registry.py "<assets_dir>" --get <model_id> | python scripts/llm.registry.py "openrouter-llm-tracker/assets" --get openai/gpt-4o |
| Show statistics | python scripts/llm.registry.py "<assets_dir>" --count | python scripts/llm.registry.py "openrouter-llm-tracker/assets" --count |
| Load snapshot | python scripts/llm.registry.py "<assets_dir>" --snapshot YYYY-MM-DD | python scripts/llm.registry.py "openrouter-llm-tracker/assets" --snapshot 2026-05-11 --list |

Notes:
- Wrap assets_dir in quotes if path contains spaces.
- Combine flags: --free-only --filter-type coding is valid.

### 3.9 S-008: View Leaderboard (CLI Mode — No Script Writing)

| Task | CLI Command | Example |
|------|-------------|---------|
| Top 20 leaderboard | python scripts/llm.scorer.py "<assets_dir>" --leaderboard | python scripts/llm.scorer.py "openrouter-llm-tracker/assets" --leaderboard |
| Top N leaderboard | python scripts/llm.scorer.py "<assets_dir>" --leaderboard N | python scripts/llm.scorer.py "openrouter-llm-tracker/assets" --leaderboard 10 |

### 3.10 S-009: Batch Test Registry Models (CLI Mode — No Script Writing)

| Task | CLI Command | Example |
|------|-------------|---------|
| Test all models | python scripts/llm.curl.py "<api_key>" --registry-test | python scripts/llm.curl.py "sk-or-v1-xxx" --registry-test |
| Test free models only | python scripts/llm.curl.py "<api_key>" --registry-test --free-only | python scripts/llm.curl.py "sk-or-v1-xxx" --registry-test --free-only |
| Write results to file | python scripts/llm.curl.py "<api_key>" --registry-test --free-only --output <path> | python scripts/llm.curl.py "sk-or-v1-xxx" --registry-test --free-only --output results.json |

Notes:
- api_key must be the first positional argument when using --registry-test.
- --output writes JSON array for consumption by llm.scorer.py --batch.
- --timeout and --delay are optional (default 30s, 500ms).

## 4. Error Handling

| Error | Action |
|-------|--------|
| Missing api_key | Ask user to provide api_key string before any API call |
| Missing model_id | Ask user to provide model_id before registry/config lookup |
| Model not in registry | Return error JSON string, do not guess or hallucinate model data |
| API timeout | Mark status as "timeout", include latency_ms = -1, return full dict |
| Rate limited | Mark status as "rate_limited", advise user to wait or check tier |
| Auth failed | Mark status as "auth_failed", advise user to verify API key |
| Registry file missing | Return error dict with message "Registry file not found: {path}" |
| references/MAPPING.md missing | Use default assignment_tier = domain_expert, log warning |
| references/RANKING.md missing | Use equal weights 0.2 each, log warning |
| OpenClaw config not found at official path | Error and stop. Advise user to create ~/.openclaw/config.json first, or use --merge-into with custom path |
| WorkBuddy config not found at official path | Error and stop. Advise user to create ~/.workbuddy/config.json first, or use --merge-into with custom path |

## 5. Output Rules

1. All JSON outputs must be valid JSON. No trailing commas. No comments inside JSON.
2. All string outputs to caller must be raw JSON strings, not Python repr.
3. File writes (S-002, S-003, S-005 merge, S-006 merge) use UTF-8 encoding, pretty-printed with indent=2.
4. Do not expose memory_id or internal file paths to user.
5. Do not modify user-provided model_id strings. Use exactly as given.
6. For S-007 / S-008 / S-009, capture CLI stdout and present to user. Do not reformat unless requested.
7. For S-005 / S-006 dry-run, present the full merged_config JSON to user and explicitly ask for confirmation before executing the actual merge.

## 6. File Paths (relative to skill root)

| File | Path |
|------|------|
| Registry | openrouter-llm-tracker/assets/llm.registry.json |
| Scores | openrouter-llm-tracker/assets/llm.scores.json |
| History | openrouter-llm-tracker/assets/llm.history/YYYY-MM-DD.json |
| Mapping rules | openrouter-llm-tracker/references/MAPPING.md |
| Ranking rules | openrouter-llm-tracker/references/RANKING.md |
| Environment template | openrouter-llm-tracker/.env |
| OpenClaw default config | ~/.openclaw/config.json |
| WorkBuddy default config | ~/.workbuddy/models.json |

## 7. Version

1.2.2 | 2026-05-14 | Fixed S-006 output format to match ACTUAL ~/.workbuddy/models.json schema (key/display_name/supports_tools/context_window etc.). Changed CLI to use --model-id and --param-type flags (positional args were ambiguous). Updated default merge target to ~/.workbuddy/models.json.
1.2.1 | 2026-05-14 | Fixed script-relative default paths for --registry and --scores. Fixed --merge-into to support optional argument (uses default path when no value provided). Updated CLI examples in SKILL.md to match argparse behavior.
