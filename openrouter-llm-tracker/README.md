---
title: "OpenRouter LLM Tracker — README.md"
name: "openrouter-llm-tracker"
description: "Human-readable skill guide. Daily auto-fetch OpenRouter LLM list, build registry, history, scoring system, test API connectivity, generate OpenClaw / WorkBuddy compatible model configs."
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
  local_path: "{baseDir}/README.md"
  github_path: "openrouter-llm-tracker/README.md"
---
# OpenRouter LLM Tracker

## 1. 技能概述

本技能負責與 OpenRouter 平台對接，持續追蹤其模型生態變化。核心價值在於將分散的模型資訊結構化為內部可用的註冊表，並透過評分機制動態調整模型的委任等級，最終輸出可直接餵入 OpenClaw 或 WorkBuddy 的 JSON 配置。新增 API 連通性測試功能，確保代理架構中配置的 LLM 可正常通訊。

## 2. 功能清單

| 功能編號 | 功能名稱 | 說明 |
|----------|----------|------|
| F-001 | LLM 列表獲取 | 調用 OpenRouter API，拉取當前所有模型元數據 |
| F-002 | LLM 紀錄存儲 | 將獲取的列表寫入註冊表與歷史快照 |
| F-003 | LLM 評分 | 根據使用評價提升/下降最高委任等級 |
| F-004 | OpenClaw 參數生成 | 輸入識別 ID 與參數類型，回傳 OpenClaw JSON config string |
| F-005 | WorkBuddy 參數生成 | 輸入識別 ID 與參數類型，回傳 WorkBuddy JSON config string |
| F-006 | LLM Curl 連通測試 | 使用 Python 直接測試 OpenRouter 平台連接，驗證 API key 與模型設定正確性 |

## 3. 數據模型與字段映射

### 3.1 核心註冊表字段 (model.json)

| 字段名稱 | JSON 路徑 | 類型 | 說明 | 示例 |
|----------|-----------|------|------|------|
| 識別 ID | models.id / agents.models.key | string | OpenRouter API 使用的模型 ID，含命名空間 | openai/gpt-oss-120b:free |
| 模型英文名稱 | models.name / models.alias | string | 官方英文顯示名稱 | GPT-OSS-120B |
| 模型中文名稱 | models.name_zh | string | 內部使用的中文名稱 | GPT 開源 120B |
| 供應商 | models.vendor | string | 模型開發商 | OpenAI |
| 地區 | models.region | string | 供應商總部所在地 | 美國 |
| LLM 類型 | models.llm_type | enum | 專責分類，見 3.2 | coding |
| 委任類型 | models.assignment_tier | enum | 模型在代理架構中的角色等級，見 3.3 | domain_expert |
| 上架日期 | models.release_date | string (YYYY-MM-DD) | OpenRouter 首次上架日期，可留空 | 2026-05-06 |
| 定價 Input | models.pricing.input_per_1m | number | 每百萬輸入 token 價格 (USD) | 0.0 |
| 定價 Output | models.pricing.output_per_1m | number | 每百萬輸出 token 價格 (USD) | 0.0 |
| Max Input tokens | models.context.max_input | integer | 最大輸入上下文長度 | 131072 |
| Max Output tokens | models.context.max_output | integer | 最大輸出長度 | 65536 |
| 支持工具 | models.capabilities.tools | boolean | 是否支援 function calling / tool use | true |
| 支持圖片 | models.capabilities.vision | boolean | 是否支援圖片/多模態輸入 | false |
| 思考等級 | models.capabilities.reasoning | enum | 深度思考能力等級，見 3.4 | high |

### 3.2 LLM 類型枚舉 (固定在 scripts/*.py 中)

| 枚舉值 | 說明 |
|--------|------|
| general | 通用對話型 |
| coding | 編碼專精型 |
| ocr | 文字識別專精型 |
| vision | 視覺理解專精型 |
| multimodal | 多模態通用型 |
| reasoning | 深度推理專精型 |
| agentic | 代理工作流專精型 |
| audio | 語音處理專精型 |

