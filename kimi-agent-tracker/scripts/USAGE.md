---
title: "Kimi Agent Tracker - CLI Usage Guide"
name: "kimi-agent-tracker"
description: "CLI 用法教程。所有參數調整通過單一 config.json，禁止編輯腳本，不使用 .env。"
version: "5.5.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-31T23:30:00+08:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{baseDir}/scripts/USAGE.md"
  github_path: "kimi-agent-tracker/scripts/USAGE.md"
---

# Kimi Agent Tracker — CLI 用法教程

版本：v5.3.0 | 更新時間：2026-05-31

## 核心原則

所有參數調整通過 `.config/kimi_tracker_config.json`，禁止編輯 `.py` 腳本。
本技能不使用 `.env`，所有配置集中於單一 JSON 檔案。

## 快速開始

### Step 0: 環境檢查

    python3 -m pip list | grep playwright
    python3 -m playwright install chromium

### Step 1: 確認配置檔案

檢查 `.config/kimi_tracker_config.json` 是否存在：

    ls .config/kimi_tracker_config.json

如需調整參數，直接編輯此檔案。例如修改 daemon 循環間隔：

    # 編輯 .config/kimi_tracker_config.json
    "daemon": {
      "interval_sec": 1800    # 改為 30 分鐘
    }

### Step 2: 首次登入

    python3 scripts/kimi_login_manager.py --visible --stay-open 300

在瀏覽器中完成 SMS 登入，腳本自動檢測並保存 session。

### Step 3: 驗證登入態

    python3 scripts/kimi_login_manager.py --validate

預期輸出：`[VALIDATE] Login valid: True`

### Step 4: 提取對話列表 (v5.1.0)

    # 提取對話列表
    python3 scripts/kimi_conversation_lister.py --limit 10

    # 可見模式調試
    python3 scripts/kimi_conversation_lister.py --visible --limit 5

    # 執行單元測試（無需瀏覽器）
    python3 scripts/kimi_conversation_lister.py --test

### Step 5: 批量下載

    python3 scripts/kimi_downloader.py --url "https://www.kimi.com/chat/..." --file-types py,md,json

### Step 6: 啟動 Daemon

    python3 scripts/tracker_daemon.py --start

## 常用命令速查

### F-001 登入管理 (v4.0.0)

| 命令 | 用途 |
|------|------|
| `--validate` | 驗證現有 session |
| `--force-login --visible --stay-open 300` | 強制重新登入 |
| `--diagnose` | 診斷登入頁面結構 |
| `--test` | 執行 AST 單元測試（無需瀏覽器） |

**v4.0.0 更新**：lazy import `browser_connector`（測試模式無需 playwright），`_BROWSER_AVAILABLE` 守衛。

### F-002 對話列表 (v5.1.0)

| 命令 | 用途 |
|------|------|
| `--limit N` | 提取 N 個對話 |
| `--output NAME` | 指定輸出檔名 |
| `--visible` | 顯示瀏覽器窗口 |
| `--trace` | 啟用 Playwright trace |
| `--profile-dir PATH` | 指定 browser profile 目錄 |
| `--test` | 執行 AST 單元測試（無需瀏覽器） |

**v5.1.0 新增功能**：
- `Tracer` 參數：記錄所有 UI 操作（navigate, scroll, selector match, extract）
- `report_to_manager()`：結構化報告 `{ chats_found, chats_valid, chats_invalid, total_elapsed }`
- `--test` 模塊：10 項 AST 單元測試，覆蓋 Tracer 四種模式、狀態文件導入

### F-003 下載器 (v5.3.0) — Download Button + HTTP Header 驗證

**下載方式**：點擊檔案 → 預覽面板 → 點擊 Download 按鈕 → 瀏覽器原生下載

| 命令 | 用途 |
|------|------|
| `--conversation-json PATH` | 讀取 conversations.json（由 Lister 生成） |
| `--max-files N` | 每個對話最多下載 N 個文件 |
| `--visible` | 顯示瀏覽器窗口 |
| `--download-dir PATH` | 指定下載目錄 |
| `--profile-dir PATH` | 指定 browser profile 目錄 |
| `--test` | 執行 AST 單元測試（無需瀏覽器） |

