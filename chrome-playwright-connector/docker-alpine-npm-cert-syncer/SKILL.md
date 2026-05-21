---
# ============================================================
# YAML Frontmatter — Agent 快速篩選 Metadata
# 此區塊為 Agent 啟動時唯一讀取的部分，正文不載入 Context Window
# ============================================================

name: docker-alpine-npm-cert-syncer
description: >
  Nginx Proxy Manager (NPM) Let's Encrypt 證書自動同步與標準化技能。
  當用戶提及證書同步、NPM、Let's Encrypt、Elasticsearch SSL、Kibana 證書等關鍵詞時激活。
  協調 Docker 運維專家與證書架構師完成證書標準化與自動續約重載。

triggers:
  - cert-sync
  - alpine cert
  - npm certificate
  - letsencrypt sync
  - elasticsearch ssl
  - kibana certificate
  - 證書同步
  - 憑證更新
  - ssl certificate
  - fullchain.pem
  - privkey.pem
  - 證書標準化
  - NPM 證書

allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Edit

compatibility: >
  Requires Docker Compose v2.29+,
  支援 Windows Docker Desktop / macOS Docker Desktop / Linux Docker CE / QNAP Container Station.
  依賴 Nginx Proxy Manager 已生成的 Let's Encrypt 證書卷.

user-invocable: true
disable-model-invocation: false

metadata:
  category: infrastructure
  subcategory: certificate-management
  team: devops
  priority: high
  version: 1.0.0
  author: Generator
  last.updated: 2026-04-26
  target.platforms:
    - windows
    - macos
    - linux
    - qnap
---

# ============================================================
# 命名規則變量定義 🔒 LOCK v0.0 PERMANENT
# ============================================================

## 核心命名變量

| 變量類型 | 格式 | 說明 | 示例 |
|:---------|:-----|:-----|:-----|
| SKILL_FOLDER | <CATEGORY>-<PROJECT>-<PURPOSE> | 技能文件夾名稱（使用連字符） | docker-alpine-npm-cert-syncer |
| COMPOSE_NAME | <PROJECT>_<PURPOSE> | Docker Compose 項目名（使用底線） | alpine_npm_cert_syncer |
| CONTAINER_NAME | <PROJECT>.<PURPOSE>.<PORT> | 容器名稱（使用點號） | alpine.npm.cert.syncer |
| PURPOSE_NAME | <PURPOSE> | 用途標識（使用點號） | npm.cert.syncer |

### 變量對照表

| 變量 | 值 | 用途 |
|:-----|:---|:-----|
| SKILL_FOLDER | docker-alpine-npm-cert-syncer | 技能文件夾名稱 |
| COMPOSE_NAME | alpine_npm_cert_syncer | docker-compose.yaml 中的 COMPOSE_PROJECT_NAME |
| CONTAINER_NAME | alpine.npm.cert.syncer | Docker 容器名稱 |
| PURPOSE_NAME | npm.cert.syncer | 腳本和配置文件命名前綴 |

---

# ============================================================
# 技能目錄結構
# ============================================================

```
docker-alpine-npm-cert-syncer/
├── SKILL.md                          ← 本文件（核心指令 + Metadata）
├── scripts/
│   ├── init.npm.cert.syncer.sh             ← 首次環境初始化（檢查 Docker、卷、容器、腳本）
│   └── validate.npm.cert.syncer.sh        ← 驗證同步結果與證書有效性
├── references/
│   ├── alpine.npm.cert.syncer.path.spec.md         ← NPM 證書存儲路徑規格
│   └── alpine.npm.cert.syncer.guide.md     ← 操作指南與故障排查
└── assets/
    ├── docker.compose.npm.cert.syncer.yaml ← Docker Compose 實施模板
    ├── entrypoint.npm.cert.syncer.sh     ← 容器入口同步腳本
    └── test.entrypoint.sh               ← 測試用入口腳本（可選）
```

---

# ============================================================
# 正文區塊 — 僅在 Agent 匹配成功後載入
# ============================================================

