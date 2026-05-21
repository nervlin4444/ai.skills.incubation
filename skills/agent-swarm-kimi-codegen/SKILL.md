---
id: agent-swarm-kimi-codegen
version: v1.2.0
description: "Kimi代碼分包。執行Moonshot API調用、避坑經驗注入、閉環修正3輪、Context Caching Token優化、JSON Schema強制輸出、交付Generator。"
author: Kevin Lin
skill_bundle: agent-harness-by-kevinlinz
tags: [swarm-kimi, codegen, LLM-execution, api-subcontractor]
---

## 🔴 身份分流（讀到這裡立即停止，不要往下讀）

### 若你是 Sub-Agent（L1 / L2 / L3）且非 Codegen 角色
本文件與你無關。你已從任命書獲得任務，直接執行即可。
**禁止繼續閱讀以下內容**
立即停止。關閉本文件。去執行你的任務。

### 若你是 Main Agent（L0）或 Codegen（L1 Sub-Agent）
繼續閱讀以下內容。本文件是你的執行指令。

---

## ⚠️ 認知糾偏（僅 Codegen 閱讀）

### 錯誤理解
❌ "Kimi Codegen 可以生成任何代碼"
❌ "閉環修正可以無限進行"
❌ "避坑經驗可以憑空編造"
❌ "JSON Schema 可以靈活調整"
❌ "Token 優化不重要，準確性優先"

### 正確理解
✅ 只有複雜算法或生產級代碼才分包，簡單腳本本地生成
✅ 最多 3 輪自動修正，第 4 輪必須上報主人
✅ 避坑經驗必須來自真實 SKILL_CORRECTIONS.md / SCRIPT_CORRECTIONS.md
✅ Schema 必須固定，禁止調整，下游工具依賴固定欄位
✅ Token 優化和準確性並不矛盾，Context Caching 和 Diff 傳輸兼顧兩者

---

## 🔴 口訣（條件反射，無需理解語義）

    注。調。修。交。

含義：注入避坑 → 調用 API → 修正錯誤 → 交付代碼。

---

## 🚨 立即執行（8 個步驟）

### [ ] 步驟 1：身份確認
- 檢查任命書角色：必須是「Codegen / 代碼分包專家」
- 若角色不符 → 輸出 [IDENTITY-ERROR] 並停止
- 確認層級標記：L1（Codegen 只能是 L1，禁止 L2+）

### [ ] 步驟 2：載入家族手冊（5 項強制勾選）
- [ ] agent-bootstrap（身份判斷）
- [ ] agent-conversation-mode（對話記錄）
- [ ] agent-coordination-mode（任務路由）
- [ ] SKILL_CORRECTIONS.md（錯誤避免）
- [ ] SCRIPT_CORRECTIONS.md（腳本錯誤避免）
- 缺少任何一項 → 輸出 [FAMILY-MANUAL-MISSING] 並停止

### [ ] 步驟 3：接收分包需求
從 Generator 或 coordinator 接收：
- [ ] structured_spec（代碼需求規格，JSON 格式）
- [ ] task_id（任務編號，用於追蹤會話）
- [ ] 代碼複雜度評估（確認是否需要分包）

**分包門檻**：
- 代碼行數 > 50 行 → 建議分包
- 涉及算法邏輯 → 必須分包
- 需要單元測試覆蓋 > 80% → 必須分包
- 簡單腳本（< 50 行，無複雜邏輯）→ 本地生成，不分包

### [ ] 步驟 4：注入避坑經驗
使用腳本 `kimi_codegen.py` 讀取並注入：
```python
from kimi_codegen import inject_pitfalls

pitfalls = inject_pitfalls(
    skill_corrections=Path("assets/SKILL_CORRECTIONS.md"),
    script_corrections=Path("assets/SCRIPT_CORRECTIONS.md"),
    historical_corrections=Path("assets/CORRECTION.md")
)
```

注入內容必須包含：
- [ ] 邊界條件教訓（空值、最大值、負數、極端輸入）
- [ ] 依賴版本教訓（必須鎖定的版本號）
- [ ] 異常處理教訓（超時、重試、降級策略）
- [ ] 測試覆蓋教訓（必須包含的測試類型）

**禁止**：憑空編造避坑經驗。必須來自真實記錄。

### [ ] 步驟 5：調用 Moonshot API（Round 1）
使用腳本 `kimi_codegen.py` 調用：
```python
from kimi_codegen import KimiCodegenAgent

agent = KimiCodegenAgent(api_key=os.getenv("MOONSHOT_API_KEY"))
code_package = agent.generate(
    spec=structured_spec,
    task_id=task_id,
    pitfalls=pitfalls
)
```

**API 參數（禁止修改）**：
- [ ] 模型：kimi-k2.6
- [ ] temperature：0.1
- [ ] max_tokens：16000
- [ ] top_p：0.95
- [ ] response_format：{"type": "json_object"}
- [ ] System Prompt：啟用 Context Caching

**輸出驗證**：
- [ ] 必須是合法 JSON
- [ ] 必須包含所有 required 欄位（code / logic_analysis / test_coverage / dependencies / execution_command）
- [ ] code.main 和 code.tests 不能為空

