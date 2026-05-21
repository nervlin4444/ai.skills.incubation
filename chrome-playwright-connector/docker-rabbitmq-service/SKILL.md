---
# ============================================================
# YAML Frontmatter — Agent 快速篩選 Metadata
# 此區塊為 Agent 啟動時唯一讀取的部分，正文不載入 Context Window
# ============================================================

name: docker.rabbitmq.service
description: >
  使用 Docker Compose 部署 RabbitMQ 消息隊列服務，支援 AMQP 協議、Management 插件與 MQTT 擴展。
  當用戶提及 RabbitMQ、消息隊列、AMQP、OpenClaw 跨實例通訊、MQTT Broker、異步任務隊列時激活此技能。
  協調 DevOps 專家與系統管理員完成部署、初始化、驗證與日常運維。

triggers:
  - rabbitmq
  - 消息隊列
  - message queue
  - amqp
  - mqtt
  - mqtt broker
  - openclaw 通訊
  - 異步任務
  - async queue
  - event bus
  - 事件總線
  - rabbitmq 部署
  - rabbitmq 安裝
  - rabbitmq 設定
  - docker compose rabbitmq

allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Edit

compatibility: >
  Requires Docker Compose v2.29+,
  支援 Windows Docker Desktop / macOS Docker Desktop / Linux Docker CE / QNAP Container Station

user-invocable: true
disable-model-invocation: false

metadata:
  category: infrastructure
  subcategory: message-queue
  team: devops
  priority: high
  version: 1.0.0
  author: Generator
  last_updated: 2026-04-27
  target_platforms:
    - windows
    - macos
    - linux
    - qnap
---

# ============================================================
# 技能目錄樹狀架構
# ============================================================
# 以下為此技能包的完整目錄結構，所有技能必須遵循此架構：
#
#   docker.rabbitmq.service/  ← 技能文件夾（使用連字符，兼容文件系統）
#   ├── SKILL.md                          ← 本文件（核心指令 + Metadata）
#   │   ├── YAML Frontmatter              ← Agent 啟動時唯一讀取的篩選區塊
#   │   ├── 角色定位                       ← DevOps 專家 / 系統管理員
#   │   ├── 工作流程                       ← Summon → Monitor → Record → Report
#   │   ├── 報告模板                       ← 部署驗證報告標準化輸出
#   │   ├── 互動模式                       ← 用戶觸發邏輯與異常處理
#   │   └── 實作細節                       ← Scripts / References / Assets 索引
#   │
#   ├── CONFIRMATION.md                   ← 🆕 待確認項清單（交付前必須用戶確認）
#   │   ├── 命名名稱 (Naming)             ← 項目前綴、容器名、卷名、用戶名
#   │   ├── 路徑 (Paths)                  ← Compose文件、.env、備份目錄、Socket路徑
#   │   ├── 參數 (Parameters)             ← 端口、資源限制、密碼、版本號
#   │   └── 確認流程                      ← PENDING → CONFIRMED / MODIFIED
#   │
#   ├── scripts/                          ← 可執行腳本（Python / Bash / JS）
#   │   ├── init.rabbitmq.sh             ← 環境自動檢測與初始化腳本
#   │   └── validate.rabbitmq.sh         ← 部署後驗證與合規檢查腳本
#   │
#   ├── references/                       ← 參考文檔與規範（只讀）
#   │   └── rabbitmq.guide.md            ← 操作指南、最佳實踐與常見問題
#   │
#   └── assets/                           ← 模板資源與靜態文件
#       └── docker.compose.rabbitmq.yaml  ← Docker Compose 實施模板（含三級規則標記）
#
# ============================================================

# ============================================================
# 強制規範區塊 — 所有衍生技能必須遵循
# ============================================================

