---
title: "Agent Conversation Mode Execution Guide"
name: agent-conversation-mode
description: "Agent conversation backup daemon. Agent zero participation. Daemon autonomously polls platform trace files and archives to CONVERSATION.md. Lifecycle routed through daemon-script-connector."
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
  - local_path: "{baseDir}/SKILL.md"
    github_path: "agent-conversation-mode/SKILL.md"
---

# agent-conversation-mode v6.0.0

**Agent does NOT participate in backup.**
**Daemon autonomously polls platform trace files.**
**Lifecycle managed by daemon-script-connector.**

---

## Identity Split

### If you are a Sub-Agent (L1 / L2 / L3)

This file is not for you.
Stop. Close. Execute your task.

### If you are a Main Agent (L0)

Continue. This skill requires no action from you.
The daemon runs independently.

---

## Architecture

```
Platform (WorkBuddy / OpenClaw / Kimi)
    |
    v  Auto-generates trace files
~/.workbuddy/traces/{pid}/trace_*.json
    |
    v  Daemon polls (interval: 60s)
conversation_daemon.py
    |
    v  Minimal header parse + full JSON copy
trace_extractor.py
    |
    v  Append-only archive
data/CONVERSATION.md
```

---

## Daemon Lifecycle

All lifecycle operations route through daemon-script-connector.

### Install

    python "{DAEMON_CONNECTOR}/scripts/daemon_connector.py" --install --skill-name agent-conversation-mode --script-path "~/.workbuddy/skills/agent-conversation-mode/scripts/conversation_daemon.py" --interval 60

### Status

    python "{DAEMON_CONNECTOR}/scripts/daemon_connector.py" --status --skill-name agent-conversation-mode

### Run-Now (immediate execution)

    python "{DAEMON_CONNECTOR}/scripts/daemon_connector.py" --run-now --skill-name agent-conversation-mode

### Remove

    python "{DAEMON_CONNECTOR}/scripts/daemon_connector.py" --remove --skill-name agent-conversation-mode

---

## Data Flow

| Step | Component | Action |
|------|-----------|--------|
| 1 | Platform | Auto-generates trace JSON files |
| 2 | Daemon | Scans `~/.workbuddy/traces/*/` for new `trace_*.json` |
| 3 | Daemon | Reads first 2KB for metadata (trace_id, session, agent, model) |
| 4 | Daemon | Checks `state/last_processed.json` for duplicates |
| 5 | Daemon | Reads full JSON, appends to `data/CONVERSATION.md` with header |
| 6 | Daemon | Updates `state/last_processed.json` |

---

## Output Format (CONVERSATION.md)

```markdown
## [TRACE] trace_xxx | 2026-05-25 14:53:43+0800
### Meta
- Platform: workbuddy
- Agent: cli
- Model: tencent/hy3-preview-20260421
- Session: xxx
- Duration: 260905ms | Tokens: 846552 | Spans: 30

### Raw Trace
```json
[full trace JSON content]
```

---
```

---

## Red Lines

- [ ] Agent must NOT write trigger files
- [ ] Agent must NOT call daemon directly
- [ ] Agent must NOT manage PID files
- [ ] Daemon must NOT manage its own deployment
- [ ] All lifecycle through daemon-script-connector
- [ ] CONVERSATION.md is append-only, never overwritten

---

## Version Lock

LOCK v6.0.0 PERMANENT -- Agent zero participation, autonomous trace polling, connector lifecycle routing.
