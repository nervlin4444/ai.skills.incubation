---
# ============================================================
# YAML Frontmatter — Agent 快速篩選 Metadata
# 此區塊為 Agent 啟動時唯一讀取的部分，正文不載入 Context Window
# ============================================================

name: docker.portainer.webportal
description: >
  Docker 容器管理與監控平台 Portainer 的標準化部署技能。
  當用戶提及 Portainer、Docker GUI、容器管理、Docker 監控、NAS Docker 管理等關鍵詞時激活。
  協調 Docker 運維專家與安全架構師完成 Portainer 服務部署與權限配置。

triggers:
  - portainer
  - docker gui
  - 容器管理
  - docker 監控
  - NAS docker
  - portainer deploy
  - docker 管理介面
  - container management
  - docker dashboard
  - portainer agent
  - docker.sock 掛載

allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Edit

compatibility: >
  Requires Docker Compose v2.29+,
  支援 Windows Docker Desktop / macOS Docker Desktop / Linux Docker CE / QNAP Container Station.
  需要 Docker Socket 訪問權限以管理本地容器。

user-invocable: true
disable-model-invocation: false

metadata:
  category: infrastructure
  subcategory: container-management
  team: devops
  priority: high
  version: 1.0.0
  author: Generator
  last_updated: 2026-04-26
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
#   docker.portainer.webportal/
#   ├── SKILL.md                          ← 本文件（核心指令 + Metadata）
#   │   ├── YAML Frontmatter              ← Agent 啟動時唯一讀取的篩選區塊
#   │   ├── 角色定位                       ← 職責說明
#   │   ├── 工作流程                       ← Summon → Monitor → Record → Report
#   │   ├── 報告模板                       ← 標準化輸出格式
#   │   ├── 互動模式                       ← 用戶觸發邏輯
#   │   └── 實作細節                       ← Scripts / References / Assets 索引
#   │
#   ├── scripts/
#   │   ├── init.webportal.sh             ← 首次環境初始化（創建卷、檢查 docker.sock）使用 xxx.yyy.zzz.sh 命名
#   │   └── validate.webportal.sh         ← 驗證部署結果與服務健康狀態 使用 xxx.yyy.zzz.sh 命名
#   │
#   ├── references/
#   │   ├── portainer.guide.md            ← 操作指南、快速開始與故障排查
#   │   └── portainer.security.md         ← 安全最佳實踐、docker.sock 風險與權限控制
#   │
#   └── assets/
#       ├── docker.portainer.webportal.yaml ← Docker Compose 實施模板（含三級規則標記）
#       └── portainer-agent-stack.yml     ← Portainer Agent 多節點部署模板（可選）
#
# ============================================================

# ============================================================
# 正文區塊 — 僅在 Agent 匹配成功後載入
# ============================================================

# docker.portainer.webportal Docker 管理面板部署技能

## 角色定位
- **ContainerOps Architect（容器運維架構師）**：負責設計 Portainer 部署架構、網絡規劃、數據持久化策略，確保與現有 Docker 生態無縫整合。
- **Security Auditor（安全審計員）**：負責審查 docker.sock 掛載風險、特權模式（privileged）必要性、端口暴露範圍，制定最小權限原則。

## 工作流程

### 1. 召喚階段（Summon）
sub-agent：
- **ContainerOps Architect**：確認部署目標（本地 / NAS / 遠程節點）、確認端口可用性、**確認是否開放 Edge Agent 端口（8000）**、輸出 docker.portainer.webportal.yaml（使用 `xxx.yyy.zzz.sh` 命名格式）
- **Security Auditor**：審查 docker.sock 掛載路徑、評估 privileged 模式必要性、確認管理員帳號策略、**審查 Edge Agent 端口暴露風險**