## 規範零：命名體系總覽 🔒 LOCK v0.0 PERMANENT

    所有技能包必須遵循以下分層命名體系。
    涉及 Docker 的 Compose / Container / Image / Volume / Network 命名
    必須遵守對應格式，創造技能時必須遵守。

    | 命名類型 | 格式 | 分隔符 | 示例 | 說明 |
    |:---------|:-----|:-------|:-----|:-----|
    | SKILL_NAME | <CATEGORY>.<PROJECT>.<PURPOSE> | 點號 | docker.rabbitmq.master | 技能文件名前綴 |
    | COMPOSE_NAME | <PROJECT>_<PURPOSE> | 底線 | rabbitmq_master | COMPOSE_PROJECT_NAME |
    | CONTAINER_NAME | <PROJECT>.<PURPOSE>.<PORT> | 點號 | rabbitmq.master.5672 | 主容器名 |
    | SUB_CONTAINER_NAME | <SUB_IMAGE>.<PURPOSE>.<PORT> | 點號 | redis.cache.6379 | 子容器名 |
    | VOLUME_NAME | <PROJECT>.<PURPOSE>.<PORT> | 點號 | rabbitmq.data.5672 | 主卷名 |
    | SUB_VOLUME_NAME | <SUB_IMAGE>.<PURPOSE>.<PORT> | 點號 | redis.data.6379 | 子卷名 |
    | NETWORK_NAME | <HOST>.<TYPE>.network | 點號 | qnap.bridge.network | 網絡名 |

    占位符說明：
      <CATEGORY>    → 技能/鏡像的項目類名稱，例如 Excel, Docker...
                      一般查看使用方法建議，可以詢問用戶
      <PROJECT>     → 技能/鏡像的名稱，鏡像直接用已下載的鏡像名稱
                      可以詢問用戶
      <PURPOSE>     → 技能的實際名稱，可以詢問用戶
      <PORT>        → 技能需要使用的對外端口，一般查看使用方法建議
                      可以詢問用戶
      <SUB_IMAGE>   → 主鏡像需要用到的關連應用鏡像項目類名稱
      <HOST>        → 用於所在網絡名稱，可以詢問用戶
      <TYPE>        → 用於所在網絡接橋方法，一般查看使用方法建議

    命名對照示例（以 RabbitMQ 為例）：
      | 類型 | 命名結果 |
      |:-----|:---------|
      | SKILL_NAME | docker.rabbitmq.service |
      | COMPOSE_NAME | rabbitmq_service |
      | CONTAINER_NAME | rabbitmq.service.5672 |
      | SUB_CONTAINER_NAME | redis.cache.6379 |
      | VOLUME_NAME | rabbitmq.data.5672 |
      | SUB_VOLUME_NAME | redis.data.6379 |
      | NETWORK_NAME | <動態檢測> |

    ⚠️ NETWORK_NAME 動態檢測規則：
      - 必須先執行 `docker network ls` 檢查現有網絡
      - 如果存在符合命名規範的網絡（如 nervlin.bridge.network），建議用戶跟隨
      - 如果不存在，則建議創建新網絡：<HOST>.<TYPE>.network
      - HOST 建議使用當前主機名或 Docker Host 標識
      - 在 CONFIRMATION.md 中必須讓用戶確認網絡選擇

    統一原則：
      所有 Docker 資源命名（容器、卷、網絡）統一使用點號分隔。
      禁止混用連字符或底線（COMPOSE_NAME 除外，因其受 Docker 網絡名限制）。
      允許 FQDN 風格（含多點），例如：nervlin.myqnapcloud.com.cert.master

## 規範一：檔案命名格式 🔒 LOCK v1.0 PERMANENT

    所有技能包內檔案名稱統一使用 xxx.yyy.zzz.ext 格式。
    全部以點號（.）作為分隔符，禁止使用中劃線（-）或下劃線（_）。
    檔案命名對應 SKILL_NAME 格式：<CATEGORY>.<PROJECT>.<PURPOSE>.ext

    正確示例：
      - init.rabbitmq.sh          ← SKILL_NAME=init.rabbitmq, ext=sh
      - validate.rabbitmq.sh      ← SKILL_NAME=validate.rabbitmq, ext=sh
      - docker.compose.rabbitmq.yaml  ← SKILL_NAME=docker.compose.rabbitmq, ext=yaml
      - rabbitmq.guide.md         ← SKILL_NAME=rabbitmq.guide, ext=md
      - rabbitmq.skill.md         ← SKILL_NAME=rabbitmq.skill, ext=md

    錯誤示例（禁止出現）：
      - init_rabbitmq.sh          ← 含底線
      - docker-compose.rabbitmq.yaml  ← 含中劃線
      - rabbitmq_guide.md         ← 含底線