**v5.3.0 架構變更**：

| 項目 | v5.1.3（舊） | v5.3.0（新） |
|------|-------------|-------------|
| 下載方式 | preview panel `innerText` 提取 | Download 按鈕 → 瀏覽器原生下載 |
| HTTP headers | 無 | `content-length`, `etag`, `last-modified`, `content-type` |
| 大小驗證 | 無 | `actual_size == Content-Length`（100% 匹配才算成功） |
| 多文件 | 連續 DOM 點擊（文件 2/3 失敗） | 每個文件前 `page.goto()` reload（100% 成功） |
| header 捕獲 | 無 | 每文件獨立 `page.on("response")` + `finally` 清理 |
| 拒絕未驗證數據 | 無 | `size_mismatch` 狀態標記，ETag 唯一性判定 |

**驗證指標**：HTTP header `Content-Length` + 檔案實際大小 **百分百一致** 才算成功下載。

### F-004 下載管理器 (v5.1.0) — 业务逻辑核心

| 命令 | 用途 |
|------|------|
| `--interval N` | 循环间隔秒数（SAFETY_MARGIN=30s） |
| `--total-timeout N` | 总超时秒数 |
| `--once` | 单次执行 |
| `--test` | 执行 AST + tracer 单元测试 |

**v5.1.0 新增功能**：tracer_to_logger、check_etag_match、head_pre_check、session_expired 管理、update_download_state 富化 HTTP headers。

### F-005 Daemon (v5.0.0)

| 命令 | 用途 |
|------|------|
| `--start` | 啟動守護程序 |
| `--stop` | 停止守護程序 |
| `--status` | 查看運行狀態 |
| `--run-once` | 單次執行（測試） |
| `--interval N` | 覆蓋循環間隔（秒） |

### F-006 Core Tracer (v1.0.0)

| 命令 | 用途 |
|------|------|
| `--trace-zip PATH` | 解壓並分析 Playwright trace.zip |
| `--trace-dir PATH` | 直接分析已解壓的 trace/ 目錄 |
| `--output NAME` | 指定輸出 JSON 文件名 |
| `--test` | 執行 AST 單元測試（無需瀏覽器） |

**v1.0.0 新增功能**：
- `Tracer` 類：記錄帶時間戳的事件，支援 paired timing (`{tag}.start` / `{tag}.done`)
- `get_summary()`：返回 `{ total_events, unique_event_types, elapsed_total, paired_timings }`
- `export_json(path)`：匯出完整事件紀錄為 JSON
- `clear()`：重置內部狀態
- 向後兼容 `trace_minifier.py`（`DOMSummaryExtractor` + `minify_trace` + `main` CLI）

## 配置調整速查

編輯 `.config/kimi_tracker_config.json`：

| 需求 | 修改路徑 | 默認值 |
|------|---------|--------|
| 平台 URL | platform.base_url | https://www.kimi.com |
| 登入等待更久 | login.max_login_wait_sec | 600 |
| 檢測更頻密 | login.login_check_interval_sec | 3 |
| 強制每次重新認證 | login.force_reauth | false |
| daemon 更頻密 | daemon.interval_sec | 900 |
| 每次下載更多對話 | daemon.conversation_count | 10 |
| 下載文件類型 | file_types | "" |
| 日誌級別 | logging.level | INFO |

## 故障排查

| 症狀 | 排查步驟 |
|------|---------|
| validate False | 執行 `--force-login --visible` 重新登入 |
| 提取 0 個對話 | 先 `--validate`，再 `--diagnose` |
| .md 下載失敗 | 確認 preview panel 打開後有 format menu |
| .py/.json 下載失敗 | 確認 `pre code` 元素存在（DevTools 檢查） |
| daemon 不啟動 | `tracker_daemon.py --status` 檢查 PID |
| selector 不匹配 | 更新 config，禁止改腳本 |

## Pytest 結果 — kimi_conversation_lister.py v5.1.0

執行命令：

    cd scripts && python3 kimi_conversation_lister.py --test

