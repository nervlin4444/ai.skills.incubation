---
title: "Scripts Usage Guide"
name: "openrouter-llm-tracker"
description: "Usage instructions for all scripts in the openrouter-llm-tracker skill bundle. Includes CLI query modes, batch config generation in official formats for OpenClaw and WorkBuddy, and smart-merge for Windows, macOS, and Linux."
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
  local_path: "{baseDir}/scripts/USAGE.md"
  github_path: "openrouter-llm-tracker/scripts/USAGE.md"
---
# Scripts Usage Guide

## 1. Environment Setup

### 1.1 Python Version

Python 3.10 or higher required.

### 1.2 Dependencies

Standard library only: json, datetime, pathlib, os, time, typing, urllib, argparse, shutil.

Optional but recommended: requests (for better error handling in llm.curl.py).

```bash
pip install requests  # optional, enables requests mode in llm.curl.py
```

### 1.3 Directory Structure

Ensure the following directories exist before running scripts:

```bash
mkdir -p "openrouter-llm-tracker/data/llm.history"
mkdir -p "openrouter-llm-tracker/references"
```

### 1.4 Environment Variables

Copy the .env template from skill root and set your OpenRouter API key:

```bash
cp "openrouter-llm-tracker/.env" "openrouter-llm-tracker/.env.local"
# Edit .env.local and replace OPENROUTER_API_KEY with your actual key
```

Both OpenClaw and WorkBuddy configs reference the key via ${OPENROUTER_API_KEY}.

## 2. Script Reference

### 2.1 llm.fetcher.py -- F-001: Fetch Model List

**Purpose**: Query OpenRouter API and return structured model metadata.

**Function**: `fetch_models(api_key: str) -> List[Dict]`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| api_key | str | Yes | OpenRouter API key. Must start with "sk-or-v1-" |

**Returns**: List of model dicts conforming to the schema in LLM/SKILL.md section 2.

**Example**:

```python
from scripts.llm.fetcher import fetch_models

models = fetch_models(api_key="sk-or-v1-your-key-here")
print(f"Fetched {len(models)} models")
print(models[0]["id"])  # e.g. "openai/gpt-oss-120b:free"
```

**API Endpoint**: GET https://openrouter.ai/api/v1/models

**Error Handling**: Raises ConnectionError on network failure. Returns empty list on API error.

---

### 2.2 llm.registry.py -- F-002: Registry Manager + CLI Queries

**Purpose**: Persist model list to JSON registry and daily snapshot. Provide CLI queries without writing new scripts.

**Functions**:

#### `save_registry(models: List[Dict], data_dir: str) -> None`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| models | List[Dict] | Yes | Output from fetch_models() |
| data_dir | str | Yes | Path to assets directory |

**Writes**:
- `{data_dir}/llm.registry.json` -- Current master registry
- `{data_dir}/llm.history/YYYY-MM-DD.json` -- Daily snapshot

#### `load_registry(data_dir: str) -> Dict`

Returns dict with keys "models" and "meta".

#### `load_snapshot(data_dir: str, date_str: str) -> Dict`

Returns snapshot for a specific date (YYYY-MM-DD).

---

**CLI Usage** (Windows / macOS / Linux compatible):

| Command | Description |
|---------|-------------|
| `python scripts/llm.registry.py "<data_dir>"` | Show meta (count, updated_at) |
| `python scripts/llm.registry.py "<data_dir>" --list` | List all models as table |
| `python scripts/llm.registry.py "<data_dir>" --free-only` | List only free models |
| `python scripts/llm.registry.py "<data_dir>" --filter-tier domain_expert` | Filter by tier |
| `python scripts/llm.registry.py "<data_dir>" --filter-type coding` | Filter by LLM type |
| `python scripts/llm.registry.py "<data_dir>" --search gemini` | Search by name/ID keyword |
| `python scripts/llm.registry.py "<data_dir>" --get openai/gpt-4o` | Get single model JSON |
| `python scripts/llm.registry.py "<data_dir>" --count` | Show statistics by vendor/tier/type |
| `python scripts/llm.registry.py "<data_dir>" --snapshot 2026-05-11 --list` | Load snapshot then list |