### 3.3 委任類型映射 (references/MAPPING.md 待定)

委任類型分為兩大類，具體映射規則由 references/MAPPING.md 定義，本技能預留接口待填充。

| 大類 | 子類 | 預設說明 |
|------|------|----------|
| Main Agent | omnipotent | 萬能型，可處理任何任務 |
| Main Agent | c_level | C-level 管理層級，戰略決策 |
| Main Agent | specialist_manager | 專項管理，負責特定領域統籌 |
| Main Agent | strategic_expert | 戰略專家，長期規劃與分析 |
| Sub Agent | domain_expert | 領域專家，單一領域深度處理 |
| Sub Agent | supervisor | 主管級，監督並協調下級代理 |
| Sub Agent | staff | 員工級，執行具體操作任務 |

### 3.4 思考等級枚舉 (固定在 scripts/*.py 中)

| 枚舉值 | 說明 |
|--------|------|
| false | 不支援深度思考 |
| low | 基礎推理能力 |
| medium | 中等推理深度 |
| high | 高階推理，支援 chain-of-thought |
| adaptive | 自適應推理，根據任務動態調整 |

## 4. 目錄結構

```
openrouter-llm-tracker/
├── readme/
│   └── SKILL.md                  # 人類閱讀版 (本文件)
├── LLM/
│   └── SKILL.md                  # LLM 執行指令版 (待生成)
├── scripts/
│   ├── llm.fetcher.py            # F-001: 調用 OpenRouter API 獲取模型列表
│   ├── llm.registry.py           # F-002: 註冊表讀寫與歷史快照管理
│   ├── llm.scorer.py             # F-003: 評分計算與委任等級調整
│   ├── llm.config.openclaw.py    # F-004: OpenClaw JSON config 生成
│   ├── llm.config.workbuddy.py   # F-005: WorkBuddy JSON config 生成
│   ├── llm.curl.py               # F-006: API 連通性測試與模型設定驗證
│   ├── USAGE.md                  # 腳本使用說明 (v1.2.2)
├── assets/
│   ├── llm.registry.json         # 當前模型主註冊表 (F-002 輸出)
│   ├── llm.scores.json          # 評分與委任等級 (F-003 輸出)
│   └── llm.history/             # 歷史快照目錄，按 YYYY-MM-DD 命名
│       ├── 2026-05-11.json
│       └── ...
├── references/
│   ├── MAPPING.md               # 委任等級映射規則 (待定，由主人填充)
│   └── RANKING.md               # 評分維度與權重定義 (待定，由主人填充)
└── .gitignore
```

## 5. 使用方式

### 5.1 前置條件

| 項目 | 要求 |
|------|------|
| Python | 3.10+ |
| 依賴 | requests, json, datetime, pathlib (標準庫為主) |
| API Key | OpenRouter API Key，由調用方以 string 形式傳入 |

### 5.2 調用接口

本技能不對外暴露 HTTP 服務，所有功能以 Python 函數形式供其他 agent / skill 調用。

