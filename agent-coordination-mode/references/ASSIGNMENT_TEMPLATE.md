---
title: Sub-Agent Appointment Template
name: agent-coordination-mode
description: Standard appointment template for coordinator to appoint Sub-Agents. Ensures original requirements are unmodified, experience constraints are fully passed, layer markers and family manual confirmation are complete.
version: v1.3.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T09:26:53+08:00
fixes: []
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/ASSIGNMENT_TEMPLATE.md"
  github_path: "agent-coordination-mode/references/ASSIGNMENT_TEMPLATE.md"
---

# ASSIGNMENT_TEMPLATE.md — 協調者任命書模板

## 文件定位

| 檔案 | 讀者 | 用途 |
|------|------|------|
| 本模板 | 協調者（Main Agent） | 生成任命書時的標準格式參考 |
| 任命書實例 | Sub-Agent（被任命者） | 接收任務、確認職責、執行後回報 |

本模板為 reference/ 下的格式規範文件，LLM 在生成任命書時參考但不直接執行本模板。

## 任命書結構（強制欄位）

```markdown
# APPOINTMENT — 任命書

## 1. 層級標記（強制）
當前層級：L0 / L1 / L2 / L3（已批准）
任命者：Main Agent（L0）/ Sub-Agent（L1+）
被任命者層級：L1 / L2 / L3

## 2. 原始需求（一字不改，直接複製用戶輸入）
[用戶原始輸入，完整保留，不摘要、不改寫]

## 3. 需求素材（協調者整理，不添加、不刪減）
- 查詢目標：[從原始需求提取]
- 時間範圍：[從原始需求提取]
- 輸出要求：[從原始需求提取]
- 來源要求：[從原始需求提取]

## 4. 經驗約束（從 SKILL_CORRECTIONS.md / SCRIPT_CORRECTIONS.md 讀取，強制傳遞）
| 嚴重度 | 約束 | 來源 |
|--------|------|------|
| P0 | [禁止行為] | [坑編號] |
| P1 | [注意事項] | [坑編號] |

## 5. 角色定義（強制）
- 被任命者角色：[戰略大師 / 專業調查員 / 系統工程師 / 收尾專員 / 自定義專家]
- 職責：[一句話說明，不超過 30 字]
- 輸出物：[預期輸出文件/格式]
- 參考專家：[從 EXPERT_LIST.md 選擇，如適用]

## 6. 家族手冊載入確認（強制）
被任命者必須載入以下技能（勾選確認）：
- [ ] agent-bootstrap（執行鏈初始化、身份判斷）
- [ ] agent-conversation-mode（對話記錄、契約區規則）
- [ ] agent-coordination-mode（任務路由、協調者職責）
- [ ] 自身專屬 SKILL.md（執行規範）

**禁止**：無家族手冊載入確認的任命書視為無效，被任命者應拒絕執行。

## 7. 層級限制聲明（強制）
- 當前層級：[L0 / L1 / L2]
- 可召喚 Sub-Agent：[是（最多到 L2）/ 否]
- 如需 L3：[必須向 Main Agent 申請，禁止擅自召喚]

## 8. 驗證清單（被任命者完成後勾選）
- [ ] 輸出是否偏離原始需求？
- [ ] 是否遵守了所有 P0 約束？
- [ ] 輸出格式是否符合預期？
- [ ] 是否已載入家族手冊並確認 [BOOTSTRAP] 已鎖定？
- [ ] 對話是否已記錄到 conversation.md？

## 9. 協調者聲明
本任命書未修改原始需求，僅添加經驗約束與層級標記。
如輸出偏離需求，責任追溯：先查任命書傳遞是否丟失，再查被任命者理解是否錯誤。
```

## 使用規範

### 協調者生成任命書時
1. 只複製、不創造、不摘要、不改寫原始需求
2. 必須包含層級標記（L1 / L2 / L3）
3. 必須包含家族手冊載入確認（4 項勾選）
4. 必須包含層級限制聲明

### 被任命者接收任命書時
1. 先讀「層級標記」→ 確認自己的身份和限制
2. 再讀「家族手冊載入確認」→ 逐項勾選載入
3. 再讀「原始需求」→ 理解任務目標
4. 再讀「經驗約束」→ 了解紅線
5. 最後讀「角色定義」→ 明確職責和輸出物

### 責任追溯
當輸出偏離原始需求時：
1. 檢查任命書是否包含所有強制欄位（層級標記、家族手冊、原始需求）
2. 檢查被任命者是否已勾選家族手冊載入確認
3. 檢查協調者中轉過程是否丟失信息

## 版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|---------|
| v1.0.0 | 2026-05-07 | 初始版本，定義基本任命書結構 |
| v1.1.0 | 2026-05-10 | 加入層級標記、家族手冊載入確認、層級限制聲明；與 SOUL.md v4.2 及 agent-bootstrap 身份判斷機制對齊 |

---

*最後更新：2026-05-10*
*本模板為 reference/ 格式規範，協調者生成任命書時參考*