**Notes**:
- Wrap `data_dir` in quotes if the path contains spaces.
- Combine flags: `--free-only --filter-type coding` is valid.

---

### 2.3 llm.scorer.py -- F-003: Update Scores + Leaderboard

**Purpose**: Evaluate model performance and adjust assignment tier. Provide leaderboard CLI.

**Functions**:

#### `update_score(model_id: str, dimensions: Dict[str, int], data_dir: str, force: bool = False) -> Dict`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model_id | str | Yes | Model identifier |
| dimensions | Dict[str, int] | Yes | Scores per dimension (0-100) |
| data_dir | str | Yes | Path to assets directory |
| force | bool | No | Bypass minimum sample check |

**Returns**: Updated score record dict.

#### `get_model_score(model_id: str, data_dir: str) -> Optional[Dict]`

Retrieve score record for a model.

#### `score_from_batch_results(batch_results_path, registry_path, data_dir, min_latency_override)`

Calculate scores from F-006 batch results and write to llm.scores.json.

---

**CLI Usage**:

| Command | Description |
|---------|-------------|
| `python scripts/llm.scorer.py "<data_dir>" <model_id> latency=90 accuracy=85 ...` | Update single model score |
| `python scripts/llm.scorer.py --batch` | Batch mode from f006_batch_results.json |
| `python scripts/llm.scorer.py --batch 50.0` | Batch mode with min latency override |
| `python scripts/llm.scorer.py "<data_dir>" --leaderboard` | Top 20 leaderboard |
| `python scripts/llm.scorer.py "<data_dir>" --leaderboard 10` | Top 10 leaderboard |

---

### 2.4 llm.curl.py -- F-006: Test Connectivity + Batch Registry Test

**Purpose**: Verify API key validity and model availability. Support single model test or batch registry test.

**Functions**:

#### `test_model_connectivity(api_key, model_id, test_prompt, max_tokens, timeout_seconds) -> Dict`

**Returns**: Result dict with status / latency_ms / response / error_message.

#### `test_registry_models(api_key, registry_path, free_only, max_tokens, timeout_seconds, delay_ms) -> List[Dict]`

Test all (or free-only) models in registry.

---

**CLI Usage**:

| Command | Description |
|---------|-------------|
| `python scripts/llm.curl.py "<api_key>"` | Test default model (openai/gpt-4o) |
| `python scripts/llm.curl.py "<api_key>" openai/gpt-4o` | Test specific model |
| `python scripts/llm.curl.py "<api_key>" openai/gpt-4o "Say hello" 128` | Custom prompt and max_tokens |
| `python scripts/llm.curl.py "<api_key>" --registry-test` | Test all models in registry |
| `python scripts/llm.curl.py "<api_key>" --registry-test --free-only` | Test only free models |
| `python scripts/llm.curl.py "<api_key>" --registry-test --free-only --output results.json` | Write results to file |

**Notes**:
- `api_key` must be the first positional argument.
- `--output` writes a JSON array suitable for `llm.scorer.py --batch`.
- `--timeout` (default 30) and `--delay` (default 500ms) are optional.

---

### 2.5 llm.config.openclaw.py -- F-004: OpenClaw Config (Official Format)

**Purpose**: Generate OpenClaw-compatible JSON config in official schema. Supports single model, batch top-N, or smart-merge into existing agent config.

**Official Default Path**: `~/.openclaw/config.json` (auto-expanded cross-platform).

