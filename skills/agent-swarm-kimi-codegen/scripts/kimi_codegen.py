"""
kimi_codegen.py v1.2.0
Agent Swarm Kimi Codegen 配套腳本
Moonshot API 調用、避坑經驗注入、閉環修正、Token 優化、JSON Schema 驗證

用法:
    from kimi_codegen import (
        KimiCodegenAgent,
        inject_pitfalls,
        validate_schema,
        check_content_integrity
    )
"""

import os
import re
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

__version__ = "1.2.0"

# ============================================================
# Config (v1.2.0 locked — 對齊 LLM/SKILL.md)
# ============================================================
class KimiCodegenConfig:
    MODEL = "kimi-k2.6"
    TEMPERATURE = 0.1
    MAX_TOKENS = 16000
    TOP_P = 0.95
    BASE_URL = "https://api.moonshot.ai/v1"
    MAX_RETRY = 3
    MAX_ROUNDS = 3  # 閉環修正上限
    TIMEOUT_SECONDS = 120


# ============================================================
# JSON Schema 定義（強制輸出格式）
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
# 避坑經驗注入
# ============================================================
def inject_pitfalls(
    skill_corrections: Optional[Path] = None,
    script_corrections: Optional[Path] = None,
    historical_corrections: Optional[Path] = None,
    max_pitfalls: int = 10
) -> List[str]:
    """
    從 CORRECTION 文件讀取避坑經驗

    Args:
        skill_corrections: SKILL_CORRECTIONS.md 路徑
        script_corrections: SCRIPT_CORRECTIONS.md 路徑
        historical_corrections: 歷史 CORRECTION.md 路徑
        max_pitfalls: 最多注入幾條經驗

    Returns:
        list: 避坑經驗字符串列表
    """
    pitfalls = []
    sources = [skill_corrections, script_corrections, historical_corrections]

    for source in sources:
        if source and Path(source).exists():
            with open(source, "r", encoding="utf-8") as f:
                content = f.read()
            # 簡易提取：找 "- **" 開頭的行
            lines = content.split("\n")
            for line in lines:
                if line.strip().startswith("- **") and len(pitfalls) < max_pitfalls:
                    pitfalls.append(line.strip().lstrip("- ").strip())

    if not pitfalls:
        pitfalls.append("無歷史避坑經驗，請確保邊界條件和異常處理完善")

    return pitfalls


# ============================================================
# System Prompt 模板（Context Caching 優化）
# ============================================================
SYSTEM_PROMPT_TEMPLATE = (
    "You are a professional retail system code subcontractor.\n"
    "Task: Generate code and tests based on structured_spec.\n"
    "Constraints:\n"
    "1. Output ONLY JSON. No Markdown or explanations.\n"
    "2. Code MUST conform to input/output Schema.\n"
    "3. MUST cover ALL boundary conditions (see spec.test_matrix).\n"
    "4. Pitfalls (see below) MUST be embedded in code logic.\n"
    "5. Comments ONLY for 'why', not 'what'. No verbose docs.\n"
    "6. Use parameterized tests (pytest.mark.parametrize).\n\n"
    "Historical lessons:\n"
    "{pitfalls}\n"
)


# ============================================================
# Schema 驗證
# ============================================================
def validate_schema(code_package: Dict[str, Any]) -> Dict[str, Any]:
    """
    驗證 code_package 是否符合 JSON Schema

    Args:
        code_package: Kimi 返回的代碼包

    Returns:
        dict: {valid, missing_fields, error, warning}
    """
    required = CODE_PACKAGE_SCHEMA["required"]
    missing = []

    for field in required:
        if field not in code_package:
            missing.append(field)

    # 檢查 code 子欄位
    if "code" in code_package:
        code_required = CODE_PACKAGE_SCHEMA["properties"]["code"]["required"]
        for sub_field in code_required:
            if sub_field not in code_package["code"]:
                missing.append(f"code.{sub_field}")

    valid = len(missing) == 0

    return {
        "valid": valid,
        "missing_fields": missing,
        "error": None if valid else f"[SCHEMA-MISSING] 缺少欄位: {', '.join(missing)}",
        "warning": None
    }


