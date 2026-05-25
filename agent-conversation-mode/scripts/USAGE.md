---
title: "conversation_append.py v1.4.0 Usage Manual"
name: "agent-conversation-mode"
description: "Passive real-time recording tool usage guide. Updated for v1.4.0 with --from-file long content support, --user-input/--agent-response short content, and CHANGELOG discipline integration."
version: "v5.1"
github_repository: "nervlin4444/ai.agent.harness"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/USAGE.md"
    github_path: "/agent-conversation-mode/scripts/USAGE.md"
---

# conversation_append.py v1.4.0 Usage Manual

## 1. Quick Start (3 Steps)

### Step 1: Environment Setup

    set CONVERSATION_REALTIME_RECORD=true

Or in PowerShell:

    $env:CONVERSATION_REALTIME_RECORD="true"

### Step 2: Initialize Conversation File

    python conversation_append.py --file ./assets --init --conv-id C-20260517143200 --date 2026-05-17

This creates: `./assets/conversations/2026-05-17/C-20260517143200.md`

### Step 3: Append Structured Block

    python conversation_append.py --file ./assets --type tool_call --content "use_skill(agent-bootstrap) v5.1 loaded" --conv-id C-20260517143200 --date 2026-05-17

---

## 2. Command Reference

### 2.1 Version Check (Mandatory Before Any Operation)

    python conversation_append.py --version

Expected output: `[VERSION] v1.4.0`

| Actual Version | Available Params | Execution Strategy |
|:---|:---|:---|
| **v1.4.0** | --user-input / --agent-response / **--from-file** / --type / --content | Short: CLI args, Long: JSON file |
| v1.3.0 | --user-input / --agent-response / --type / --content | Short: CLI args, Long: split multiple |
| v1.2.0 or earlier | --type / --content only | Compatibility mode (degraded) |

### 2.2 Init Mode (Create New Conversation File)

| Parameter | Required | Description |
|:---|:---|:---|
| --file | Yes | Skill assets directory path |
| --init | Yes | Flag to create new file |
| --conv-id | Yes | Conversation ID (e.g. C-20260517143200) |
| --date | Yes | Date stamp (YYYY-MM-DD) |

Example:

    python conversation_append.py --file ~/.workbuddy/skills/agent-conversation-mode/assets --init --conv-id C-20260517143200 --date 2026-05-17

### 2.3 Short Content Mode (< 500 chars)

#### Method A: Backup Both User + Agent (Recommended)

| Parameter | Required | Description |
|:---|:---|:---|
| --file | Yes | Path to CONVERSATION.md or assets directory |
| --user-input | Yes | User message content |
| --agent-response | Yes | Agent response content |
| --conv-id | Conditional | Required if --file is directory |
| --date | Conditional | Required if --file is directory |
| --json | No | Output result as JSON |

Example:

    python conversation_append.py --file ./assets --user-input "Hello" --agent-response "Hi there" --conv-id C-20260517143200 --date 2026-05-17 --json

#### Method B: Backup Agent Response Only

    python conversation_append.py --file ./assets --agent-response "Agent reply text" --conv-id C-20260517143200 --date 2026-05-17

#### Method C: Backup Tool Call

    python conversation_append.py --file ./assets --type tool_call --content "use_skill(agent-bootstrap) - loaded v5.1" --conv-id C-20260517143200 --date 2026-05-17

### 2.4 Long Content Mode (> 500 chars) — v1.4.0 New Feature

#### Method D: JSON File Transfer (Recommended)

**Step 1: Generate JSON File**

    # Windows PowerShell
    $json = @{
        user_input = "User input can be very long..."
        agent_response = "Agent response can be very long, no command line limit..."
    } | ConvertTo-Json -Depth 1
    $json | Set-Content -Path "./temp/backup_C-20260517143200.json" -Encoding UTF8

    # Linux / macOS
    echo '{"user_input":"...","agent_response":"..."}' > ./temp/backup_C-20260517143200.json

**Step 2: Execute Backup**

    python conversation_append.py --file ./assets --from-file ./temp/backup_C-20260517143200.json --conv-id C-20260517143200 --date 2026-05-17

**Step 3: (Optional) Clean Up**

    Remove-Item ./temp/backup_C-20260517143200.json

#### JSON File Format

    {
        "user_input": "Complete user input text",
        "agent_response": "Complete agent response text (no length limit)",
        "block_type": "final_response",
        "metadata": {"source": "agent-conversation-mode"}
    }

**Important**: Temporary JSON files are **NOT temporary scripts**:
- Not `.py` files (no executable code)
- Pure UTF-8 text data files
- Can be retained as backup logs
- Does NOT violate "no temporary scripts" rule

---

## 3. Block Types

| Type | When to Use | Example Content |
|:---|:---|:---|
| tool_call | After use_skill() execution | use_skill(agent-bootstrap) - load v5.1 |
| process_msg | Intermediate step descriptions | Reload user skills: 3 items loaded |
| table | Structured reports | Markdown table syntax |
| list | Pending items or bullet points | 1. Fix path issue 2. Update script |
| final_response | Agent complete response | Full response text |
| user_input | User message | User query text |
| error | Error or exception | [ERROR] File not found |

---

## 4. Output Format in CONVERSATION.md