### [ ] 步驟 6：本地沙箱測試
在交付 Generator 前，必須本地測試：
- [ ] 執行 code.tests（pytest）
- [ ] 檢查測試覆蓋率是否達標
- [ ] 記錄失敗測試到 error_report

**測試通過** → 進入步驟 8（交付）
**測試失敗** → 進入步驟 7（閉環修正）

### [ ] 步驟 7：閉環修正（Round 2-3）
使用腳本 `kimi_codegen.py` 修正：
```python
error_report = {
    "failed_test": "test_empty_sku_list",
    "error_type": "ASSERTION_ERROR",
    "error_line": 42,
    "expected": "validation_errors",
    "actual": "null",
    "hint": "Boundary condition empty sku_list not handled"
}

fixed_package = agent.fix(
    session_id=code_package["_meta"]["session_id"],
    error_report=error_report
)
```

**修正規則**：
- [ ] 只傳輸 error_report（Diff 傳輸，不重傳完整 spec）
- [ ] 記錄當前輪次（Round 2 / Round 3）
- [ ] 修正後重新執行沙箱測試
- [ ] Round 3 後仍有錯誤 → 輸出 [ESCALATED] → 上報主人

### [ ] 步驟 8：交付 Generator
- [ ] 輸出 code_package（JSON 格式）
- [ ] 輸出 logic_analysis（Markdown 格式，供 Evaluator QC）
- [ ] 輸出 test_coverage 清單（供驗收核對）
- [ ] 標記 [CODEGEN-COMPLETE]
- [ ] 將會話記錄（session_id / 輪次 / Token 消耗）傳遞給 coordinator

---

## ❌ 紅線（觸碰即錯）

- [ ] 禁止生成簡單腳本（< 50 行）也分包（浪費 Token）
- [ ] 禁止閉環修正超過 3 輪
- [ ] 禁止憑空編造避坑經驗
- [ ] 禁止調整 JSON Schema（固定欄位）
- [ ] 禁止修改 API 參數（模型/temperature/max_tokens 已鎖定）
- [ ] 禁止不測試就交付
- [ ] 禁止輸出 Markdown 圍欄（必須純 JSON）
- [ ] 禁止遺漏 session_id 和輪次記錄

---

## ⚡ 異常處理（條件反射）

### 異常 1：身份確認失敗
- 觸發：任命書角色不是 Codegen
- 動作：輸出 [IDENTITY-ERROR] → 停止
- 禁止：繼續執行本 skill

### 異常 2：API 調用失敗
- 觸發：Moonshot API 返回錯誤（超時、限流、認證失敗）
- 動作：
  1. 重試最多 3 次（指數退避間隔）
  2. 若仍失敗 → 輸出 [API-FAILURE] → 上報主人
- 禁止：無限重試

### 異常 3：JSON 解析失敗
- 觸發：Kimi 返回內容無法解析為合法 JSON
- 動作：
  1. 嘗試提取 JSON 片段（正則匹配）
  2. 若仍失敗 → 輸出 [JSON-PARSE-ERROR] → 上報主人
- 禁止：將錯誤內容當作合法輸出傳遞

### 異常 4：Schema 欄位缺失
- 觸發：code_package 缺少 required 欄位
- 動作：輸出 [SCHEMA-MISSING] → 列出缺失欄位 → Round 2 修正
- 禁止：傳遞不完整的 code_package

### 異常 5：閉環修正超過 3 輪
- 觸發：Round 3 後仍有錯誤
- 動作：輸出 [ESCALATED] → 累積錯誤報告 → 上報主人
- 禁止：繼續第 4 輪自動修正

### 異常 6：Token 消耗異常
- 觸發：單次調用消耗 Token > 10000
- 動作：輸出 [TOKEN-ALERT] → 建議拆分任務 → 上報主人
- 禁止：不報告繼續執行

---

## 🔒 版本鎖定

🔒 LOCK v1.2.0 PERMANENT — API 參數（模型/temperature/max_tokens）、JSON Schema、閉環修正上限（3輪）禁止修改

---

## 附錄 A：API 參數快速對照

| 參數 | 值 | 說明 |
|------|-----|------|
| 模型 | kimi-k2.6 | 固定 |
| temperature | 0.1 | 低溫度，高確定性 |
| max_tokens | 16000 | 固定上限 |
| top_p | 0.95 | 固定 |
| response_format | {"type": "json_object"} | 強制 JSON |
| base_url | https://api.moonshot.ai/v1 | 固定 |

## 附錄 B：JSON Schema 定義

```json
{
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
```

## 附錄 C：閉環修正狀態流轉

```
Round 1: generate() → 本地測試
    ├──→ 通過 → 交付
    └──→ 失敗 → Round 2: fix()
            ├──→ 通過 → 交付
            └──→ 失敗 → Round 3: fix()
                    ├──→ 通過 → 交付
                    └──→ 失敗 → [ESCALATED] 上報主人
```

## 附錄 D：Token 優化策略

| 策略 | 實施方式 | 節省比例 |
|------|---------|---------|
| Context Caching | System Prompt 緩存 | 30-50% |
| Compact JSON | separators=(',', ':') | 10-15% |
| Diff 傳輸 | 修正輪次只傳 error_report | 40-60% |
| Response Format 強制 | 減少格式無效重試 | 20-30% |

---

*LLM 執行指令集 v1.2.0*
*禁止修改核心流程*
