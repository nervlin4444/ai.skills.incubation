---
title: "conversation-mode v3.3.2 - Passive Real-time Recording Specification"
description: "Production-safe, audit-friendly, non-daemon real-time conversation recording with full risk assessment"
version: "v3.3.2-proposal"
date: "2026-05-11"
author: "Agent Swarm Architecture"
---

# conversation-mode v3.3.2 Real-time Recording - Risk Assessment and Design Spec

> Core Principle: Passive Trigger (Non-Daemon), Zero Privilege Escalation, Sandbox Execution, Auditable, Switchable

---

## 1. Design Philosophy: Why This Is NOT a High-Risk Daemon

### 1.1 Traditional Daemon Risk Flags

| Feature | High-Risk Reason | Does This Solution Have It? |
|:---|:---|:---|
| Resident background process | Resource consumption, hard to monitor, may run out of control | **NO** - No resident process |
| Active system probing | Invades platform internals, violates least privilege principle | **NO** - Only reads already-generated output |
| Privilege escalation | Needs root/admin rights to write to system directories | **NO** - Only writes to skill assets/ directory |
| Hidden behavior | User cannot detect or disable | **NO** - frontmatter clearly marked, one-click disable |
| Network communication | May leak data externally | **NO** - Pure local file operations |

### 1.2 This Solution's Positioning

**NOT a "Monitoring Daemon", but an "Output Archiver"**

- Analogy: Like a printer driver - after each print job completes, automatically saves a PDF copy
- Will NOT: Actively monitor system, modify platform behavior, stay resident in memory
- Will ONLY: After Agent has already generated output, "make a copy" to conversation.md

---

## 2. Architecture: Passive Trigger Design

### 2.1 Trigger Timing

```
[User Input] -> [Agent Processing] -> [Agent Generates Output]
                                           |
                                           +-> [UI Displays Output]
                                           |
                                           +-> [Passive Recorder Triggered]
                                                   |
                                                   +-> [Append to CONVERSATION.md]
```

**Key: Trigger point is AFTER "Agent has generated output", not "during platform internal processing"**

### 2.2 Trigger Conditions (Strictly Limited)

| Trigger Condition | Description | Risk Control |
|:---|:---|:---|
| Agent generates Markdown table | Task reports, skill version tables, pending items | Only records already-rendered text, does not probe UI |
| Agent calls use_skill() | Tool call name + parameter summary | Only records call command, not internal execution process |
| Agent outputs process message | Intermediate step descriptions | Only records text that Agent actively outputs |
| Agent final response | Complete response content | Already recorded, now adds structured markers |

### 2.3 Non-Trigger Situations (Explicitly Excluded)

- Do NOT record platform internal error logs
- Do NOT record user sensitive input (passwords, API Keys)
- Do NOT record network request details
- Do NOT record data from other conversations
- Do NOT actively execute when Agent has not generated output

---

## 3. Technical Implementation: Zero-Intrusion Hook

### 3.1 Implementation Layer

At the **Agent level** (not platform level):

```python
# Pseudo-code: Passive Trigger Recorder
class PassiveRecorder:
    def on_agent_output(self, output_block: dict):
        """
        Passively triggered when Agent generates output block
        output_block contains:
        - type: "table" | "tool_call" | "process_msg" | "final_response"
        - content: Already rendered Markdown text
        - timestamp: Generation time
        """
        if not self.is_enabled():
            return  # One-click disable, zero performance cost
        
        if self.should_record(output_block):
            self.append_to_conversation(output_block)
    
    def is_enabled(self) -> bool:
        # Read switch from frontmatter or environment variable
        return os.getenv("CONVERSATION_REALTIME_RECORD", "true").lower() == "true"
    
    def should_record(self, block: dict) -> bool:
        # Strict recording boundary check
        return block["type"] in ALLOWED_TYPES and len(block["content"]) < MAX_SIZE
```

### 3.2 Integration with Existing Scripts

Modify `conversation_append.py` (v1.0.0 -> v1.1.0):

```python
# conversation_append.py v1.1.0 new function
def append_structured_block(
    conversation_path: Path,
    block_type: str,  # "tool_call" | "process_msg" | "table" | "final_response"
    content: str,
    metadata: dict = None
) -> dict:
    """
    Passive trigger append structured block
    
    Features:
    - Pure append (a+ mode), no overwrite
    - Auto-add block separator markers (for later parsing)
    - Length validation (single block max 50KB)
    - Return {success, bytes_written, warning}
    """
```