## 規範一-A：COMPOSE_NAME Docker 命名限制 🔒 LOCK v1.0-A PERMANENT

    僅限 COMPOSE_NAME（COMPOSE_PROJECT_NAME）必須遵守 Docker 引擎命名限制。
    此限制不影響檔案命名（規範一）或其他 Docker 資源命名（規範一-B/C/D）。

    COMPOSE_NAME 格式：<PROJECT>_<PURPOSE>
    分隔符：底線（_）
    原因：Docker Compose 使用 COMPOSE_PROJECT_NAME 生成網絡名、容器名前綴等，
          而 Docker 網絡名禁止點號，因此 COMPOSE_NAME 必須使用底線。

    COMPOSE_NAME 允許字符：
      ✅ 小寫字母 a-z
      ✅ 數字 0-9（但不能以數字開頭）
      ✅ 連字符 -
      ✅ 底線 _
    COMPOSE_NAME 禁止字符：
      ❌ 點號 .（Docker 網絡名禁止）
      ❌ 空格
      ❌ 大寫字母 A-Z
      ❌ 其他特殊符號 !@#$%^&*() 等

    自動建議規則：
      當檢測到建議 COMPOSE_NAME 含點號時，自動提議以底線取代。
      例：用戶輸入 "rabbitmq.master" → 系統建議 "rabbitmq_master"

    正確示例（COMPOSE_NAME）：
      - rabbitmq_master
      - portainer_agent
      - dify_api
      - myapp_worker

    錯誤示例（COMPOSE_NAME 禁止）：
      - rabbitmq.master（含點號）
      - MyApp（含大寫）
      - 123app（以數字開頭）

## 規範一-B：CONTAINER_NAME 命名格式 🔒 LOCK v1.0-B PERMANENT

    容器名稱格式：<PROJECT>.<PURPOSE>.<PORT>
    分隔符：點號（.）
    Docker 引擎允許容器名含點號，因此遵循 SKILL_NAME 點號格式。

    正確示例：
      - rabbitmq.master.5672      ← PROJECT=rabbitmq, PURPOSE=master, PORT=5672
      - portainer.agent.9001      ← PROJECT=portainer, PURPOSE=agent, PORT=9001
      - redis.cache.6379          ← PROJECT=redis, PURPOSE=cache, PORT=6379

    子容器（SUB_CONTAINER_NAME）格式：<SUB_IMAGE>.<PURPOSE>.<PORT>
      - postgres.db.5432          ← SUB_IMAGE=postgres, PURPOSE=db, PORT=5432
      - elasticsearch.search.9200 ← SUB_IMAGE=elasticsearch, PURPOSE=search, PORT=9200

## 規範一-C：VOLUME_NAME 命名格式 🔒 LOCK v1.0-C PERMANENT

    卷名稱格式：<PROJECT>.<PURPOSE>.<PORT>
    分隔符：點號（.）
    Docker 引擎允許卷名含點號，因此遵循 SKILL_NAME 點號格式。
    統一原則：全部使用點號分隔，禁止混用連字符或底線。
    允許 FQDN 風格（含多點），例如：nervlin.myqnapcloud.com.cert.master

    正確示例：
      - rabbitmq.data.5672        ← PROJECT=rabbitmq, PURPOSE=data, PORT=5672
      - portainer.data.9001       ← PROJECT=portainer, PURPOSE=data, PORT=9001
      - nervlin.myqnapcloud.com.cert.master  ← FQDN 風格，含多點

    子卷（SUB_VOLUME_NAME）格式：<SUB_IMAGE>.<PURPOSE>.<PORT>
      - postgres.data.5432        ← SUB_IMAGE=postgres, PURPOSE=data, PORT=5432
      - redis.data.6379            ← SUB_IMAGE=redis, PURPOSE=data, PORT=6379

    注意：external volume 必須預先創建，創建命令示例：
      docker volume create rabbitmq.data.5672
      docker volume create nervlin.myqnapcloud.com.cert.master

