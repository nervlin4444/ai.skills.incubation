---
title: "Platform Trace Format Reference"
name: agent-conversation-mode
description: "Documentation for platform-generated trace JSON format based on actual WorkBuddy trace analysis."
version: "v6.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T16:55:00+08:00"
fixes: []
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  - local_path: "{baseDir}/references/platform_trace_format.md"
    github_path: "agent-conversation-mode/references/platform_trace_format.md"
---

# Platform Trace Format Reference

Based on actual trace file analysis: `trace_e58b3f5ea01d49cbaaab7462f4d6d5f7.json`

---

## File Location

    ~/.workbuddy/traces/{worker_pid}/trace_{uuid}.json

Example:

    ~/.workbuddy/traces/52813/trace_e58b3f5ea01d49cbaaab7462f4d6d5f7.json

---

## Top-Level Structure

    {
      "trace": {
        "traceId": "trace_{uuid}",
        "name": "Agent workflow",
        "workerPid": 52813,
        "workerHostname": "KEVINLINZ.local",
        "startedAt": "2026-05-25T06:53:43.128Z",
        "endedAt": "2026-05-25T06:58:04.033Z",
        "duration": 260905,
        "status": "ok",
        "spanCount": 30,
        "totalTokens": 846552,
        "metadata": {},
        "sessionId": "{uuid}",
        "agentName": "cli",
        "modelInfo": {
          "models": ["tencent/hy3-preview-20260421"],
          "totalInputTokens": 840496,
          "totalOutputTokens": 6056,
          "totalCachedTokens": 772352,
          "lastCallInputTokens": 840496,
          "callCount": 9
        }
      },
      "spans": [...]
    }

---

## Span Types

| type | Description | Example |
|------|-------------|---------|
| `custom` | Platform internal events | `mcp_tools` |
| `agent` | Agent container span | `cli` |
| `generation` | LLM generation | Agent response generation |
| `function` | Tool/function call | `Skill`, `Bash`, `Read` |

---

## Span Structure (Function Type)

    {
      "traceId": "trace_xxx",
      "spanId": "span_xxx",
      "parentId": "span_xxx",
      "name": "Skill",
      "type": "function",
      "startedAt": "2026-05-25T06:53:57.128Z",
      "endedAt": "2026-05-25T06:53:57.136Z",
      "duration": 8,
      "status": "ok",
      "error": null,
      "toolName": "Skill",
      "toolInput": "",
      "toolOutput": "{...}"  // Full content (e.g., SKILL.md text)
    }

---

## Known Limitations

| Limitation | Detail |
|------------|--------|
| Generation content unavailable | `generation.toolOutput` is empty string `""` |
| User input not in trace | User messages embedded in platform, not exposed |
| Tool outputs complete | `function.toolOutput` contains full content |

---

## Extraction Strategy

Daemon reads first 2KB for `trace` metadata only.
Full JSON copied verbatim without deep span parsing.

---

*Reference v6.0.0*