**Output Format** (OpenClaw official):

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "nvidia/nemotron-3-nano-30b-a3b:free",
        "fallbacks": ["arcee-ai/trinity-large-thinking:free"]
      },
      "models": {
        "nvidia/nemotron-3-nano-30b-a3b:free": {"alias": "Nemotron 3 Nano 30B A3B (free)"}
      }
    }
  },
  "env": {
    "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}"
  }
}
```

**Functions**:

#### `generate_openclaw_config(model_id, param_type, registry_path) -> str`

Single model config. Returns JSON string.

#### `generate_openclaw_batch_config(param_type, registry_path, scores_path, top_n, free_only) -> str`

Batch top-N config. Returns JSON string.

#### `merge_into_openclaw_config(param_type, registry_path, scores_path, top_n, free_only, target_path, dry_run) -> str`

Smart-merge into existing config. Handles backup, replacement, routing auto-update.

---

**CLI Usage**:

| Command | Description |
|---------|-------------|
| `python scripts/llm.config.openclaw.py openai/gpt-oss-120b:free agentic` | Single model config |
| `python scripts/llm.config.openclaw.py agentic` | Standalone batch top 10 |
| `python scripts/llm.config.openclaw.py agentic --top 5` | Standalone batch top 5 |
| `python scripts/llm.config.openclaw.py agentic --free-only` | Standalone batch free only |
| `python scripts/llm.config.openclaw.py agentic --output openclaw.config.json` | Write standalone to file |

**Smart-Merge CLI**:

| Command | Description |
|---------|-------------|
| `python scripts/llm.config.openclaw.py agentic --merge-into --dry-run` | Dry-run at default path (~/.openclaw/config.json) |
| `python scripts/llm.config.openclaw.py agentic --merge-into "C:/path/config.json" --dry-run` | Dry-run at custom path |
| `python scripts/llm.config.openclaw.py agentic --merge-into` | Actual merge at default path |
| `python scripts/llm.config.openclaw.py agentic --merge-into "C:/path/config.json"` | Actual merge at custom path |
| `python scripts/llm.config.openclaw.py agentic --merge-into --free-only --top 5` | Merge top 5 free models at default path |

**Merge Behavior**:
1. Verify target exists. If not, error and stop.
2. Remove old backup (`target.backup`) if exists.
3. Backup current config to `target.backup`.
4. Replace `agents.defaults.model.primary` with Top-1 model ID.
5. Replace `agents.defaults.model.fallbacks` with remaining model IDs.
6. Replace `agents.defaults.models` map with new aliases.
7. Ensure `env.OPENROUTER_API_KEY` exists.
8. Preserve all other fields unchanged.

---

### 2.6 llm.config.workbuddy.py -- F-005: WorkBuddy Config (Official Format)

**Purpose**: Generate WorkBuddy-compatible JSON config in official schema. Supports single model, batch top-N, or smart-merge into existing agent config.

**Official Default Path**: `~/.workbuddy/config.json` (auto-expanded cross-platform).

**Output Format** (WorkBuddy official):

```json
{
  "models": [
    {
      "id": "nvidia/nemotron-3-nano-30b-a3b:free",
      "name": "NVIDIA: Nemotron 3 Nano 30B A3B (free)",
      "vendor": "NVIDIA",
      "url": "https://openrouter.ai/api/v1/chat/completions",
      "apiKey": "${OPENROUTER_API_KEY}",
      "maxInputTokens": 256000,
      "maxOutputTokens": 0,
      "supportsToolCall": true,
      "supportsImages": false
    }
  ],
  "availableModels": [
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "arcee-ai/trinity-large-thinking:free"
  ]
}
```

**Functions**:

#### `generate_workbuddy_config(model_id, param_type, registry_path) -> str`

Single model config. Returns JSON string.

#### `generate_workbuddy_batch_config(param_type, registry_path, scores_path, top_n, free_only) -> str`

Batch top-N config. Returns JSON string.

#### `merge_into_workbuddy_config(param_type, registry_path, scores_path, top_n, free_only, target_path, dry_run) -> str`

Smart-merge into existing config. Handles backup, replacement.

---

**CLI Usage**:

| Command | Description |
|---------|-------------|
| `python scripts/llm.config.workbuddy.py baidu/cobuddy:free coding` | Single model config |
| `python scripts/llm.config.workbuddy.py agentic` | Standalone batch top 10 |
| `python scripts/llm.config.workbuddy.py agentic --top 5` | Standalone batch top 5 |
| `python scripts/llm.config.workbuddy.py agentic --free-only` | Standalone batch free only |
| `python scripts/llm.config.workbuddy.py agentic --output workbuddy.config.json` | Write standalone to file |

**Smart-Merge CLI**:

| Command | Description |
|---------|-------------|
| `python scripts/llm.config.workbuddy.py agentic --merge-into --dry-run` | Dry-run at default path (~/.workbuddy/config.json) |
| `python scripts/llm.config.workbuddy.py agentic --merge-into "C:/path/config.json" --dry-run` | Dry-run at custom path |
| `python scripts/llm.config.workbuddy.py agentic --merge-into` | Actual merge at default path |
| `python scripts/llm.config.workbuddy.py agentic --merge-into "C:/path/config.json"` | Actual merge at custom path |
| `python scripts/llm.config.workbuddy.py agentic --merge-into --free-only --top 5` | Merge top 5 free models at default path |

**Merge Behavior**:
1. Verify target exists. If not, error and stop.
2. Remove old backup (`target.backup`) if exists.
3. Backup current config to `target.backup`.
4. Replace `models` array with new top-N models.
5. Replace `availableModels` array with new ID list.
6. Preserve all other fields unchanged.

---

## 3. Typical Workflows

### 3.1 Daily Registry Update

```python
from scripts.llm.fetcher import fetch_models
from scripts.llm.registry import save_registry