完整原始輸出 (2026-05-31, 10/10 passed)：

    ============================================================
      TEST RESULTS: 10/10 passed, 0 failed
    ============================================================
      [PASS] T1  test_tracer_init: tracer accessible via lister.tracer
      [PASS] T2  test_tracer_none_graceful: tracer=None accepted
      [PASS] T3  test_tracer_record_call: event=navigate.start, data={'url': 'https://kimi.com/chat/history'}
      [PASS] T3b test_tracer_callable: callable tracer received event=test.event
      [PASS] T3c test_tracer_exception_safe: no exception raised
      [PASS] T4  test_report_to_manager_format: {"chats_found": 5, "chats_valid": 5, "chats_invalid": 0, "total_elapsed": 1780228101.664}
      [PASS] T5  test_report_to_manager_empty: {'chats_found': 0, 'chats_valid': 0, 'chats_invalid': 0, 'total_elapsed': 1780228101.664}
      [PASS] T6  test_card_selectors_present: 
        [0] a[href*="/chat/"]
        [1] [class*="history"] a
        [2] [class*="chat-card"]
        [3] [class*="conversation-card"]
        [4] [class*="session-card"]
        [5] div[class] > a[href*="chat"]
      [PASS] T7  test_core_path_utils_import: skill_dir=/Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker
        config_dir=/Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker/config
        data_dir=/Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker/data
        logs_dir=/Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker/logs
        exports: get_skill_dir, get_config_dir, get_data_dir, get_logs_dir, get_download_dir, get_tracker_config_path, get_conversations_json_path, get_download_state_path
      [PASS] T8  test_core_logger_import: type=CoreLogger, methods=['debug', 'error', 'fatal', 'info', 'metric', 'step', 'warn']
    ============================================================

### Tracer 測試覆蓋矩陣

| 場景 | 測試 | tracer 值 | 行為 |
|------|:---:|-----------|------|
| 無 tracer | T2 | `None` | `_trace()` 靜默跳過 |
| 對象 `.record()` | T1, T3 | `MockTracer()` | 調用 `tracer.record(event, data)` |
| callable | T3b | `def fn(event, data)` | 調用 `tracer(event, data)` |
| 拋出異常 | T3c | `FailingTracer()` | `_trace()` 捕獲異常，不崩潰 |

## Pytest 結果 — core_tracer.py v1.0.0

執行命令：

    cd scripts && python3 core_tracer.py --test

完整原始輸出 (2026-05-31, 10/10 passed, exit code 0)：

    ============================================================
      core_tracer.py — UNIT TESTS (AST only, no browser)
    ============================================================
      [PASS] T1  test_record_stores_event: event=navigate.start, has_timestamp=True
      [PASS] T2  test_record_preserves_data: data={"selector": "a.chat-link", "count": 3}
      [PASS] T3  test_get_summary_structure: {"name": "t3", "total_events": 3, "unique_event_types": ["extract.done", "scroll.done"], "elapsed_total": 8.106231689453125e-06, "paired_timings": {"extract": null, "scroll": null}}
      [PASS] T4  test_get_timing_paired: paired timing=0.0600s
      [PASS] T5  test_get_timing_unpaired: unpaired timing=None ✓
      [PASS] T6  test_export_json_valid: name=t6, events=2
      [PASS] T7  test_export_json_roundtrip: events=[{"event": "event.one", "timestamp": 1780229476.138774, "data": {"a": 1}}, {"event": "event.two", "timestamp": 1780229476.138775, "data": {"b": 2, "c": "hello"}}]
      [PASS] T8  test_dom_extractor_elements: links=[{"tag": "a", "depth": 0, "id": null, "classes": null, "href": "/chat/1", "text_preview": "Chat 1"}, {"tag": "a", "depth": 0, "id": null, "classes": null, "href": "/chat/2", "text_preview": "Chat 2"}]
      [PASS] T9  test_dom_extractor_classes_ids: classes=['active', 'chat-card'], ids=['msg-1']
      [PASS] T10 test_clear_resets: events_after_clear=0, summary_events=0

    ============================================================
      TEST RESULTS: 10/10 passed, 0 failed
    ============================================================

### Tracer 關鍵設計決策