## 規範一-D：NETWORK_NAME 命名格式 🔒 LOCK v1.0-D PERMANENT

    網絡名稱格式：<HOST>.<TYPE>.network
    分隔符：點號（.）
    Docker 引擎允許網絡名含點號。

    ⚠️ 重要：NETWORK_NAME 必須動態檢測，禁止寫死！

    檢測邏輯：
      1. 執行 `docker network ls --format "{{.Name}}"` 取得所有網絡
      2. 過濾出符合 `<HOST>.<TYPE>.network` 格式的網絡
      3. 如果找到現有網絡（如 nervlin.bridge.network）：
         - 建議用戶跟隨該命名模式
         - 提取 HOST 部分作為建議值
      4. 如果找不到：
         - 使用當前主機名（hostname）作為 HOST
         - 建議創建新網絡：<HOST>.bridge.network

    正確示例：
      - nervlin.bridge.network   ← 檢測到現有網絡，建議跟隨
      - qnap.bridge.network       ← HOST=qnap, TYPE=bridge
      - macos.proxy.network        ← HOST=macos, TYPE=proxy
      - windows.backend.network    ← HOST=windows, TYPE=backend

    注意：
      - proxy-net 等簡化名稱保留用於 compose 文件內部引用
      - 外部網絡（external: true）必須先確認是否已存在
      - 在 CONFIRMATION.md 中必須讓用戶確認網絡選擇

## 規範二：部署命令統一 🔒 LOCK v1.1 PERMANENT

    所有涉及 Docker 部署的技能，全程使用 docker compose 命令。
    禁止使用 docker run 作為主要部署方式。

    正確示例：
      - docker compose -f assets/docker.compose.rabbitmq.yaml up -d
      - docker compose -f assets/docker.compose.rabbitmq.yaml run --rm init_rabbitmq
      - docker compose -f assets/docker.compose.rabbitmq.yaml ps
      - docker compose -f assets/docker.compose.rabbitmq.yaml logs -f

    錯誤示例（禁止出現）：
      - docker run -d --name rabbitmq ...
      - docker exec -it container sh
      - docker volume create ...（應由 compose 管理或外部預先創建）

    例外：僅在 references 文檔中說明原理時可提及 docker run，
          實際交付的腳本與模板必須轉換為 docker compose。

