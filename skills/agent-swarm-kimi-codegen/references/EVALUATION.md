# agent.swarm.kimi.codegen.evaluator.md
## Kimi Code Subcontractor Return Evaluation Standard

---

### File Info
| Field | Content |
|-------|---------|
| skill.id | agent.swarm.kimi.codegen.evaluator |
| version | v1.0 |
| date | 2026-05-06 |
| evaluator.target | agent.swarm.kimi.codegen.v1 output |

---

## 1. Evaluation Flow

    STEP 1: Schema Check (Format Validation)
    STEP 2: Compilation (Compile/Interpret)
    STEP 3: Unit Test Execution
    STEP 4: Boundary Injection Test
    STEP 5: Security Scan (v1.0 simplified)
    STEP 6: Token Audit

---

## 2. Evaluation Criteria

### 2.1 Schema Check

| Check | Pass Standard | Weight |
|-------|---------------|--------|
| Valid JSON | Parseable, no syntax error | Mandatory |
| Required fields present | code.main, code.tests, logic_analysis, test_coverage, dependencies, execution_command | Mandatory |
| No Markdown fences | Code strings contain no triple backticks | Mandatory |
| _meta complete | session_id, round, model, token_usage | Mandatory |

### 2.2 Compilation

| Language | Validation Command | Pass Standard |
|----------|------------------|---------------|
| Python | python -m py_compile {file} | No SyntaxError |
| C# | dotnet build | Build Success |
| PowerShell | Get-Command syntax check | No parse error |
| Bash | bash -n {file} | No syntax error |

### 2.3 Unit Test Execution

| Check | Pass Standard | Note |
|-------|---------------|------|
| All tests pass | pytest / dotnet test exit code 0 | v1.0: unit tests only |
| Coverage claim matches | test_coverage array matches actual test names | Prevent false reporting |
| Parameterized tests preferred | Use pytest.mark.parametrize | Reduce code lines |

### 2.4 Boundary Injection Test

For each boundary in structured_spec.boundary_conditions:

    FOR each boundary IN spec.boundary_conditions:
        Construct corresponding input data
        Execute code
        Verify output matches expected (or throws expected exception)
        IF not handled -> mark FAILED, record boundary name

### 2.5 Security Scan (v1.0 Simplified)

v1.0 does not enable full static analysis, but performs:

| Check | Block Condition | Action |
|-------|-----------------|--------|
| Dangerous functions | Code contains eval, exec, os.system, subprocess.call | BLOCK immediately |
| Hardcoded secrets | String contains password, api_key, secret followed by '=' | Flag WARNING |
| Network calls | Contains requests, urllib, socket | Flag WARNING (confirm if expected) |
| FS traversal | Contains /etc/passwd, .., absolute path writes | BLOCK immediately |

### 2.6 Token Audit

| Metric | v1.0 Limit | Over-limit Action |
|--------|-----------|-------------------|
| Input tokens / task | 8,000 | Log anomaly, suggest spec optimization |
| Output tokens / task | 12,000 | Log anomaly, suggest task splitting |
| Total tokens / task | 20,000 | Log anomaly, suggest LOCAL for next trigger |
| Fix rounds | 3 | Force escalate at round 4 |

---

## 3. Scoring Matrix

| Dimension | Weight | Excellent (90-100) | Pass (70-89) | Fail (<70) |
|-----------|--------|-------------------|--------------|------------|
| Correctness | 40% | All tests pass, all boundaries covered | Core tests pass, 1-2 boundary misses | Core tests fail |
| Conciseness | 20% | No redundancy, precise comments | Mild redundancy | Large template/dead code |
| Test Quality | 20% | Parameterized tests, 100% coverage | Regular tests, >=80% coverage | Tests missing or fake-pass |
| Token Efficiency | 10% | Total < 15,000 | Total < 20,000 | Total >= 20,000 |
| Security Compliance | 10% | No WARNING | 1-2 WARNING | Contains BLOCK item |

**Total Score**: Weighted sum >= 70 = "PASSED", deployable.
**Total Score < 70**: Return to Kimi for fix (counts toward fix rounds).

---

## 4. Output Formats

### 4.1 Passed (evaluation.pass.json)

    {
      "status": "PASSED",
      "task_id": "...",
      "session_id": "...",
      "score": 85,
      "breakdown": {
        "correctness": 40,
        "conciseness": 18,
        "test_quality": 16,
        "token_efficiency": 8,
        "security": 10
      },
      "token_audit": {
        "input_tokens": 5200,
        "output_tokens": 8900,
        "total": 14100,
        "rounds": 1
      },
      "recommendation": "Deployable"
    }

### 4.2 Failed (evaluation.fail.json)

    {
      "status": "FAILED",
      "task_id": "...",
      "session_id": "...",
      "score": 55,
      "breakdown": {...},
      "failure_reasons": [
        "Boundary condition 'empty_sku_list' not handled",
        "Test test_negative_qty assertion failed"
      ],
      "token_audit": {...},
      "recommendation": "Return to Kimi fix (Round 2)"
    }

### 4.3 Escalated (evaluation.escalate.json)

    {
      "status": "ESCALATED",
      "task_id": "...",
      "session_id": "...",
      "score": 45,
      "failure_reasons": [...],
      "rounds_consumed": 3,
      "token_consumed": 48000,
      "recommendation": "Reached v1.0 max resource consumption. Suggest human review or activate shielded features."
    }

---

## 5. Integration with OpenClaw

Evaluator acts as independent Agent (Evaluator Role), communicates via:

    POST /api/v1/evaluate
    Content-Type: application/json

    {
      "code_package": {...},
      "structured_spec": {...},
      "evaluation_config": "agent.swarm.kimi.codegen.evaluator.v1"
    }

OpenClaw acts based on status:

    PASSED -> call local.deploy
    FAILED -> call kimi.code.fix (if round < 3)
    ESCALATED -> call escalate_to_human

---

This file follows agent.swarm.kimi.codegen version locking mechanism.
