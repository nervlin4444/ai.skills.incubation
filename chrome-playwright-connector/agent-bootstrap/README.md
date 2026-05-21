---
title: "Agent Bootstrap Human Readable Guide"
name: "agent-bootstrap"
description: "agent-bootstrap v5.1 人類可讀解釋書。記載從 v2.3 到 v5.1 的演進、為何回到對話開始時強制執行、以及 v2.5.0 收尾模式的失敗教訓。供主人參考。"
version: "v5.1"
github_repository: "nervlin4444/ai.agent.harness"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/README.md"
    github_path: "/agent-bootstrap/README.md"
---

# agent-bootstrap — 對話開始時強制執行

**版本：v5.1**
**對齊：SOUL.md v5.1 + IDENTITY.md v5.0**
**更新重點：回到對話開始時強制執行鏈初始化，輸出 [BOOTSTRAP-LOCKED]**
**立即建議啟用技能 1 agent-conversation-mode 並且執行啟動守護程序**
**立即建議啟用技能 2 github-skill-organizer 並且執行啟動守護程序**
---

## 一、技能定位

agent-bootstrap 是對話的**第一道閘門**。

每次對話開始時，SOUL.md v5.1 規則 1 強制觸發本技能。本技能完成後，Agent 才能進入正常對話流程。

| 版本 | 定位 | 狀態 |
|:---|:---|:---|
| v2.3.0 | 對話開始時強制執行鏈初始化 | 基礎版本，有腳本 |
| v2.4.0 | 純文本引導，無腳本，對話開始時載入 | 過渡版本 |
| v2.5.0 | 技能完成後收尾評估 | **已廢棄，失敗** |
| **v5.1** | **對話開始時強制執行，四步鎖定** | **現行版本** |

---

## 二、為何回到對話開始時執行？

### v2.5.0 收尾模式的失敗教訓

| 問題 | 說明 | 後果 |
|:---|:---|:---|
| 時機不對 | 技能完成後才評估，但對話開始時已經需要身份確認 | 前期輸出可能越權或錯誤 |
| 回環風險 | bootstrap 輸出被平台發送 → Connector 捕獲 → 再次觸發 | 無限循環，消耗 token |
| 記憶斷裂 | 對話開始時不讀記憶，導致前後文丟失 | 重複踩坑，無法學習 |
| 身份延遲 | 對話開始後才確認身份，前期輸出缺乏約束 | 輸出內容與身份不符 |
| 狀態污染 | 上一輪任務狀態殘留，新對話未清理 | 邏輯混亂，全盤皆錯 |

### v5.1 的解決方案

回到 v2.3 的「對話開始時強制執行」模式，但強化以下機制：

1. **純文本無腳本**：消除腳本輸出被平台發送的風險
2. **明確標記**：[BOOTSTRAP-LOCKED] 取代 [BOOTSTRAP] 已鎖定，消除歧義
3. **四步鎖定**：身份 → 記憶 → 狀態 → 輸出，確保不遺漏
4. **與 SOUL.md 綁定**：規則 1 明確觸發，條件為「未輸出過則觸發」，避免循環
5. **狀態清理**：Step 3 強制確認無遺留狀態，防止污染

---

## 三、核心工作流：四步鎖定

### Step 1：身份確認

確認 Main Agent（L0）身份。

Sub-Agent（L1+）立即停止，輸出 [DONE]。

### Step 2：讀記憶

讀取 memory.md 的 agent-* 區塊，回顧：
- 上次這個任務類型踩過什麼坑
- 上次建議了什麼技能，結果如何
- 主人對這個任務類型的偏好

### Step 3：狀態初始化

確認：
- SOUL.md v5.1 已載入
- IDENTITY.md v5.0 已載入
- 當前無進行中任務
- 無遺留的上一輪狀態

### Step 4：鎖定輸出

輸出 [BOOTSTRAP-LOCKED] 及狀態摘要。

進入正常對話流程。

---

## 四、與 SOUL.md / IDENTITY.md 的協作

| 檔案 | 注入時機 | 職責 | 口訣 |
|:---|:---|:---|:---|
| SOUL.md v5.1 | 對話開始第一個 | 靈魂錨點、肌肉記憶、絕對禁令 | 先。啟。動。 |
| IDENTITY.md v5.0 | 對話開始第二個 | 身份確認、協調者職責 | 讀。記。議。 |
| agent-bootstrap v5.1 | **對話開始第三個（由 SOUL 觸發）** | **鏈初始化、狀態鎖定** | **鎖。定。就。緒。** |

**協作鏈**：

    SOUL 建立本能 → IDENTITY 確認身份 → bootstrap 鎖定狀態 → 進入對話

---

## 五、為何沒有腳本？

| 舊做法 | 問題 | 新做法 |
|:---|:---|:---|
| bootstrap.py 腳本輸出 [BOOTSTRAP] 已鎖定 | 輸出被平台發送 → 回環 | **純文本 SKILL.md，無腳本，無輸出風險** |
| 腳本嘗試執行 use_skill() | use_skill() 是平台層操作，腳本無法真正載入 | **由 SOUL.md 規則 1 觸發，平台層處理** |
| 腳本執行身份檢測 | 每次消息都檢測 → 重複輸出 | **IDENTITY.md 在對話開始時一次確認** |