| 項目 | 說明 |
|------|------|
| `record(event, **data)` | 附加 `event` + `timestamp` + `data`，無返回值 |
| `get_summary()` | `name`, `total_events`, `unique_event_types`, `elapsed_total`, `paired_timings` |
| `get_timing(tag)` | `start` / `done` 都有 → `float`；任一缺失 → `None` |
| `export_json(path)` | 包含 `summary` + `events` 完整歷史，確保目錄存在 |
| `clear()` | 清空 `_events` + 重置 `_start_time` |
| 向後兼容 | `DOMSummaryExtractor` + `minify_trace()` + `main()` CLI 原樣保留 |

## Pytest 結果 — core_path_utils.py v5.0.0（公用模塊）

> **適用範圍**：所有 `core_*.py` 及其引用者。非 kimi-agent-tracker 專用。

執行命令：

    cd scripts && python3 core_path_utils.py --test

完整原始輸出 (2026-05-31, 10/10 passed, exit code 0)：

    ============================================================
      core_path_utils.py — UNIT TESTS (AST only)
    ============================================================
      [PASS] T1  test_get_skill_dir: /Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker
      [PASS] T2  test_resolve_base_dir: /Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker/config
      [PASS] T3  test_resolve_home: resolved=/Users/kevinlinz/test_xyz_path, home=/Users/kevinlinz
      [PASS] T4  test_ensure_dir_creates: /var/.../T/kimi_test_ensure_1780229941
      [PASS] T5  test_get_config_dir: /Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker/config
      [PASS] T6  test_get_data_dir: /Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker/data
      [PASS] T7  test_get_logs_dir: /Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker/logs
      [PASS] T8  test_get_download_dir: /Users/kevinlinz/Downloads
      [PASS] T9  test_get_conversations_json: /Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker/config/conversations.json
      [PASS] T10 test_tracker_config_and_state: config=tracker_config.json, state=download_state.json

    ============================================================
      TEST RESULTS: 10/10 passed, 0 failed
    ============================================================

## Pytest 結果 — core_logger.py v5.0.0（公用模塊）

> **適用範圍**：所有 `core_*.py` 及其引用者。非 kimi-agent-tracker 專用。

執行命令：

    cd scripts && python3 core_logger.py --test

完整原始輸出 (2026-05-31, 10/10 passed, exit code 0)：

    ============================================================
      core_logger.py — UNIT TESTS (AST only)
    ============================================================
      [PASS] T1  test_init_no_file: component=T1, log_file=None
      [PASS] T2  test_init_with_file: component=T2, log_file=/var/.../kimi_logger_test_....log
      [PASS] T3  test_info_output: [2026-05-31T12:19:40.371+00:00] [INFO] [T3] hello world
      [PASS] T4  test_warn_output: [2026-05-31T12:19:40.372+00:00] [WARN] [T4] test warning
      [PASS] T5  test_error_output: [2026-05-31T12:19:40.372+00:00] [ERROR] [T5] critical error
      [PASS] T6  test_debug_and_fatal: [2026-05-31T12:19:40.372+00:00] [DEBUG] [T6] debug msg | [2026-05-31T12:19:40.372+00:00] [FATAL] [T6] fatal msg
      [PASS] T7  test_step_format: [2026-05-31T12:19:40.372+00:00] [STEP] [T7] [S001] Config loaded successfully
      [PASS] T8  test_metric_format: [2026-05-31T12:19:40.372+00:00] [METRIC] [T8] cycle_time=45s
      [PASS] T9  test_file_writing: lines=2, file=/var/.../kimi_logger_file_test_....log
      [PASS] T10 test_get_default_logger: type=CoreLogger, component=T10_TEST, log_file=tracker.log

    ============================================================
      TEST RESULTS: 10/10 passed, 0 failed
    ============================================================

## core_*.py 測試總覽（3 個公用模塊）

| 文件 | 版本 | 測試 | 結果 | 執行命令 |
|------|------|:--:|:--:|------|
| `core_tracer.py` | 1.0.0 | 10 | ✅ | `python3 core_tracer.py --test` |
| `core_path_utils.py` | 5.0.0 | 10 | ✅ | `python3 core_path_utils.py --test` |
| `core_logger.py` | 5.0.0 | 10 | ✅ | `python3 core_logger.py --test` |
| **合計** | | **30** | **✅ 30/30** | |