### 3.3 CONVERSATION.md New Format (Block-based)

```markdown
---
id: C-20260511105000
date: 2026-05-11 10:50:00
status: active
realtime_record: enabled  # Clearly marked enabled status
---

## User Input
[user input content]

## [BLOCK: tool_call] 2026-05-11 10:50:05
- use_skill("agent-bootstrap") - load v2.3.0
- use_skill("agent-conversation-mode") - load v3.3.1
- use_skill("agent-coordination-mode") - load v1.3.0
- use_skill("write_to_file") - create 2026-05-11.md

## [BLOCK: process_msg] 2026-05-11 10:50:12
Reload user skills: agent-bootstrap v2.3.0, agent-conversation-mode v3.3.1, agent-coordination-mode v1.3.0 loaded

## [BLOCK: table] 2026-05-11 10:50:18 - Task Execution Report
| Item | Status | Description |
|:---|:---|:---|
| Reload user skills | Done | agent-bootstrap v2.3.0... |
| Update working memory | Done | Created/updated ... |
| ... | ... | ... |

## [BLOCK: table] 2026-05-11 10:50:20 - New Skill Version Highlights
| Skill | Version | Key Updates |
|:---|:---|:---|
| agent-bootstrap | v2.3.0 | Added identity judgment mechanism... |
| ... | ... | ... |

## [BLOCK: list] 2026-05-11 10:50:22 - Pending Items
1. agent-mission-planning skill identification issue...
2. conversation_append.py misuse issue...

## Agent Final Response
[final response content]
```

---

## 4. Risk Assessment Matrix

### 4.1 Architecture Risks

| Risk Item | Severity | Likelihood | Mitigation | Residual Risk |
|:---|:---|:---|:---|:---|
| File I/O blocks Agent output | Medium | Low | Async write (non-blocking a+ mode) | Very Low |
| Single conversation file too large | Medium | Medium | Single block 50KB limit, total file 10MB rotation | Low |
| Concurrent write conflicts | Low | Very Low | File lock (flock) or process-level serialization | Very Low |
| Disk space exhaustion | High | Low | Auto-cleanup files older than 7 days, total directory 500MB limit | Low |

### 4.2 Security Risks

| Risk Item | Severity | Likelihood | Mitigation | Residual Risk |
|:---|:---|:---|:---|:---|
| Records sensitive data (passwords, API Keys) | High | Medium | **Content Filter**: Regex match password patterns, replace with [REDACTED] | Low |
| Record files read by unauthorized users | Medium | Low | Write to skill assets/ directory (existing skill permission controls) | Low |
| Record content tampered for attacks | Medium | Very Low | Append-only no overwrite, block hash validation (optional) | Very Low |
| Rated as high-risk auto-execution | High | Medium | **Passive trigger design**, **no resident process**, **frontmatter clearly marked** | Very Low |

### 4.3 Operational Risks

| Risk Item | Severity | Likelihood | Mitigation | Residual Risk |
|:---|:---|:---|:---|:---|
| Production environment performance degradation | High | Low | Write operation < 5ms, batch buffer (optional), one-click disable | Very Low |
| Cannot disable recording during failures | High | Very Low | Environment variable switch (CONVERSATION_REALTIME_RECORD=false) takes effect immediately | Very Low |
| Log format incompatible with old versions | Medium | Medium | Keep old format parser, new format is block-based extension | Low |
| Developers misunderstand as monitoring tool | Medium | Medium | Documentation clearly states "Output Archiver" positioning, non-Daemon | Low |

### 4.4 Compliance Risks (skill_validate Audit)

| Check Item | This Solution Status | Description |
|:---|:---|:---|
| AGENT-001 Conversation record missing | Solved | Real-time recording ensures no missing |
| AGENT-006 Miswrite to memory.md | Not touched | Only writes to conversation.md |
| ARCH-001 SKILL.md positioning | Compliant | LLM execution instruction set |
| ARCH-002 frontmatter single line | Compliant | description single line |
| ARCH-003 File naming | Compliant | Dot-separated |
| ARCH-008 Fool-proof mechanism | Strengthened | New 8 red lines + 6 exceptions |
| **New: Non-Daemon declaration** | **Required** | frontmatter clearly marked `realtime_record: enabled` |
| **New: One-click disable mechanism** | **Required** | Environment variable + frontmatter dual switch |