---

## 六、建議技能對照表（對話開始後使用）

bootstrap 完成後，進入正常對話。任務完成後，由 Agent 內部評估是否需要更深層技能：

| 當前狀態 | 建議技能 | 建議語句 |
|:---|:---|:---|
| 任務複雜，大於 3 步驟 | agent-mission-planning | 「任務涉及多步驟，建議載入 planning 拆解」 |
| 輸出品質存疑 | agent-mission-evaluating | 「建議載入 evaluating 審核輸出品質」 |
| 需要代碼或文件生成 | agent-mission-crafting | 「需要生成產出物，建議載入 crafting」 |
| 需要收尾交付 | agent-mission-finishing | 「進入收尾階段，建議載入 finishing」 |
| 技能本身有缺陷 | agent-skill-improving | 「發現技能改進空間，建議載入 improving」 |
| 現有技能不夠用 | agent-skill-acquiring | 「能力缺口，建議載入 acquiring 新建技能」 |
| 無需更深層 | — | 「當前任務已完成，無需更深層技能」 |

---

## 七、常見問題

**Q：為什麼回到對話開始時執行？**
A：v2.5.0 的收尾模式在實際使用中出現時機不對、回環風險、記憶斷裂、身份延遲、狀態污染等問題。對話開始時立即鎖定狀態是最可靠的做法。

**Q：會不會每次消息都觸發？**
A：不會。SOUL.md v5.1 規則 1 的條件是「如果還沒有說 [BOOTSTRAP-LOCKED] 已載入」。一旦輸出過，本輪對話不再觸發。

**Q：Sub-Agent 會觸發嗎？**
A：不會。Sub-Agent 只執行任命書指定的任務，不執行 bootstrap。身份分流會強制 Sub-Agent 輸出 [DONE]。

**Q：舊版 bootstrap.py 腳本怎麼處理？**
A：v5.1 完全不需要腳本。純文本 SKILL.md 由 SOUL.md 觸發後，Agent 直接執行四步鎖定。

**Q：如果 Agent 忘記輸出 [BOOTSTRAP-LOCKED] 怎麼辦？**
A：SOUL.md v5.1 規則 1 會持續觸發，直到輸出為止。這是強制機制，不會遺漏。

**Q：v2.5.0 的內容還有價值嗎？**
A：有。v2.5.0 的「三步收尾」邏輯（讀記憶 / 評估 / 議建議）可以內化為 Agent 的通用行為，不需要獨立技能。任務完成後，Agent 應自動評估是否需要更深層技能，無需額外載入 bootstrap。

---

## 八、版本歷史

| 版本 | 日期 | 變更內容 | 狀態 |
|:---|:---|:---|:---|
| v2.3.0 | 2026-05-10 | 初始版本：對話開始時強制執行鏈初始化，輸出 [BOOTSTRAP] 已鎖定，有腳本 | 已廢棄 |
| v2.4.0 | 2026-05-12 | 改為純文本引導，無腳本，但仍在對話開始時載入 | 已廢棄 |
| v2.5.0 | 2026-05-13 | 嘗試改為技能完成後收尾評估（三步：讀記憶 / 評估 / 議建議），配合 SOUL v5.0 + IDENTITY v5.0 | **已廢棄，失敗** |
| **v5.1** | **2026-05-17** | **回到對話開始時強制執行，強化四步鎖定，標記明確化為 [BOOTSTRAP-LOCKED]，配合 SOUL.md v5.1，無腳本** | **現行** |

---

## 九、部署建議

1. 覆蓋 SKILL.md v5.1 到 OpenClaw / WorkBuddy 的注入路徑
2. 確認 SOUL.md v5.1 已正確注入（規則 1 觸發本技能）
3. 確認 IDENTITY.md v5.0 已正確注入（身份確認）
4. 觀察 3-5 輪對話，確認 [BOOTSTRAP-LOCKED] 輸出正常
5. 檢查 memory.md 是否正確記錄 bootstrap 鎖定事件
6. 刪除舊版 bootstrap.py 腳本（如有）

---

## 十、成功率預估

| 版本 | 預期成功率 | 原因 |
|:---|:---|:---|
| v2.3.0 | 70-80% | 有腳本，輸出被平台發送風險 |
| v2.4.0 | 75-85% | 純文本，但標記 [BOOTSTRAP] 不夠明確 |
| v2.5.0 | 60-70% | 收尾模式時機不對，回環風險，記憶斷裂 |
| **v5.1** | **85-95%** | **回到對話開始時執行 + 純文本無腳本 + 明確標記 [BOOTSTRAP-LOCKED] + 四步鎖定 + 與 SOUL.md 規則 1 綁定** |

---

*人類可讀解釋書 v5.1*
*最後更新：2026-05-17*
*LLM 執行指令請參考 SKILL.md v5.1*