## 規範三：環境自動檢測 🔄 FLEX v1.0 EVOLVING

    初始化腳本（scripts/init.<purpose>.sh）必須自動檢測現有環境，
    輸出命名建議供用戶確認，不應要求用戶手動執行命令核實。

    必須自動檢測的項目：
      1. 現有容器命名模式 → 建議 PROJECT_PREFIX（遵循規範一-A，僅小寫/數字/連字符/底線）
      2. 現有網絡列表 → 動態檢測並建議 NETWORK_NAME（遵循規範一-D）
         - 執行 `docker network ls` 檢查現有網絡
         - 如果存在符合 <HOST>.<TYPE>.network 格式的網絡（如 nervlin.bridge.network）
         - 建議用戶跟隨現有命名模式
         - 如果不存在，建議創建新網絡：<HOST>.<TYPE>.network
         - HOST 建議使用當前主機名或 Docker Host 標識
      3. 現有卷列表 → 建議重用或新建 rabbitmq.data.5672
      4. Docker Socket 路徑 → 自動匹配平台
      5. 端口佔用情況 → 標記衝突端口 (5672 / 15672)
      6. .env 文件存在性 → 自動生成模板或檢測默認密碼

    網絡檢測邏輯示例：
      EXISTING_NETWORKS=$(docker network ls --format "{{.Name}}")
      SUGGESTED_NETWORK=$(echo "$EXISTING_NETWORKS" | grep -E "^[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.network$" | head -1)
      if [ -n "$SUGGESTED_NETWORK" ]; then
        echo "檢測到現有網絡: $SUGGESTED_NETWORK"
        echo "建議跟隨命名模式: $(echo $SUGGESTED_NETWORK | grep -oE '^[^\.]+')"
      else
        HOSTNAME=$(hostname | grep -oE '^[^\.]+')
        echo "建議創建新網絡: ${HOSTNAME}.bridge.network"
      fi

    檢測邏輯示例：
      EXISTING_CONTAINERS=$(docker ps -a --format '{{.Names}}')
      COMMON_PREFIX=$(echo "$EXISTING_CONTAINERS" | grep -oE '^[a-zA-Z0-9]+' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
      echo "建議項目前綴: ${COMMON_PREFIX}"
      read -p "是否採用? [y/N]: " answer

## 規範四：待確認項清單 🔄 FLEX v1.1 EVOLVING

    所有技能包交付前必須產出 CONFIRMATION.md，列出所有建議值供用戶確認。
    禁止在未經用戶確認的情況下直接執行部署。

    CONFIRMATION.md 必須包含四大類別：
      1. 命名名稱 (Naming)   — 項目前綴、容器名、卷名、網絡名、用戶名、服務名
      2. 路徑 (Paths)        — Compose 文件路徑、.env 路徑、備份路徑、Socket 路徑、掛載點
      3. 參數 (Parameters)   — 端口、資源限制、版本號、健康檢查閾值
      4. 敏感值 (Secrets)    — 密碼、Token、Cookie、API Key（必須標記為「必須修改」）

    命名名稱注意事項：
      - 檔案命名遵循規範一（xxx.yyy.zzz.ext，使用點號）
      - COMPOSE_NAME 遵循規範一-A（<PROJECT>_<PURPOSE>，使用底線，禁止點號）
      - CONTAINER_NAME 遵循規範一-B（<PROJECT>.<PURPOSE>.<PORT>，使用點號）
      - VOLUME_NAME 遵循規範一-C（<PROJECT>.<PURPOSE>.<PORT>，使用點號，允許 FQDN）
      - NETWORK_NAME 遵循規範一-D（<HOST>.<TYPE>.network，使用點號）

    每項格式：
      | 項次 | 類別 | 建議值 | 用途 | 狀態 |
      |:----:|:-----|:-------|:-----|:----:|
      | N-01 | 項目前綴 | <建議值> | <用途說明> | [PENDING] |

    確認流程：
      Step 1: Generator 產出 CONFIRMATION.md + 所有技能檔案
      Step 2: 用戶逐項審閱，標記 [CONFIRMED] 或 [MODIFIED: xxx]
      Step 3: Generator 根據確認結果更新所有檔案中的占位符
      Step 4: 執行 docker compose config 語法驗證
      Step 5: 用戶最終確認後，進入 docker compose up -d 執行階段

    占位符標註規範：
      - 命名占位符    : <PROJECT_PREFIX>, <SERVICE_NAME>, <CONTAINER_NAME>
      - 路徑占位符    : <HOST_PATH>, <CONFIG_PATH>, <BACKUP_PATH>
      - 參數占位符    : <PORT>, <VERSION>, <CIDR>
      - 敏感占位符    : <GENERATE_RANDOM>, <PASSWORD>, <API_KEY>

## 規範五：敏感值防呆 🔒 LOCK v1.2 PERMANENT

    所有密碼、Token、Cookie 必須使用占位符 <GENERATE_XXCHAR_RANDOM_STRING>，
    禁止在模板中硬編碼真實密碼。

    init 腳本必須自動檢測 .env 中是否存在默認/弱密碼，
    若發現則觸發 ⛔ STOP v1.0，強制要求修改後方可繼續。

    檢測邏輯示例：
      if grep -q "DEFAULT_PASS=password123" .env; then
        echo "⛔ STOP: 檢測到弱密碼，必須修改"
        exit 1
      fi

# ============================================================
# 正文區塊 — 僅在 Agent 匹配成功後載入
# ============================================================

# RabbitMQ Docker Compose 部署技能

## 角色定位
- **DevOps 專家**：負責 Docker Compose 模板審查、網絡架構設計、資源限制配置
- **系統管理員**：負責環境初始化、用戶權限配置、備份策略執行、日常運維監控
- **安全審計員**：負責密碼強度檢查、guest 用戶刪除確認、端口暴露策略審查

## 工作流程

### 1. 召喚階段（Summon）
sub-agent：
- **環境檢測員**：執行 `scripts/init.rabbitmq.sh`，輸出環境檢測報告
- **配置審查員**：檢查 `.env` 文件、確認密碼非默認值、確認 Erlang Cookie 已設置
- **網絡架構師**：確認 proxy-net / backend-net / app-net 三層網絡隔離就緒

### 2. 監控階段（Monitor）
- 啟動後持續監控 `docker compose ps` 容器狀態
- 監控健康檢查 `rabbitmq-diagnostics ping` 返回值
- 監控 Management UI 可達性（經外部反向代理網絡反向代理）
- 監控 AMQP 端口 5672 內部服務連線狀態
- 監控資源使用（CPU / Memory）是否觸發 deploy.resources.limits
- ⚠️ 網絡名稱必須動態檢測，禁止寫死（遵循規範一-D）

### 3. 記錄階段（Record）
- 記錄部署時間戳、版本號、環境變量哈希（脫敏）
- 記錄用戶創建日誌（rabbitmq / openclaw / guest 刪除確認）
- 記錄網絡掛載清單（proxy-net / backend-net / app-net）
- 記錄卷掛載確認（rabbitmq.data.5672 external volume）
- 記錄備份檔案路徑與時間戳

### 4. 報告階段（Report）
- 執行 `scripts/validate.rabbitmq.sh`，生成標準化驗證報告
- 輸出 PASS/FAIL 統計、異常項詳情、修復建議
- 輸出 CONFLICT_REPORT.md（若觸發 ⛔ STOP 規則）

## 報告模板

    ============================================================
    [REPORT] docker.rabbitmq.service 部署驗證報告
    ============================================================
    項目名稱    : <PROJECT_PREFIX>
    部署時間    : <TIMESTAMP>
    技能版本    : docker.rabbitmq.service.skill.md v1.0.0
    Compose 文件 : docker.compose.rabbitmq.yaml

    --- 命名規則變量 ---
    SKILL_NAME    : <SKILL_NAME>
    COMPOSE_NAME  : <COMPOSE_NAME>
    CONTAINER_NAME: <CONTAINER_NAME>

    --- 環境檢測 ---
    項目前綴    : <PROJECT_PREFIX>
    <NETWORK_NAME>   : <存在/已創建/缺失>
    rabbitmq.data.5672: <已掛載/缺失>
    端口 5672  : <可用/衝突>
    端口 15672 : <可用/衝突>

    --- 部署狀態 ---
    容器狀態    : <running / exited / missing>
    健康檢查    : <healthy / unhealthy / none>
    用戶清單    : <rabbitmq: administrator, openclaw: user, guest: deleted>
    插件狀態    : <rabbitmq_management: enabled>

    --- 網絡與存儲 ---
    掛載網絡    : <<NETWORK_NAME>, backend-net, app-net>
    掛載卷      : <rabbitmq.data.5672 (external)>
    資源限制    : <CPU: X, Memory: Y>

    --- 驗證統計 ---
    通過項      : <N>
    失敗項      : <N>
    結論        : <符合規範 / 需人工介入>
    ============================================================

## 互動模式

### 正常流程
1. 用戶觸發關鍵詞（RabbitMQ / 消息隊列 / AMQP / OpenClaw 通訊）
2. Agent 加載 SKILL.md 正文區塊
3. Agent 指引用戶執行 `bash init.rabbitmq.sh` 進行環境檢測
4. Agent 指引用戶執行 `docker compose -f docker.compose.rabbitmq.yaml up -d`
5. Agent 指引用戶執行 `docker compose -f docker.compose.rabbitmq.yaml run --rm init_rabbitmq`
6. Agent 指引用戶執行 `bash validate.rabbitmq.sh` 確認部署

### 異常處理（⛔ STOP v1.0 CONFLICT-RESOLVE）
| 觸發條件 | 動作 | 輸出 |
|:---------|:-----|:-----|
| 端口 5672 / 15672 被佔用 | STOP → REPORT | CONFLICT_REPORT.md：標記衝突進程，建議修改 .env 端口或停止衝突服務 |
| proxy-net 缺失 | STOP → AWAIT | 提示用戶選擇 (A) 自動創建 (B) 修改網絡名稱 |
| rabbitmq.data.5672 卷缺失 | STOP → AWAIT | 提示用戶選擇 (A) 自動創建 (B) 改用 bind mount |
| 默認密碼未修改 | STOP → RESOLVE | 強制要求修改密碼，拒絕繼續部署 |
| guest 用戶未刪除 | STOP → RESOLVE | 標記安全風險，要求重新執行 init_rabbitmq |

## 實作細節

### Scripts
- `scripts/init.rabbitmq.sh`: 初始化環境檢測與設置。必須遵循規範三，自動檢測環境並輸出建議。包含 .env 生成、密碼強度檢查、端口衝突檢測。
- `scripts/validate.rabbitmq.sh`: 驗證輸出物語法、結構與規範符合性。全程使用 docker compose 命令。檢查容器狀態、健康檢查、用戶配置、網絡掛載、卷掛載、資源限制。

### References
- `references/rabbitmq.guide.md`: 操作指南、最佳實踐與常見問題。包含與原 docker run 方案對照表、日常運維命令、FAQ、安全建議。

### Assets
- `assets/docker.compose.rabbitmq.yaml`: Docker Compose 結構化模板文件。必須遵循規範一（xxx.yyy.zzz.ext 命名）與規範二（全程 docker compose 命令）。包含三級規則控制架構（🔒 LOCK / ⛔ STOP / 🔄 FLEX）、三層網絡隔離、外部命名卷防呆、共享環境變量錨點、服務健康檢查、profiles 隔離的 init 與 backup 服務。

### Environment Template
- `.env.example`: 環境變量配置模板。包含默認用戶/密碼、端口、Erlang Cookie、資源限制等配置項。複製為 `.env` 後根據實際環境修改。

### 關鍵設計決策

#### 為何保留 15672 端口映射？
原 docker run 方案直接暴露 15672。Compose 方案保留此映射但標記為 ⛔ STOP v1.4，要求生產環境必須經 proxy-net 由外部 Nginx / NPM 反向代理，禁止直接暴露公網。

#### 為何使用 external volume？
遵循 🔒 LOCK v1.2 PERMANENT。RabbitMQ mnesia 數據庫包含隊列狀態與消息持久化，屬生產關鍵數據。external volume 確保 `docker compose down -v` 無法誤刪。

#### 為何需要 init_rabbitmq 服務？
原 docker run 方案需手動執行 5 條 rabbitmqctl 命令。Compose 方案將此邏輯封裝為一次性 init 服務（profiles: ["init"]），通過 `depends_on condition: service_healthy` 確保主服務就緒後執行，避免手動操作錯誤。

#### 為何需要 app-net？
OpenClaw 跨實例通訊場景要求 RabbitMQ 與 OpenClaw 實例處於同一可互通網絡。app-net 專為此設計，不暴露於 proxy-net，實現單向/雙向跨地域通訊。

# ============================================================
# 🔄 FLEX vX.X EVOLVING — 踩坑經驗（可選章節）
# ============================================================
# 用途：記錄實戰中發現的常見錯誤與解決方案
# 格式：問題描述 → 解決方案 → 驗證命令 → 常見錯誤示例
# ============================================================

## 踩坑經驗

### Docker Compose 項目名命名規則
**問題描述**：
Docker Compose 項目名（COMPOSE_PROJECT_NAME）不能包含點號（.），因為 Docker 網絡名禁止點號。

**解決方案**：
1. **技能文件名稱（SKILL_NAME）**：使用點號（.），例如 `docker.rabbitmq.service`
2. **技能文件夾名**：使用連字符（-），例如 `docker-rabbitmq-service`（兼容文件系統）
3. **COMPOSE_PROJECT_NAME**：使用底線（_），例如 `rabbitmq_service`
4. **容器名（CONTAINER_NAME）**：使用點號（.），例如 `rabbitmq.service.5672`
5. **檔案名**：使用點號（.），例如 `init.rabbitmq.sh`

**驗證命令**：
    docker compose config  # 檢查配置是否合法

**常見錯誤**：
- 使用點號：`rabbitmq.service` ❌（作為 COMPOSE_PROJECT_NAME）
- 使用空格：`rabbitmq service` ❌
- 使用大寫：`RabbitMQ-Service` ❌
- 正確格式：`rabbitmq_service` ✅（COMPOSE_PROJECT_NAME）
- 正確格式：`rabbitmq.service.5672` ✅（CONTAINER_NAME）