---

## 5. Production Environment Deployment Guide

### 5.1 Enable Steps (Administrator Operation)

```powershell
# 1. Set environment variable (global switch)
[Environment]::SetEnvironmentVariable("CONVERSATION_REALTIME_RECORD", "true", "User")

# 2. Verify skill version
# Confirm agent-conversation-mode >= v3.3.2

# 3. Monitor first run
# Check if CONVERSATION.md correctly generates block markers
```

### 5.2 Disable Steps (Emergency)

```powershell
# Method 1: Environment variable (takes effect immediately, no Agent restart needed)
$env:CONVERSATION_REALTIME_RECORD = "false"

# Method 2: Modify skill frontmatter (takes effect next conversation)
# In LLM/SKILL.md frontmatter set:
# realtime_record: disabled

# Method 3: Remove skill (last resort)
# Remove agent-conversation-mode v3.3.2, rollback to v3.3.1
```

### 5.3 Performance Monitoring Metrics

| Metric | Normal Value | Warning Value | Danger Value |
|:---|:---|:---|:---|
| Single write latency | < 5ms | 5-20ms | > 20ms |
| Single conversation file size | < 1MB | 1-5MB | > 5MB |
| Log directory total size | < 100MB | 100-500MB | > 500MB |
| CPU usage (recorder) | < 0.1% | 0.1-1% | > 1% |

---

## 6. Integration with Existing Skill System

### 6.1 Family Manual Update

agent-conversation-mode v3.3.2 family manual (5 mandatory loads):

| Order | Skill | Version | Purpose |
|:---|:---|:---|:---|
| 1 | SOUL.md | v4.2 | Identity anchor |
| 2 | agent-bootstrap | v2.3.0 | Identity judgment |
| 3 | agent-conversation-mode | **v3.3.2** | **Conversation record + real-time archive** |
| 4 | agent-coordination-mode | v1.3.0 | Task routing |
| 5 | agent-skill-acquiring | v1.2.0 | Skill query |

### 6.2 Mnemonic Update

Original mnemonic: "Record. Conversation." (record conversation)
New mnemonic: "Record. Archive." (record archive)

Meaning:
- **Record**: Identify output blocks that need recording
- **Archive**: Real-time append to conversation.md
- **Classify**: Categorize archive (block markers)
- **File**: File management (length validation, rotation cleanup)

### 6.3 Exception Handling Addition

**Exception 7: Real-time record write failure**
- Trigger: Disk full, insufficient permissions, file lock conflict
- Actions:
  1. Output `[RECORD-FAILED]` marker
  2. Store pending records in memory buffer (max 10 items)
  3. Batch append when next write succeeds
  4. If fails 3 times consecutively, auto-disable real-time recording and report to master
- Prohibited: Blocking Agent output due to record failure

---

## 7. Confirmation Checklist (CONFIRMATION.md)

| Item | Suggested Value | Status |
|:---|:---|:---|
| Real-time record switch default | `enabled` (production environment recommend `disabled` for pilot first) | Pending confirmation |
| Single block size limit | 50KB | Pending confirmation |
| Total file rotation threshold | 10MB | Pending confirmation |
| Directory total size limit | 500MB | Pending confirmation |
| Auto-cleanup days | 7 days | Pending confirmation |
| Sensitive data filter rules | Passwords, API Keys, Tokens, Credit card numbers | Pending confirmation |
| Performance monitoring enabled | `true` (record each write latency) | Pending confirmation |

---

## 8. Conclusion

This solution's core value:

1. **Solves Problem #1**: 15 tool calls, 28 process messages, structured reports all real-time archived
2. **Production Safe**: Passive trigger, no Daemon, one-click disable
3. **Audit Friendly**: Clear "Output Archiver" positioning, not monitoring tool
4. **Risk Controllable**: All risk items have mitigation measures, residual risk very low

**NOT "monitoring", but "archiving"; NOT "Daemon", but "Hook"**

---

*Spec version: v3.3.2-proposal*
*Generated date: 2026-05-11*
