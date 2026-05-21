# USAGE.md — kimi_codegen.py 使用說明

> 版本：v1.2.0（對齊 agent-swarm-kimi-codegen v1.2.0）
> 位置：`scripts/USAGE.md`

---

## 版本對齊表

| 文件 | 版本 | 用途 |
|------|------|------|
| kimi_codegen.py | v1.2.0 | Moonshot API 調用、避坑注入、閉環修正、Schema 驗證 |
| LLM/SKILL.md | v1.2.0 | Codegen 執行指令集 |
| readme/SKILL.md | v1.2.0 | 人類可讀解釋書 |
| USAGE.md | v1.2.0 | 本文件：腳本用法說明 |

---

## 快速開始

### 1. 注入避坑經驗

```python
from kimi_codegen import inject_pitfalls

pitfalls = inject_pitfalls(
    skill_corrections=Path("assets/SKILL_CORRECTIONS.md"),
    script_corrections=Path("assets/SCRIPT_CORRECTIONS.md"),
    historical_corrections=Path("assets/CORRECTION.md"),
    max_pitfalls=10
)

print(pitfalls)
# ['邊界條件：sku_list 為空時必須返回 validation_errors', '依賴版本：pandas 必須鎖定 >=2.0.0', ...]
```

### 2. 初始代碼生成（Round 1）

```python
from kimi_codegen import KimiCodegenAgent

agent = KimiCodegenAgent(api_key=os.getenv("MOONSHOT_API_KEY"))

spec = {
    "task_id": "T20260511",
    "description": "生成條碼校驗算法",
    "input_schema": {"barcode": "string"},
    "output_schema": {"valid": "boolean", "error": "string"},
    "test_matrix": ["empty", "valid", "invalid_checksum", "max_length"],
    "pitfalls": ["條碼長度必須為 13 位", "校驗位算法必須符合 EAN-13 標準"]
}

result = agent.generate(
    spec=spec,
    task_id="T20260511",
    pitfalls=pitfalls
)

print(result)
# {
#     "status": "GENERATED",
#     "session_id": "sess-1234567890-T20260511",
#     "round": 1,
#     "code_package": {...},
#     "token_usage": {"prompt": 1500, "completion": 2000, "total": 3500},
#     "warning": None
# }
```

### 3. Schema 驗證

```python
from kimi_codegen import validate_schema

validation = validate_schema(result["code_package"])

print(validation)
# {
#     "valid": True,
#     "missing_fields": [],
#     "error": None,
#     "warning": None
# }
```

### 4. 閉環修正（Round 2-3）

```python
error_report = {
    "failed_test": "test_empty_barcode",
    "error_type": "ASSERTION_ERROR",
    "error_line": 15,
    "expected": "{'valid': False, 'error': 'EMPTY_BARCODE'}",
    "actual": "{'valid': True, 'error': None}",
    "hint": "空條碼時應返回 valid=False"
}

fixed = agent.fix(
    session_id=result["session_id"],
    error_report=error_report
)

print(fixed)
# {
#     "status": "FIXED",
#     "session_id": "sess-1234567890-T20260511",
#     "round": 2,
#     "code_package": {...},
#     "token_usage": {"prompt": 500, "completion": 800, "total": 1300}
# }
```

### 5. 會話信息查詢

```python
session_info = agent.get_session_info(result["session_id"])
print(f"當前輪次: {session_info.get('round')}")
print(f"歷史錯誤: {session_info.get('last_error_report')}")
```

### 6. 內容完整性預檢

```python
from kimi_codegen import check_content_integrity

result = check_content_integrity(
    content="準備寫入的完整內容...",
    expected_length=500
)
```

---

## 標準整合模板（Agent 直接複用）

```python
import os
from pathlib import Path
from kimi_codegen import (
    KimiCodegenAgent,
    inject_pitfalls,
    validate_schema
)

# 步驟 1：注入避坑經驗
pitfalls = inject_pitfalls(
    skill_corrections=Path("assets/SKILL_CORRECTIONS.md"),
    script_corrections=Path("assets/SCRIPT_CORRECTIONS.md")
)

# 步驟 2：創建 Agent
agent = KimiCodegenAgent(api_key=os.getenv("MOONSHOT_API_KEY"))

# 步驟 3：初始生成
code_package = agent.generate(
    spec=structured_spec,
    task_id=task_id,
    pitfalls=pitfalls
)

# 步驟 4：Schema 驗證
validation = validate_schema(code_package["code_package"])
if not validation["valid"]:
    print(validation["error"])
    # 上報 coordinator

# 步驟 5：本地沙箱測試（模擬）
# ... 執行 pytest ...

# 步驟 6：如有錯誤，閉環修正
if test_failed:
    for round_num in range(2, 4):  # Round 2-3
        fixed = agent.fix(
            session_id=code_package["session_id"],
            error_report=error_report
        )
        if fixed["status"] == "ESCALATED":
            print("[ESCALATED] 需人工介入")
            break
        # 重新測試...

# 步驟 7：交付 Generator
print("[CODEGEN-COMPLETE]")
```

---

## 輸出文件規範

| 文件類型 | 命名格式 | 存放位置 | 說明 |
|---------|---------|---------|------|
| 代碼包 | `code_package_{session_id}.json` | `assets/` | Kimi 返回的 JSON |
| 會話記錄 | 內部 `session_history` | 內存 | 追蹤輪次和 Token |

---

## 常見問題

**Q：API Key 如何配置？**
A：設置環境變數 `MOONSHOT_API_KEY`，或在創建 `KimiCodegenAgent` 時傳入 `api_key` 參數。

**Q：閉環修正超過 3 輪怎麼辦？**
A：自動輸出 `[ESCALATED]`，上報主人。禁止繼續第 4 輪。

**Q：Schema 驗證失敗能否手動修復？**
A：可以，但必須記錄修復原因到 CORRECTION.md，並在下次改進時反饋給 Kimi。

---

*最後更新：2026-05-11*
