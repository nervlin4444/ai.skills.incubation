---
title: "Assignment Tier Mapping Rules"
name: "openrouter-llm-tracker"
description: "Defines the mapping rules between model capabilities and assignment tiers in the agent swarm architecture."
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
  local_path: "{baseDir}/references/MAPPING.md"
  github_path: "openrouter-llm-tracker/references/MAPPING.md"
---
# Assignment Tier Mapping Rules

## 1. Tier Hierarchy

```
Main Agent (主代理)
├── omnipotent        (萬能型)
├── c_level           (C-level 管理)
├── specialist_manager (專項管理)
└── strategic_expert  (戰略專家)

Sub Agent (子代理)
├── domain_expert     (領域專家)
├── supervisor        (主管)
└── staff             (員工)
```

## 2. Mapping Dimensions

Tier assignment is determined by evaluating models across these dimensions. Each dimension contributes to the final tier decision.

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Context Length | 20% | Max input tokens capability |
| Tool Reliability | 25% | Function calling success rate |
| Reasoning Depth | 25% | Chain-of-thought quality |
| Multimodal Breadth | 15% | Vision / audio / video support |
| Cost Efficiency | 15% | Price-performance ratio |

## 3. Tier Thresholds (Default — Pending Owner Calibration)

| Tier | Min Composite Score | Key Requirements |
|------|---------------------|------------------|
| omnipotent | 95 | 1M+ context, adaptive reasoning, all modalities, tools, top 1% accuracy |
| c_level | 90 | 500K+ context, high reasoning, tools, top 5% accuracy |
| specialist_manager | 85 | 256K+ context, high reasoning, tools, domain-specific excellence |
| strategic_expert | 80 | 256K+ context, high reasoning, strong analytical benchmarks |
| domain_expert | 70 | 128K+ context, medium+ reasoning, tools, domain benchmark top 20% |
| supervisor | 60 | 128K+ context, medium reasoning, tools, reliable execution |
| staff | 0 | All other models, or models with limited capabilities |

## 4. Override Rules

These rules take precedence over composite scores:

| Rule | Condition | Override Tier |
|------|-----------|---------------|
| R-001 | Model explicitly labeled as "agentic" or "coding agent" by vendor | specialist_manager or domain_expert |
| R-002 | Model supports reasoning=adaptive + tools + vision + 1M context | omnipotent |
| R-003 | Model is OCR-only or audio-only | staff (specialized tool, not general agent) |
| R-004 | Model pricing is free tier with 429 rate limits | domain_expert max (unreliable for production) |
| R-005 | Model has SWE-Bench Verified > 60% | domain_expert minimum for coding tasks |
| R-006 | Model is flagged as "preview" or "experimental" | staff max (unstable) |

## 5. Vendor-Specific Defaults (Pending Owner Confirmation)

| Vendor | Default Tier | Rationale |
|--------|--------------|-----------|
| OpenAI (GPT series) | c_level | General purpose, high reliability |
| Anthropic (Claude) | c_level | Long context, strong reasoning |
| DeepSeek | domain_expert | Coding excellence, cost efficient |
| Alibaba (Qwen) | domain_expert | Long context, Chinese optimized |
| Baidu | domain_expert | Coding / OCR specialized |
| Tencent | staff | Minimal footprint, unstable |
| Google (Gemma) | domain_expert | Open weights, general capability |
| NVIDIA (Nemotron) | domain_expert | Open weights, coding specialized |
| Meta (Llama) | supervisor | General open source, reliable |
| MiniMax | domain_expert | Office automation specialized |
| Z.AI (GLM) | domain_expert | Chinese reasoning |
| Moonshot (Kimi) | c_level | Long context leader |
| Xiaomi (MiMo) | domain_expert | Cost efficient frontier |
| StepFun | domain_expert | Coding + reasoning |
| Poolside (Laguna) | domain_expert | Coding agent specialized |
| inclusionAI (Ring) | domain_expert | Thinking model |
| LiquidAI (LFM) | staff | Ultra-small, limited capability |
| NousResearch (Hermes) | supervisor | Open source general |
| CognitiveComputations (Dolphin) | staff | Uncensored, risky |

## 6. Status

| Item | Status | Owner |
|------|--------|-------|
| Dimension weights | Pending calibration | 主人 |
| Tier thresholds | Pending calibration | 主人 |
| Vendor defaults | Pending confirmation | 主人 |
| Override rules | Pending addition | 主人 |

## 7. Usage

This file is read by scripts/llm.scorer.py during score calculation. If this file is missing or a section is empty, the script falls back to default values and logs a warning.

---

*File: openrouter-llm-tracker/references/MAPPING.md*
*Naming convention: dot-separated, no hyphens or underscores in filenames*