## Pytest 結果 — kimi_downloader.py v5.3.0

執行命令：

    cd scripts && python3 kimi_downloader.py --test

完整原始輸出 (2026-05-31, 12/12 passed, exit code 0)：

    ============================================================
      kimi_downloader.py — UNIT TESTS (AST only, no browser)
    ============================================================
      [PASS] T1  test_default_init: headless=True, dl_dir=kimi_downloads, tracer=None
      [PASS] T2  test_custom_init: headless=False, dl_dir=/tmp/kimi_test_dl
      [PASS] T3  test_now_iso_format: 2026-05-31T23:29:53
      [PASS] T4  test_is_cached_true: file exists: /var/.../kimi_cache_test_.../hello.py
      [PASS] T5  test_is_cached_false
      [PASS] T6  test_simple_logger_methods: info/debug/warning/error all OK
      [PASS] T7  test_core_path_utils_import: skill=kimi-agent-tracker, config=config, data=data, logs=logs
      [PASS] T8  test_core_logger_import: type=CoreLogger, methods=['debug','error','fatal','info','metric','step','warn']
      [PASS] T9  test_session_seen_populate: seen={'file_b.py', 'file_a.py'}
      [PASS] T10 test_cli_args_parse: json=test.json, max=5, visible=True
      [PASS] T11 test_tracer_events: calls=[('test.event.one', ['key']), ('test.event.two', ['count'])]
      [PASS] T12 test_sync_playwright_import: system python: OK

    ============================================================
      TEST RESULTS: 12/12 passed, 0 failed
    ============================================================

## 真實下載測試 — HTTP Header 雙驗證 (2026-05-31)

測試命令：

    python3 kimi_downloader.py \
      --conversation-json config/conversations.json \
      --max-files 3 --visible --download-dir /tmp/kimi_test_dl

下載目錄：`/tmp/kimi_test_dl/`

### HTTP Header + File Content 驗證結果（3/3 百分百匹配）

| 文件 | 實際大小 | Content-Length | ETag | Last-Modified | size_verified |
|------|:---:|:---:|------|------|:---:|
| `kimi_conversation_lister_v500.py` | 11826 | 11826 | `ce1a5e89e810...` | 2026-05-28 01:02:59 GMT | ✅ |
| `trace_minifier_v500.py` | 10330 | 10330 | `1e437ddef111...` | 2026-05-28 02:33:17 GMT | ✅ |
| `kimi_conversation_lister_v501.py` | 13822 | 13822 | `40e2611ddb5d...` | 2026-05-28 02:35:31 GMT | ✅ |

### 完整原始輸出

    [DL] kimi_conversation_lister_v500.py
    [OK] kimi_conversation_lister_v500.py (11826 bytes) | etag="ce1a5e89e81 | size_ok=Y
    [RELOAD] Refreshing page for next file...
    [DL] trace_minifier_v500.py
    [OK] trace_minifier_v500.py (10330 bytes) | etag="1e437ddef11 | size_ok=Y
    [RELOAD] Refreshing page for next file...
    [DL] kimi_conversation_lister_v501.py
    [OK] kimi_conversation_lister_v501.py (13822 bytes) | etag="40e2611ddb5 | size_ok=Y
    [DONE] OK:3 CACHE:0 FAIL:0

### batch_report 完整原始內容

```json
{
  "version": "5.3.0",
  "downloaded": 3, "cached": 0, "failed": 0,
  "download_dir": "/tmp/kimi_test_dl",
  "results": [
    {
      "name": "kimi_conversation_lister_v500.py",
      "status": "success", "size": 11826,
      "content_type": "text/x-python",
      "etag": "\"ce1a5e89e810ba64e412af4f08e2e8b8\"",
      "last_modified": "Thu, 28 May 2026 01:02:59 GMT",
      "content_length": "11826", "size_verified": true
    },
    {
      "name": "trace_minifier_v500.py",
      "status": "success", "size": 10330,
      "content_type": "text/x-python",
      "etag": "\"1e437ddef1114a4bc51e21ce3fec8cb7\"",
      "last_modified": "Thu, 28 May 2026 02:33:17 GMT",
      "content_length": "10330", "size_verified": true
    },
    {
      "name": "kimi_conversation_lister_v501.py",
      "status": "success", "size": 13822,
      "content_type": "text/x-python",
      "etag": "\"40e2611ddb5debd97f7931c6b0b8e19d\"",
      "last_modified": "Thu, 28 May 2026 02:35:31 GMT",
      "content_length": "13822", "size_verified": true
    }
  ]
}
```