After appending, the file contains block markers:

    ---
    id: "C-20260517143200"
    date: "2026-05-17"
    status: "active"
    realtime_record: "enabled"
    version: "v5.1"
    ---

    ## [BLOCK: tool_call] 2026-05-17 14:32:05 {"hash": "a1b2c3d4"}
    - use_skill(agent-bootstrap) - load v5.1
    <!-- END BLOCK: tool_call hash=a1b2c3d4 -->

    ## [BLOCK: table] 2026-05-17 14:32:18 {"hash": "e5f6g7h8"}
    | Item | Status |
    |:---|:---|
    | Task A | Done |
    <!-- END BLOCK: table hash=e5f6g7h8 -->

---

## 5. CHANGELOG Discipline Integration

When modifying scripts in the scripts/ directory, update CHANGELOG.md simultaneously.

### Format

    ## [CHANGELOG] {YYYY-MM-DD HH:MM:SS} | {filename} | {change_type}
    Reason: {reason for change}
    Summary: {change summary}
    Impact: {scope of impact}
    Agent: {agent identifier}

### Change Types

| Type | Description |
|:---|:---|
| BUGFIX | Fix a bug |
| FEATURE | Add new functionality |
| REFACTOR | Refactor code |
| DOCS | Update documentation or comments |
| CONFIG | Update configuration |
| SECURITY | Security-related changes |

### Example

    ## [CHANGELOG] 2026-05-17 14:32:15 | conversation_append.py | BUGFIX
    Reason: Fix PowerShell encoding issue causing error capture failure
    Summary: Add try/except + error log write to UTF-8 file
    Impact: All Windows PowerShell execution scenarios
    Agent: Main Agent (L0)

---

## 6. Emergency Shutdown

If recording causes issues, disable immediately without restarting Agent:

    # PowerShell
    $env:CONVERSATION_REALTIME_RECORD="false"

    # Or modify skill frontmatter (takes effect next conversation)
    # In SKILL.md: realtime_record: disabled

---

## 7. Troubleshooting

| Symptom | Cause | Solution |
|:---|:---|:---|
| [RECORD-DISABLED] | Env var set to false | Set CONVERSATION_REALTIME_RECORD=true |
| [BLOCK-REJECTED] | Invalid block type | Use allowed types only |
| [BLOCK-OVERSIZE] | Content > 50KB | Split into multiple blocks |
| [DIR-FULL] | Directory > 500MB | Old files auto-cleaned after 7 days |
| [RECORD-FAILED] | Disk full / permission | Check disk space and write permissions |
| [PATH-ERROR] | Missing conv-id or date | Provide both when --file is directory |
| [VERSION-MISMATCH] | Script < v1.4.0 | Report to user, use compatibility mode |
| [CONTENT-LONG] | Content > 500 chars | Use --from-file with JSON file |

---

## 8. Version Differences

| Feature | v1.0.0 | v1.1.0 | v1.3.0 | **v1.4.0** |
|:---|:---|:---|:---|:---|
| Recording timing | End only | Real-time | Real-time | Real-time |
| Block structure | Flat text | Structured | Structured | Structured |
| Content filtering | None | Auto-redacted | Auto-redacted | Auto-redacted |
| File rotation | None | Auto 10MB | Auto 10MB | Auto 10MB |
| Auto cleanup | None | 7 days | 7 days | 7 days |
| Directory cap | None | 500MB | 500MB | 500MB |
| Hash integrity | None | MD5 | MD5 | MD5 |
| CLI interface | Basic | Full argparse | + --user-input / --agent-response | **+ --from-file** |
| Long content | N/A | N/A | Split multiple | **JSON file** |
| Cross-platform | Limited | Limited | Better | **Full UTF-8 JSON** |

---

## 9. Production Checklist

Before deploying to production:

- [ ] Set CONVERSATION_REALTIME_RECORD=true
- [ ] Verify script version == v1.4.0 (python conversation_append.py --version)
- [ ] Test with --init to create sample conversation file
- [ ] Append one tool_call block and verify format
- [ ] Append one table block and verify Markdown syntax preserved
- [ ] Test short content with --user-input / --agent-response
- [ ] Test long content with --from-file and JSON file
- [ ] Test emergency shutdown with env var = false
- [ ] Verify 7-day cleanup does not remove active files
- [ ] Confirm directory size stays under 500MB
- [ ] Create CHANGELOG.md from template
- [ ] Test script modification scenario with CHANGELOG update

---

## 10. Integration with Agent Skills

When Agent generates output, call append_conversation() immediately:

    # Short content (< 500 chars)
    python conversation_append.py --file ./assets --user-input "{user_text}" --agent-response "{agent_text}" --conv-id C-20260517143200 --date 2026-05-17

    # Long content (> 500 chars)
    # Step 1: Write JSON file
    # Step 2: python conversation_append.py --file ./assets --from-file ./temp/backup.json --conv-id C-20260517143200 --date 2026-05-17

    # After tool call
    python conversation_append.py --file ./assets --type tool_call --content 'use_skill("{skill_name}") - {result_summary}' --conv-id C-20260517143200 --date 2026-05-17

---

## 11. Performance Metrics

| Metric | Normal | Warning | Action |
|:---|:---|:---|:---|
| Single write latency | < 5ms | 5-20ms | Monitor |
| File size | < 1MB | 1-5MB | Rotation active |
| Directory size | < 100MB | 100-500MB | Cleanup active |
| Block count per conversation | < 50 | 50-100 | Review necessity |
| CHANGELOG entries per session | < 10 | 10-20 | Review script stability |

---

*Manual version: v5.1 (aligned with conversation_append.py v1.4.0)*
*For agent-conversation-mode v5.1*