```python
# 示例：由外部 agent 調用
from scripts.llm.fetcher import fetch_models
from scripts.llm.registry import save_registry, load_registry
from scripts.llm.scorer import update_score
from scripts.llm.config.openclaw import generate_openclaw_config
from scripts.llm.config.workbuddy import generate_workbuddy_config
from scripts.llm.curl import test_model_connectivity

# F-001: 獲取最新列表
models = fetch_models(api_key="sk-or-v1-...")

# F-002: 寫入註冊表與歷史
save_registry(models, data_dir="openrouter-llm-tracker/data/")

# F-003: 評分更新
update_score(
    model_id="openai/gpt-oss-120b:free",
    dimensions={"latency": 95, "accuracy": 88},
    data_dir="openrouter-llm-tracker/data/"
)

# F-004: 生成 OpenClaw config string
config_str = generate_openclaw_config(
    model_id="openai/gpt-oss-120b:free",
    param_type="agentic",  # 或 "general", "vision", "reasoning"
    registry_path="openrouter-llm-tracker/data/llm.registry.json"
)
# config_str 為 JSON string，直接回傳給需要的 agent

# F-005: 生成 WorkBuddy config string
config_str = generate_workbuddy_config(
    model_id="baidu/cobuddy:free",
    param_type="coding",
    registry_path="openrouter-llm-tracker/data/llm.registry.json"
)

# F-006: 測試 API 連通性
result = test_model_connectivity(
    api_key="sk-or-v1-...",
    model_id="openai/gpt-oss-120b:free",
    test_prompt="Hello, this is a connectivity test.",
    max_tokens=50
)
# result 為 dict，包含 status / latency_ms / response_text / error 等字段
```

### 5.3 輸出規範

| 功能 | 輸出形式 | 說明 |
|------|----------|------|
| F-001 | Python dict list | 模型元數據列表 |
| F-002 | JSON file | 寫入 assets/ 目錄 |
| F-003 | JSON file | 更新 data/llm.scores.json |
| F-004 | JSON string | 不回寫文件，直接 string 回傳 |
| F-005 | JSON string | 不回寫文件，直接 string 回傳 |
| F-006 | Python dict | 包含連通性測試結果與診斷資訊 |

## 6. F-006 LLM Curl 連通測試詳細說明

### 6.1 測試流程

```
[調用方] → llm.curl.py → [OpenRouter API: /api/v1/chat/completions]
                                      ↓
                              發送最小測試請求 (1-3 tokens)
                                      ↓
                              記錄響應時間、HTTP 狀態碼、錯誤碼
                                      ↓
                              解析響應，驗證模型名稱是否匹配
                                      ↓
                              [調用方] ← 返回測試結果 dict
```

### 6.2 測試結果結構

| 字段 | 類型 | 說明 |
|------|------|------|
| status | string | "success" / "error" / "timeout" / "rate_limited" / "auth_failed" |
| model_id | string | 被測試的模型 ID |
| latency_ms | integer | 從发送請求到收到首 token 的時間 (毫秒) |
| total_latency_ms | integer | 完整響應時間 (毫秒) |
| http_status | integer | HTTP 狀態碼 |
| response_text | string | 模型返回的測試文本 |
| token_usage | dict | {input_tokens, output_tokens, total_tokens} |
| error_code | string | OpenRouter 錯誤碼 (如有) |
| error_message | string | 人類可讀的錯誤描述 (如有) |
| model_matched | boolean | 響應中的 model 字段是否與請求的 model_id 一致 |
| timestamp | string | ISO 8601 測試時間戳 |

### 6.3 錯誤碼映射

| OpenRouter 錯誤碼 | 對應 status | 建議處理 |
|---------------------|-------------|----------|
| 401 / 403 | auth_failed | 檢查 API key 是否正確或已過期 |
| 404 | error | 模型 ID 不存在或已下架 |
| 429 | rate_limited | 等待後重試，或切換付費 tier |
| 502 / 503 | error | 供應商端暫時不可用，記錄並告警 |
| 524 | timeout | 增加超時時間或標記模型為不穩定 |
| 200 但空響應 | error | 模型可能處於維護模式 |

## 7. OpenClaw / WorkBuddy 配置格式說明