# ============================================================
# 主 Agent 類
# ============================================================
class KimiCodegenAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MOONSHOT_API_KEY")
        self.base_url = KimiCodegenConfig.BASE_URL
        self.session_history: Dict[str, Any] = {}

    def generate(self, spec: Dict[str, Any], task_id: str, pitfalls: List[str]) -> Dict[str, Any]:
        """
        Round 1: 初始代碼生成

        Args:
            spec: structured_spec（代碼需求規格）
            task_id: 任務編號
            pitfalls: 避坑經驗列表

        Returns:
            dict: code_package 或錯誤包
        """
        pitfalls_text = "\n".join([f"- {p}" for p in pitfalls]) if pitfalls else "- None"
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(pitfalls=pitfalls_text)

        # Token 優化：compact JSON
        user_content = json.dumps(spec, ensure_ascii=False, separators=(',', ':'))

        # 調用 API（簡化實現，實際需使用 openai 庫）
        # 此處為結構化返回模板
        session_id = f"sess-{int(time.time())}-{task_id}"

        self.session_history[session_id] = {
            "task_id": task_id,
            "round": 1,
            "spec": spec,
            "pitfalls": pitfalls,
            "system_prompt": system_prompt,
            "user_content": user_content
        }

        # 模擬返回（實際需替換為真實 API 調用）
        return {
            "status": "GENERATED",
            "session_id": session_id,
            "round": 1,
            "code_package": {
                "code": {"main": "", "tests": "", "dockerfile": ""},
                "logic_analysis": "",
                "test_coverage": [],
                "dependencies": [],
                "execution_command": ""
            },
            "token_usage": {"prompt": 0, "completion": 0, "total": 0},
            "warning": None
        }

    def fix(self, session_id: str, error_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Round 2-3: 閉環修正

        Args:
            session_id: 會話 ID
            error_report: 錯誤報告 {failed_test, error_type, error_line, expected, actual, hint}

        Returns:
            dict: 修正後 code_package 或 [ESCALATED]
        """
        session = self.session_history.get(session_id)
        if not session:
            return {
                "status": "FAILED",
                "session_id": session_id,
                "error": f"[SESSION-NOT-FOUND] 會話 {session_id} 不存在"
            }

        current_round = session.get("round", 1)
        if current_round >= KimiCodegenConfig.MAX_ROUNDS:
            return {
                "status": "ESCALATED",
                "session_id": session_id,
                "reason": "MAX_ROUNDS_EXCEEDED",
                "message": f"已達 v{__version__} 最大修正輪次 {KimiCodegenConfig.MAX_ROUNDS}，需人工介入"
            }

        # Token 優化：只傳輸 error_report（Diff 傳輸）
        fix_prompt = json.dumps(error_report, ensure_ascii=False, separators=(',', ':'))

        session["round"] = current_round + 1
        session["last_error_report"] = error_report
        session["last_fix_prompt"] = fix_prompt

        # 模擬返回
        return {
            "status": "FIXED",
            "session_id": session_id,
            "round": session["round"],
            "code_package": {
                "code": {"main": "", "tests": "", "dockerfile": ""},
                "logic_analysis": "",
                "test_coverage": [],
                "dependencies": [],
                "execution_command": ""
            },
            "token_usage": {"prompt": 0, "completion": 0, "total": 0},
            "warning": None
        }

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """獲取會話信息"""
        return self.session_history.get(session_id, {})


# ============================================================
# 內容完整性預檢
# ============================================================
def check_content_integrity(content: str, expected_length: int = 0) -> Dict[str, Any]:
    """
    內容完整性預檢（供 LLM 調用前自檢）

    Args:
        content: 準備寫入的內容
        expected_length: 畫面上實際輸出的字數預期

    Returns:
        dict: {is_complete, actual_length, expected_length, ratio, warning}
    """
    actual_length = len(content)
    ratio = actual_length / expected_length if expected_length > 0 else 1.0
    is_complete = ratio >= 0.9

    warning = None
    if expected_length > 0 and ratio < 0.9:
        warning = (
            f"[CONTENT-INCOMPLETE-WARNING] 記錄長度 {actual_length} < 預期 {expected_length} "
            f"（達成率 {ratio:.1%}）。禁止傳入摘要，必須傳入完整內容。"
        )

    return {
        "is_complete": is_complete,
        "actual_length": actual_length,
        "expected_length": expected_length,
        "ratio": ratio,
        "warning": warning
    }


if __name__ == "__main__":
    print(f"kimi_codegen.py v{__version__} 已載入")
    print(f"模型: {KimiCodegenConfig.MODEL}")
    print(f"溫度: {KimiCodegenConfig.TEMPERATURE}")
    print(f"最大 Token: {KimiCodegenConfig.MAX_TOKENS}")
    print(f"閉環修正上限: {KimiCodegenConfig.MAX_ROUNDS} 輪")