### 2. 監控階段（Monitor）
- 監控 Portainer 容器健康狀態（HTTP 9000/9443 端口響應）
- 監控 Docker Socket 可訪問性（容器列表能否正常加載）
- 監控數據卷使用情況（/data 目錄增長趨勢）
- 監控登入嘗試與異常訪問（日誌分析）

### 3. 記錄階段（Record）
- 記錄首次啟動時間與管理員帳號創建狀態
- 記錄數據卷快照與備份時間點
- 記錄端口映射與網絡配置變更歷史
- 記錄安全審查結果與風險接受聲明

### 4. 報告階段（Report）
- 輸出部署狀態報告（參考下方報告模板）
- 異常時輸出 CONFLICT_REPORT.md 標記 AWAITING_RESOLUTION

## 報告模板

    [PORTAINER-DEPLOY REPORT] 生成時間: <TIMESTAMP>
    ============================================================
    1. 部署狀態
       容器名稱      : <CONTAINER_NAME>
       運行狀態      : <RUNNING/EXITED/RESTARTING>
       鏡像版本      : <IMAGE_TAG>
       啟動時間      : <START_TIME>

    2. 端口與網絡
       HTTP 端口     : <PORT_9000>
       HTTPS 端口    : <PORT_9443>
       Edge Agent    : <PORT_8000> (如未開放則顯示「已關閉」）
       掛載網絡      : <NETWORKS>

    3. 數據持久化
       數據卷名稱    : <VOLUME_NAME>
       掛載路徑      : /data
       卷大小        : <VOLUME_SIZE>

    4. Docker 訪問
       Socket 路徑   : <SOCKET_PATH>
       特權模式      : <true/false>
       訪問權限      : <READ/WRITE>

    5. 安全狀態
       管理員帳號    : <ADMIN_USER>
       首次登入      : <FIRST_LOGIN>
       審查結果      : <PASS/WARN/FAIL>

    6. 健康檢查
       HTTP 響應    : <HEALTH_STATUS>
       API 響應     : <API_STATUS>
       下次檢查      : <NEXT_CHECK>
    ============================================================

## 互動模式

1. 用戶提及觸發詞（Portainer / Docker GUI / 容器管理等）
2. Agent 確認環境參數（PROJECT_PREFIX, HOST_SOCKET_PATH, 端口佔用情況）
3. **確認是否開放 Edge Agent 端口（8000）**（默認：關閉）
4. 輸出 docker.portainer.webportal.yaml 與初始化腳本（使用 `xxx.yyy.zzz.sh` 命名格式）
5. **賦予腳本執行權限**（chmod +x），避免執行時停頓詢問
6. 指引用戶執行 scripts/init.webportal.sh 完成前置檢查
7. 啟動服務：docker compose up -d portainer
8. 執行 scripts/validate.webportal.sh 確認部署成功
9. 指引用戶訪問 https://<host>:9443 完成首次設置

## 實作細節

### Scripts
- `scripts/init.webportal.sh`: 首次環境初始化，創建外部卷、檢查 docker.sock 存在性、驗證端口可用性、確認管理員帳號策略（使用 `xxx.yyy.zzz.sh` 命名格式）
- `scripts/validate.webportal.sh`: 驗證部署結果，檢查 HTTP/HTTPS 端口響應、容器健康狀態、數據卷掛載正確性（使用 `xxx.yyy.zzz.sh` 命名格式）

### References
- `references/portainer.guide.md`: 操作指南、快速開始步驟、故障排查矩陣、進階配置（Agent 模式、多節點管理）
- `references/portainer.security.md`: 安全最佳實踐、docker.sock 掛載風險分析、特權模式替代方案、RBAC 配置建議

### Assets
- `assets/docker.portainer.webportal.yaml`: Docker Compose 實施模板，含 🔒 LOCK / ⛔ STOP / 🔄 FLEX 三級規則標記，明確標示可修改與不可修改位置
- `assets/portainer-agent-stack.yml`: Portainer Agent 多節點部署模板，用於管理遠程 Docker 主機（可選）