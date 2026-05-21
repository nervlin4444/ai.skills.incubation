# agent.swarm.kimi.codegen.api.template.py
# Moonshot API Mode A - Code Subcontractor Template
# Version: v1.0
# Date: 2026-05-06

import json
import os
import time
from typing import Dict, Any, Optional
from openai import OpenAI

# ============================================================
# Config (v1.0 locked)
# ============================================================
class KimiCodegenConfig:
    MODEL = "kimi-k2.6"
    TEMPERATURE = 0.1
    MAX_TOKENS = 16000
    TOP_P = 0.95
    BASE_URL = "https://api.moonshot.ai/v1"
    MAX_RETRY = 3
    TIMEOUT_SECONDS = 120

# ============================================================
# System Prompt (Token-optimized)
# ============================================================
SYSTEM_PROMPT_TEMPLATE = (
    "You are a professional retail system code subcontractor.\\n"
    "Task: Generate code and tests based on structured_spec.\\n"
    "Constraints:\\n"
    "1. Output ONLY JSON. No Markdown or explanations.\\n"
    "2. Code MUST conform to input/output Schema.\\n"
    "3. MUST cover ALL boundary conditions (see spec.test_matrix).\\n"
    "4. Pitfalls (see spec.pitfalls) MUST be embedded in code logic.\\n"
    "5. Comments ONLY for 'why', not 'what'. No verbose docs.\\n"
    "6. Use parameterized tests (pytest.mark.parametrize).\\n\\n"
    "Historical lessons:\\n"
    "{pitfalls}\\n"
)

# ============================================================
# Output Schema Constraint
# ============================================================
CODE_PACKAGE_SCHEMA = {
    "type": "object",
    "required": ["code", "logic_analysis", "test_coverage", "dependencies", "execution_command"],
    "properties": {
        "code": {
            "type": "object",
            "required": ["main", "tests"],
            "properties": {
                "main": {"type": "string"},
                "tests": {"type": "string"},
                "dockerfile": {"type": "string"}
            }
        },
        "logic_analysis": {"type": "string"},
        "test_coverage": {"type": "array", "items": {"type": "string"}},
        "dependencies": {"type": "array", "items": {"type": "string"}},
        "execution_command": {"type": "string"}
    }
}

# ============================================================
# Main Agent Class
# ============================================================
class KimiCodegenAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(
            api_key=api_key or os.getenv("MOONSHOT_API_KEY"),
            base_url=KimiCodegenConfig.BASE_URL
        )
        self.session_history: Dict[str, Any] = {}

    def generate(self, spec: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        Initial code generation (Round 1)
        """
        pitfalls = spec.get("pitfalls", [])
        pitfalls_text = "\\n".join([f"- {p}" for p in pitfalls]) if pitfalls else "- None"

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(pitfalls=pitfalls_text)

        # v1.0 Token optimization: compact JSON
        user_content = json.dumps(spec, ensure_ascii=False, separators=(',', ':'))

        response = self.client.chat.completions.create(
            model=KimiCodegenConfig.MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=KimiCodegenConfig.TEMPERATURE,
            max_tokens=KimiCodegenConfig.MAX_TOKENS,
            top_p=KimiCodegenConfig.TOP_P,
            response_format={"type": "json_object"}
        )

        session_id = f"sess-{int(time.time())}-{task_id}"
        self.session_history[session_id] = {
            "task_id": task_id,
            "round": 1,
            "spec": spec,
            "response": response
        }

        try:
            code_package = json.loads(response.choices[0].message.content)
            code_package["_meta"] = {
                "session_id": session_id,
                "round": 1,
                "model": KimiCodegenConfig.MODEL,
                "token_usage": response.usage.to_dict() if response.usage else None
            }
            return code_package
        except json.JSONDecodeError:
            return self._error_package(session_id, "JSON_PARSE_ERROR", response.choices[0].message.content)

    def fix(self, session_id: str, error_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Closed-loop fix (Round 2-3)
        """
        session = self.session_history.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        current_round = session["round"]
        if current_round >= KimiCodegenConfig.MAX_RETRY:
            return {
                "status": "ESCALATED",
                "session_id": session_id,
                "reason": "MAX_RETRY_EXCEEDED",
                "message": f"Reached v1.0 max retry limit {KimiCodegenConfig.MAX_RETRY}. Human required."
            }

        # v1.0 Token optimization: only send diff + key info
        fix_prompt = json.dumps(error_report, ensure_ascii=False, separators=(',', ':'))

        response = self.client.chat.completions.create(
            model=KimiCodegenConfig.MODEL,
            messages=[
                {"role": "system", "content": "Fix the error. Output ONLY corrected JSON code_package. No explanations."},
                {"role": "user", "content": fix_prompt}
            ],
            temperature=KimiCodegenConfig.TEMPERATURE,
            max_tokens=KimiCodegenConfig.MAX_TOKENS,
            top_p=KimiCodegenConfig.TOP_P,
            response_format={"type": "json_object"}
        )

        session["round"] += 1
        session["last_response"] = response

        try:
            code_package = json.loads(response.choices[0].message.content)
            code_package["_meta"] = {
                "session_id": session_id,
                "round": session["round"],
                "model": KimiCodegenConfig.MODEL,
                "token_usage": response.usage.to_dict() if response.usage else None
            }
            return code_package
        except json.JSONDecodeError:
            return self._error_package(session_id, "JSON_PARSE_ERROR", response.choices[0].message.content)

    def _error_package(self, session_id: str, error_type: str, raw_content: str) -> Dict[str, Any]:
        return {
            "status": "FAILED",
            "session_id": session_id,
            "error_type": error_type,
            "raw_content_preview": raw_content[:500],
            "message": "Kimi returned malformed JSON. Human review required."
        }

# ============================================================
# Example Usage
# ============================================================
if __name__ == "__main__":
    agent = KimiCodegenAgent(api_key=os.getenv("MOONSHOT_API_KEY"))

    with open("structured_spec.json", "r", encoding="utf-8") as f:
        spec = json.load(f)

    result = agent.generate(spec, task_id=spec["task_id"])

    if result.get("status") != "FAILED":
        # ... local sandbox test execution ...
        error_report = {
            "session_id": result["_meta"]["session_id"],
            "failed_test": "test_empty_sku_list",
            "error_type": "ASSERTION_ERROR",
            "error_line": 42,
            "expected": "validation_errors",
            "actual": "null",
            "hint": "Boundary condition empty sku_list not handled"
        }
        fixed = agent.fix(result["_meta"]["session_id"], error_report)
        print(json.dumps(fixed, ensure_ascii=False, indent=2))