# docker-alpine-npm-cert-syncer 證書同步標準化技能

## 角色定位
- **CertSync Architect（證書同步架構師）**：負責設計證書標準化流程、確保 fullchain/privkey/cert 命名符合行業慣例，規劃 ISRG Root X1 根證書的自動更新策略。
- **Docker Operator（容器運維專家）**：負責 Docker Compose 部署、監控容器健康狀態、處理 docker.sock 掛載安全審查、驗證證書卷權限。

## 工作流程

### 1. 召喚階段（Summon）
sub-agent：
- **CertSync Architect**：確認 NPM 證書卷名稱與路徑、確認 ES 容器名稱、輸出 docker.compose.npm.cert.syncer.yaml 與 entrypoint.npm.cert.syncer.sh
- **Docker Operator**：確認 Docker 守護進程狀態、檢查外部卷存在性、審查 docker.sock 掛載風險

### 2. 監控階段（Monitor）
- 監控 /certs-sync 目錄內容（fullchain.pem / privkey.pem / cert.pem）
- 檢查 .hash 文件時間戳，識別證書續約事件
- 驗證 ISRG Root X1 根證書有效期（30 天輪詢）
- 確認 ES 容器重啟後健康狀態

### 3. 記錄階段（Record）
- 記錄每次同步的證書序列號（serial number）
- 記錄 fullchain.pem 的 md5 hash 變更歷史
- 記錄 ES 重啟時間與觸發原因（CERT.RENEWAL / MANUAL）
- 記錄根證書更新時間與下載來源

### 4. 報告階段（Report）
- 輸出標準化證書狀態報告（參考下方報告模板）
- 異常時輸出 CONFLICT.REPORT.md 標記 AWAITING.RESOLUTION

## 報告模板

```
[docker-alpine-npm-cert-syncer REPORT] 生成時間: <TIMESTAMP>
============================================================
命名規則變量：
  - SKILL_FOLDER: docker-alpine-npm-cert-syncer
  - COMPOSE_NAME: alpine_npm_cert_syncer
  - CONTAINER_NAME: alpine.npm.cert.syncer
  - PURPOSE_NAME: npm.cert.syncer
============================================================
1. 證書來源狀態
   NPM 卷路徑    : <NPM.ARCHIVE.PATH>
   最新序號      : <CERT.NUM>
   來源 Hash     : <SOURCE.HASH>

2. 同步目標狀態
   同步卷路徑    : /certs-sync
   已同步文件    : fullchain.pem, privkey.pem, cert.pem
   同步 Hash     : <SYNC.HASH>
   最後同步時間  : <LAST.SYNC>

3. 根證書狀態
   ISRG Root X1  : /certs-sync/isrgrootx1.pem
   更新時間      : <ROOT.UPDATE.TIME>
   有效期檢查    : <VALID/EXPIRED>

4. 下游服務狀態
   ES 容器名稱   : <ES.CONTAINER.NAME>
   最後重啟時間  : <LAST.RESTART>
   重啟觸發原因  : <CERT.RENEWAL / MANUAL>

5. 健康檢查
   容器狀態      : <HEALTHY/UNHEALTHY>
   容器名稱      : alpine.npm.cert.syncer
   下次檢查      : <NEXT.CHECK>
============================================================
```

## 互動模式

1. 用戶提及觸發詞（cert-sync / npm 證書 / elasticsearch ssl 等）
2. Agent 確認環境參數（COMPOSE_NAME, CONTAINER_NAME, ES.CONTAINER.NAME, NPM 卷名稱）
3. 輸出 docker.compose.npm.cert.syncer.yaml 與 assets/entrypoint.npm.cert.syncer.sh
4. 指引用戶執行 scripts/init.npm.cert.syncer.sh 完成前置檢查
5. 啟動服務：docker compose up -d
6. 執行 scripts/validate.npm.cert.syncer.sh 確認同步成功

## 實作細節