### 下載失敗標記規則（拒絕未驗證數據）

| 狀態 | 含義 | 觸發條件 |
|------|------|---------|
| `success` | ✅ 成功 | 下載完成 + `actual_size == Content-Length` |
| `size_mismatch` | ❌ 失敗 | 下載完成但 `actual_size != Content-Length` |
| `failed` | ❌ 失敗 | Cannot click / Download failed |
| `cached` | ⏭️ 跳過 | 本地已存在同名檔案 |
| `skipped` | ⏭️ 跳過 | 同一 session 內重複檔案 |

### 狀態文件架構

| 文件 | 位置 | 屬性 | 作用 |
|------|------|------|------|
| `conversations.json` | `config/` | **可重建** | Lister 輸出，記錄對話列表 + finding 狀態 |
| `download_state.json` | `data/` | **不可重建** | 累積下載歷史 + SHA256 去重 |
| `batch_report_*.json` | `data/` | 每週期產出 | 含完整 HTTP headers + size_verified |

## Pytest 結果 — kimi_login_manager.py v4.0.0

執行命令：

    cd scripts && python3 kimi_login_manager.py --test

完整原始輸出 (2026-05-31, 10/10 passed, exit code 0)：

    ============================================================
      kimi_login_manager.py — UNIT TESTS (AST only, no browser)
    ============================================================
      [PASS] T1  test_config_loaded: base_url=https://www.kimi.com
      [PASS] T2  test_config_defaults: stay=300, max_wait=600, interval=3
      [PASS] T3  test_config_selectors: selectors=['.chat-info-item', '.user-avatar', '.user-name']
      [PASS] T4  test_resolve_base_dir: /Users/kevinlinz/.workbuddy/skills/kimi-agent-tracker/config/test.json
      [PASS] T5  test_resolve_no_template: /absolute/path/to/file.txt
      [PASS] T6  test_load_config_returns_dict: keys=['diagnose', 'login', 'platform', 'selectors']
      [PASS] T7  test_login_indicators_all_str: indicators=['.chat-info-item', '.user-avatar', '.user-name']
      [PASS] T8  test_cli_validate_flag
      [PASS] T9  test_cli_diagnose_flag
      [PASS] T10 test_cli_combined_flags: validate=True, visible=True, profile=test_profile

    ============================================================
      TEST RESULTS: 10/10 passed, 0 failed
    ============================================================

## Pytest 結果 — kimi_download_manager.py v5.1.0

執行命令：

    cd scripts && python3 kimi_download_manager.py --test

完整原始輸出 (2026-06-01, 15/15 passed, exit code 0)：

    ============================================================
      kimi_download_manager.py — UNIT TESTS (AST + tracer)
    ============================================================
      [PASS] T1  test_constants: DEFAULT=20, INC=20, MAX=120, MARGIN=30
      [PASS] T2  test_step_logger: calls=[('step', 'S001', 'test message')]
      [PASS] T3  test_metric_logger: last_call=('metric', 'key1', 'val1')
      [PASS] T4  test_load_tracker_config: type=dict, keys=['conversations', 'deduplication', 'download_dir', 'headless', 'poll_interval_seconds']
      [PASS] T5  test_conversations_json_roundtrip: saved=1, loaded=1
      [PASS] T6  test_download_state_roundtrip: keys=['conversations', 'global_stats']
      [PASS] T7  test_head_pre_check_structure: keys=['content_length', 'error', 'filename', 'status']
      [PASS] T8  test_tracer_compress_to_logger: calls=[('info', "[TRACER] events=2 types=['step.done', 'step.start'] elapsed="), ('metric', 'trace_step_sec')]
      [PASS] T9  test_total_timeout_10s_stops: elapsed=5.0s, remaining=5.0s, margin=30 → would break
      [PASS] T10 test_session_expired_state_tracked: session={'expired': True, 'expired_at': '2026-06-01T00:26:43', 'expired_reason': 'validate returned 401'}
      [PASS] T11 test_session_expired_opens_login: expired=True, reason=timeout
      [PASS] T12 test_rerun_skips_expired_session: expired=True, would skip 1 conversations
      [PASS] T13 test_cli_args_all: interval=60, once=True, total_timeout=30
      [PASS] T14 test_etag_skip_logic: files=2, all_verified=True, skip=True
      [PASS] T15 test_head_pre_check_phase_a: status=200, err=

    ============================================================
      TEST RESULTS: 15/15 passed, 0 failed
    ============================================================