配置格式已寫死在對應的 scripts/*.py 中，不允許外部動態修改。具體 JSON schema 由腳本內部定義，確保與 OpenClaw / WorkBuddy 的接口版本兼容。

### 7.1 OpenClaw 配置結構 (F-004)

基於用戶提供的字段映射，生成的 JSON 包含以下節點：

```json
{
  "agents": {
    "models": {
      "key": "openai/gpt-oss-120b:free",
      "name": "GPT-OSS-120B",
      "alias": "GPT-OSS-120B",
      "vendor": "OpenAI",
      "region": "美國",
      "llm_type": "agentic",
      "assignment_tier": "domain_expert",
      "capabilities": {
        "tools": true,
        "vision": false,
        "reasoning": "high"
      },
      "context": {
        "max_input": 131072,
        "max_output": 65536
      },
      "pricing": {
        "input_per_1m": 0.0,
        "output_per_1m": 0.0
      },
      "release_date": "2026-05-06"
    }
  }
}
```

### 7.2 WorkBuddy 配置結構 (F-005)

WorkBuddy 的配置格式參照其官方模型定義規範，由腳本內部 schema 定義，輸出為可直接導入 WorkBuddy 的 JSON string。

## 8. 評分系統說明

### 8.1 評分維度 (references/RANKING.md 待定)

預留五個維度接口，具體權重與計算公式由 references/RANKING.md 定義：

| 維度 ID | 維度名稱 | 說明 |
|---------|----------|------|
| latency | 延遲表現 | 首 token 時間與總生成時間 |
| accuracy | 準確率 | 任務完成正確性 |
| tool_reliability | 工具可靠性 | function calling 成功率與穩定性 |
| cost_efficiency | 成本效益 | 單位任務的 token 消耗與費用 |
| context_stability | 上下文穩定性 | 長上下文下的表現一致性 |

### 8.2 委任等級調整邏輯

評分更新後，腳本根據 RANKING.md 定義的閾值自動判斷是否升級或降級委任類型。調整記錄寫入 llm.scores.json 的 history 陣列中，保留審計軌跡。

## 9. 數據目錄規範

`/data/` 目錄存放運行時生成的數據（llm.registry.json、llm.scores.json、history/ 等），**不入版本庫**，**不參與上傳**。

github-skill-organizer 上傳時會自動排除 `/data/` 目錄。

## 9. 待確認項

| 項目 | 狀態 | 負責方 |
|------|------|--------|
| references/MAPPING.md | 待定 | 主人 |
| references/RANKING.md | 待定 | 主人 |
| scripts/USAGE.md | 已接收 ✅ (v1.2.2) | Kevin Lin |
| LLM/SKILL.md | 待生成 | Kimi (待主人通知) |
| scripts/llm.fetcher.py | 待生成 | Kimi (待主人通知) |
| scripts/llm.registry.py | 待生成 | Kimi (待主人通知) |
| scripts/llm.scorer.py | 待生成 | Kimi (待主人通知) |
| scripts/llm.config.openclaw.py | 待生成 | Kimi (待主人通知) |
| scripts/llm.config.workbuddy.py | 待生成 | Kimi (待主人通知) |
| scripts/llm.curl.py | 待生成 | Kimi (待主人通知) |

## 10. 版本記錄

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2026-05-11 | 初始版本，框架定義與字段映射確認 |
| 1.1.0 | 2026-05-12 | 新增 F-006 LLM Curl 連通測試功能 |
| 1.2.0 | 2026-05-13 | 接收用戶提供的 llm.config.openclaw.py、llm.config.workbuddy.py、SKILL.md 更新 |
| 1.2.1 | 2026-05-13 | 修復 llm.curl.py batch_results 類型註釋 |
| 1.2.2 | 2026-05-14 | USAGE.md v1.2.2：補齊用法指南、修正 OpenClaw 路徑、新增 WorkBuddy 平台路徑備註、強化 Path Rigidity Rule |

---

*技能包名稱: openrouter-llm-tracker*  
*命名規範: 統一使用點號 (.) 作為分隔符，禁止使用中劃線 (-) 或下劃線 (_) 於檔案名稱中*  
*輸出格式: 所有 markdown 文件禁止在多行描述中使用大於號 (>) 折疊語法，強制輸出為單行*