### Scripts（核心腳本，最少 Token 設計）
- `scripts/init.npm.cert.syncer.sh`: 首次環境初始化（檢查 Docker、卷、容器、腳本路徑）
- `scripts/validate.npm.cert.syncer.sh`: 驗證同步結果（容器狀態、證書完整性、Hash 記錄、根證書）

### References
- `references/alpine.npm.cert.syncer.path.spec.md`: NPM 證書存儲路徑規格、命名規則、卷名稱慣例、標準化映射對照表
- `references/alpine.npm.cert.syncer.guide.md`: 操作指南、快速開始步驟、故障排查矩陣、安全注意事項、進階配置

### Assets
- `assets/docker.compose.npm.cert.syncer.yaml`: Docker Compose 實施模板，含 🔒 LOCK / ⛔ STOP / 🔄 FLEX 三級規則標記，明確標示可修改與不可修改位置
- `assets/entrypoint.npm.cert.syncer.sh`: 容器入口同步腳本，處理證書標準化命名、ISRG Root X1 下載、ES 自動重啟邏輯
- `assets/test.entrypoint.sh`: 測試用入口腳本

---

# ============================================================
# 命名規則詳細說明
# ============================================================

## 檔案命名格式 🔒 LOCK v1.0 PERMANENT

所有技能包內檔案名稱統一使用 xxx.yyy.zzz.ext 格式。
全部以點號（.）作為分隔符，禁止使用中劃線（-）或下劃線（_）。

正確示例：
  - init.npm.cert.syncer.sh
  - validate.npm.cert.syncer.sh
  - docker.compose.npm.cert.syncer.yaml
  - alpine.npm.cert.syncer.guide.md
  - entrypoint.npm.cert.syncer.sh

## COMPOSE_NAME Docker 命名限制 🔒 LOCK v1.0-A PERMANENT

僅限 COMPOSE_NAME（COMPOSE-PROJECT-NAME）必須遵守 Docker 引擎命名限制。
此限制不影響檔案命名（規範一）或其他 Docker 資源命名。

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

本技能 COMPOSE_NAME：alpine_npm_cert_syncer

## CONTAINER_NAME 命名格式 🔒 LOCK v1.0-B PERMANENT

容器名稱格式：<PROJECT>.<PURPOSE>.<PORT>
分隔符：點號（.）
Docker 引擎允許容器名含點號，因此遵循檔案命名點號格式。

本技能 CONTAINER_NAME：alpine.npm.cert.syncer

## 部署命令統一 🔒 LOCK v1.1 PERMANENT

所有涉及 Docker 部署的技能，全程使用 docker compose 命令。
禁止使用 docker run 作為主要部署方式。

正確示例：
  - docker compose -f assets/docker.compose.npm.cert.syncer.yaml up -d
  - docker compose -f assets/docker.compose.npm.cert.syncer.yaml ps
  - docker compose -f assets/docker.compose.npm.cert.syncer.yaml logs -f

---

# ============================================================
# 踩坑經驗
# ============================================================

### Docker Compose 項目名命名規則
**問題描述**：
Docker Compose 項目名（COMPOSE_PROJECT_NAME）不能包含點號（.），因為 Docker 網絡名禁止點號。

**解決方案**：
1. **技能文件夾名**：使用連字符（-），例如 `docker-alpine-npm-cert-syncer`
2. **COMPOSE_PROJECT_NAME**：使用底線（_），例如 `alpine_npm_cert_syncer`
3. **容器名**：可保留點號（.），例如 `alpine.npm.cert.syncer`
4. **檔案名**：使用點號（.），例如 `init.npm.cert.syncer.sh`

**驗證命令**：
```bash
# 檢查項目名是否合法
docker compose config

# 顯式指定項目名啟動
COMPOSE_PROJECT_NAME=alpine_npm_cert_syncer docker compose up -d
```

**常見錯誤**：
- 使用點號：`alpine.npm.cert.syncer` ❌（作為 COMPOSE_PROJECT_NAME）
- 使用空格：`alpine npm cert syncer` ❌  
- 使用大寫：`Alpine-Npm-Cert-Syncer` ❌
- 正確格式：`alpine_npm_cert_syncer` ✅