### run_cycle 完整 Step 流程（v5.1.0）

| Step | 功能 | 新增 |
|------|------|:---:|
| S001 | Tracer 创建 + cycle.start | v5.1.0 |
| S002 | 加载 tracker_config.json | |
| S003 | 检查 conversations 配置 | |
| S004 | 自动发现 / 手动指定对话 | |
| S005 | 保存 conversations.json | |
| S005A | HEAD pre-check 对话 URL | v5.1.0 |
| S006 | 加载 download_state.json | |
| S006E | 检查 session expired → run_login_flow | v5.1.0 |
| S007 | 浏览器 visible 设置 | |
| S008 | 遍历 conversations | |
| S008-S | ETag 比对 → 跳过已下载文件 | v5.1.0 |
| S009-W | SAFETY_MARGIN 保护（30s） | |
| S012 | 记录每对话下载结果 + update_download_state | |
| S013 | 循环完成统计 | |
| S014 | save_download_state + tracer_to_logger | v5.1.0 |

### 已集成功能（v5.1.0）

| 功能 | 说明 |
|------|------|
| `tracer_to_logger` | S001 创建 Tracer → S014 压缩到 logger |
| `check_etag_match` | S008-S 下载前比对 ETag，相同则跳过 |
| `head_pre_check` | S005A Phase A 对对话 URL 做 HEAD 验证 |
| `update_download_state` | 富化 HTTP headers（ETag/Content-Length/Last-Modified）到 download_state.json |
| `run_login_flow` | session expired 时自动调用 login_manager |
| 渐进超时 | timeout=20s, inc=20s, max=120s, SAFETY_MARGIN=30s |

### 全脚本測試總覽

| 文件 | 測試 | 結果 | 執行命令 |
|------|:--:|:--:|------|
| `core_tracer.py` | 10 | ✅ | `python3 core_tracer.py --test` |
| `core_path_utils.py` | 10 | ✅ | `python3 core_path_utils.py --test` |
| `core_logger.py` | 10 | ✅ | `python3 core_logger.py --test` |
| `kimi_conversation_lister.py` | 10 | ✅ | `python3 kimi_conversation_lister.py --test` |
| `kimi_downloader.py` | 11 | ✅ | `python3 kimi_downloader.py --test` |
| `kimi_login_manager.py` | 10 | ✅ | `python3 kimi_login_manager.py --test` |
| `kimi_download_manager.py` | 15 | ✅ | `python3 kimi_download_manager.py --test` |
| **合計** | **76** | **✅ 76/76** | |

## 目錄結構

    {baseDir}/
    ├── .config/
    │   ├── kimi_tracker_config.json    # 唯一配置中心
    │   ├── conversations.json          # 運行時狀態
    │   └── downloads.json              # 運行時狀態
    ├── .logs/
    │   └── diagnose/                   # 診斷輸出
    ├── downloads/                      # 成功下載
    ├── .duplicate/                     # 重複歸檔
    ├── references/
    │   └── KIMI_TRACKER_USAGE_PLAN.md  # 完整計劃書
    └── scripts/                        # 全部腳本

## 注意

本技能不使用 `.env` 或 `.env.example`。
所有環境相關參數（如 `KIMI_BASE_URL`、`LOG_LEVEL`）已併入 `kimi_tracker_config.json`。
Agent 執行時只讀取 `.config/kimi_tracker_config.json`，不讀取任何其他配置檔案。