API_KEY = "sk-or-v1-your-key"
DATA_DIR = "openrouter-llm-tracker/assets"

models = fetch_models(api_key=API_KEY)
save_registry(models, data_dir=DATA_DIR)
print(f"Registry updated: {len(models)} models")
```

### 3.2 Quick Query: List Free Models (No Script Writing)

```bash
# Windows PowerShell
python scripts/llm.registry.py "openrouter-llm-tracker/assets" --free-only

# macOS / Linux Bash
python scripts/llm.registry.py "openrouter-llm-tracker/assets" --free-only
```

### 3.3 New Model Evaluation Pipeline

```python
from scripts.llm.curl import test_model_connectivity
from scripts.llm.scorer import update_score

API_KEY = "sk-or-v1-your-key"
MODEL_ID = "baidu/cobuddy:free"
DATA_DIR = "openrouter-llm-tracker/assets"

# Step 1: Test connectivity
conn = test_model_connectivity(api_key=API_KEY, model_id=MODEL_ID)
if conn["status"] != "success":
    raise RuntimeError(f"Model unreachable: {conn['error_message']}")

# Step 2: Score based on test results
latency_score = max(0, 100 - conn["latency_ms"] // 10)
update_score(
    model_id=MODEL_ID,
    dimensions={
        "latency": latency_score,
        "accuracy": 85,
        "tool_reliability": 90,
        "cost_efficiency": 100,
        "context_stability": 80,
    },
    data_dir=DATA_DIR,
)
```

### 3.4 Batch Test All Free Models + Auto-Score

```bash
# Step 1: Batch test free models, write results
python scripts/llm.curl.py "sk-or-v1-xxx" --registry-test --free-only --output "openrouter-llm-tracker/data/f006_batch_results.json"

# Step 2: Auto-score from batch results
python scripts/llm.scorer.py --batch

# Step 3: View leaderboard
python scripts/llm.scorer.py "openrouter-llm-tracker/assets" --leaderboard
```

### 3.5 Smart-Merge WorkBuddy Config (Recommended Workflow)

```bash
# Step 1: Always dry-run first to preview (uses default path ~/.workbuddy/config.json)
python scripts/llm.config.workbuddy.py agentic --merge-into --dry-run

# Step 2: Review output with user, confirm OK

# Step 3: Execute actual merge (auto-backup)
python scripts/llm.config.workbuddy.py agentic --merge-into

# Alternative: custom path
python scripts/llm.config.workbuddy.py agentic --merge-into "C:/Users/Kevin/.workbuddy/config.json"

# Alternative: free only, top 5
python scripts/llm.config.workbuddy.py agentic --merge-into --free-only --top 5
```

### 3.6 Smart-Merge OpenClaw Config (Recommended Workflow)

```bash
# Step 1: Dry-run preview (uses default path ~/.openclaw/config.json)
python scripts/llm.config.openclaw.py agentic --merge-into --dry-run

# Step 2: User confirms

# Step 3: Execute
python scripts/llm.config.openclaw.py agentic --merge-into

# Alternative: custom path
python scripts/llm.config.openclaw.py agentic --merge-into "/home/kevin/.openclaw/config.json"
```

### 3.7 Complete Daily Pipeline (One-liner Style)

```bash
# 1. Fetch + save
python -c "from scripts.llm.fetcher import fetch_models; from scripts.llm.registry import save_registry; m=fetch_models('sk-or-v1-xxx'); save_registry(m, 'openrouter-llm-tracker/assets')"

# 2. Test free models
python scripts/llm.curl.py "sk-or-v1-xxx" --registry-test --free-only --output "openrouter-llm-tracker/data/f006_batch_results.json"

# 3. Score
python scripts/llm.scorer.py --batch

# 4. Preview WorkBuddy merge
python scripts/llm.config.workbuddy.py agentic --merge-into --dry-run

# 5. Execute WorkBuddy merge
python scripts/llm.config.workbuddy.py agentic --merge-into

# 6. Preview OpenClaw merge
python scripts/llm.config.openclaw.py agentic --merge-into --dry-run

# 7. Execute OpenClaw merge
python scripts/llm.config.openclaw.py agentic --merge-into
```

---

## 4. File Output Locations

| Output | Path | Format |
|--------|------|--------|
| Master registry | `{data_dir}/llm.registry.json` | JSON |
| Daily snapshot | `{data_dir}/llm.history/YYYY-MM-DD.json` | JSON |
| Score records | `{data_dir}/llm.scores.json` | JSON |
| Batch test results | `{data_dir}/f006_batch_results.json` | JSON array |
| Environment template | `{skill_root}/.env` | dotenv |
| OpenClaw single config | Returned as string | JSON |
| OpenClaw standalone batch | `{data_dir}/openclaw.config.json` | JSON |
| OpenClaw merged config | `~/.openclaw/config.json` | JSON |
| OpenClaw backup | `~/.openclaw/config.json.backup` | JSON |
| WorkBuddy single config | Returned as string | JSON |
| WorkBuddy standalone batch | `{data_dir}/workbuddy.config.json` | JSON |
| WorkBuddy merged config | `~/.workbuddy/config.json` | JSON |
| WorkBuddy backup | `~/.workbuddy/config.json.backup` | JSON |

---

## 5. Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| "Registry file not found" | First run, no registry exists | Run fetch_models + save_registry first |
| "Model ID not found in registry" | Registry outdated or model not fetched | Update registry or verify model_id spelling |
| "auth_failed" | API key invalid | Verify key starts with "sk-or-v1-" and is active |
| "rate_limited" | Free tier quota exceeded | Wait 1 minute, or add credits to OpenRouter account |
| "timeout" | Model provider slow | Increase --timeout, or mark model as unstable |
| "Cannot connect" | Network issue | Check internet, verify OpenRouter API status |
| references/MAPPING.md missing | Not yet created by owner | Script uses default tier "domain_expert" |
| references/RANKING.md missing | Not yet created by owner | Script uses equal weights 0.2 each |
| Path with spaces fails | Missing quotes around path | Wrap path in double quotes: `"C:/My Path/assets"` |
| "No scored models match criteria" | Scores file empty or no models pass filter | Run scoring first, or relax --free-only filter |
| OpenClaw config not found at official path | ~/.openclaw/config.json does not exist | Create the config file first, or use --merge-into with custom path |
| WorkBuddy config not found at official path | ~/.workbuddy/config.json does not exist | Create the config file first, or use --merge-into with custom path |
| Backup not created | Permission denied on target directory | Check write permissions for the config directory |
| WorkBuddy rejects config format | Output format mismatch | Ensure you are using llm.config.workbuddy.py (not openclaw.py) |
| OpenClaw rejects config format | Unknown keys in config | Ensure you are using llm.config.openclaw.py (not workbuddy.py) |
| "argument --merge-into: expected one argument" | Old argparse behavior | Update to v1.2.1+; --merge-into now supports optional argument |

---

*File: openrouter-llm-tracker/scripts/USAGE.md*
*Naming convention: dot-separated, no hyphens or underscores in filenames*
*Version: 1.2.1 | 2026-05-14 | Fixed script-relative default paths. Fixed --merge-into optional argument. Updated CLI examples.*
