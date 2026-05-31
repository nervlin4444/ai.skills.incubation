---
title: Kimi Agent Tracker v5.0.0 — Project Overview
name: kimi-agent-tracker
description: Playwright-based automation suite for Kimi AI platform. Downloads files via browser native Download button with HTTP header verification (Content-Length, ETag, Last-Modified). Daemon mode with ETag skip and tracer tracking.
version: "v5.0.0"
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: "2026-06-01T01:35:00+08:00"
fixes: []
auth_config:
  provider: none
  auth_method: persistent_browser_profile
  token_env_var: none
  env_file_path: none
file_mapping:
  local_path: "{baseDir}/README.md"
  github_path: "kimi-agent-tracker/README.md"
---

# Kimi Agent Tracker v5.0.0

Playwright-based automation suite for the Kimi AI platform. Downloads `.py` files from chat conversations via browser native Download button with **HTTP header verification** — Content-Length, ETag, and Last-Modified are compared against actual file sizes before a download is marked successful.

---

## Architecture (Pseudo Code)

```
┌─ tracker_daemon.py ──────────────────────────────────────────────┐
│  PID 管理 + 循环触发器。所有业务委托给 kimi_download_manager.py    │
│  for each cycle:                                                  │
│    _run_download_manager(interval) → subprocess DM                │
│    sleep(interval - elapsed)                                      │
└───────────────────────────────────────────────────────────────────┘
        │ subprocess
        ▼
┌─ kimi_download_manager.py (run_cycle) ───────────────────────────┐
│                                                                   │
│  S001  Tracer("download_manager") 创建                            │
│  S002  load_tracker_config() → 读取 config/tracker_config.json    │
│  S003  检查 conversations 配置                                    │
│  S004  PLACEHOLDER? → run_lister() 自动发现 / 直接使用配置 URL    │
│  S005  save_conversations_json() → config/conversations.json      │
│  S005A head_pre_check(url) → Phase A: HEAD 验证对话 URL 可达      │
│  S006  load_download_state() → 读取 data/download_state.json      │
│  S006E is_session_expired? → run_login_flow() → 失败则返回        │
│  S007  设置 visible / headless                                    │
│                                                                   │
│  for each conversation:                                           │
│    S008-S  check_etag_match() → 所有文件 ETag 匹配? → skip        │
│    S010    run_downloader(conversation_json, max_files, visible)   │
│              │ subprocess                                          │
│              ▼                                                    │
│    ┌─ kimi_downloader.py ────────────────────────────────────┐   │
│    │  run_batch(conversation_json, max_files, limit_chats)    │   │
│    │    for each chat:                                        │   │
│    │      _process_chat():                                    │   │
│    │        1. page.goto(url, "domcontentloaded")             │   │
│    │        2. _scan_py_links(page) → List[Dict]              │   │
│    │        3. for each .py file (max N):                     │   │
│    │           if idx > 0: page.goto(reload)  ← DOM 恢复      │   │
│    │           _download_file(page, finfo, response_headers): │   │
│    │             a. _click_file() → 点击文件                   │   │
│    │             b. _click_download_button() → 点击 Download   │   │
│    │             c. page.expect_download() → 捕获下载           │   │
│    │             d. on("response") → 捕获 HTTP headers        │   │
│    │                  (Content-Length / ETag / Last-Modified) │   │
│    │             e. download.save_as(path)                    │   │
│    │             f. actual_size == Content-Length?            │   │
│    │                  ✅ success + size_verified               │   │
│    │                  ❌ size_mismatch                         │   │
│    │             g. _close_preview() → 双 Escape + click       │   │
│    └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│    S012  update_download_state(state, url, title, results)        │
│          → 写入 ETag / SHA256 / Content-Length / file_path        │
│                                                                   │
│  S013  cycle 完成统计                                              │
│  S014  save_download_state() + tracer_to_logger(tracer, log)      │
└───────────────────────────────────────────────────────────────────┘
```

---

## 文件清单

### 核心脚本（7 个）

| 文件 | 大小 | 用途 |
|------|------|------|
| `kimi_download_manager.py` | 30KB | **业务逻辑核心** — 循环管理、ETag 跳过、session 过期、状态写入、tracer 集成 |
| `kimi_downloader.py` | 33KB | **文件下载** — Download 按钮 + HTTP header 验证、多文件 reload 恢复 DOM |
| `kimi_conversation_lister.py` | 16KB | **对话列表** — 自动发现 `/chat/history`、滚动懒加载、6 selector 匹配 |
| `kimi_login_manager.py` | 16KB | **登入管理** — SMS 登入、session 验证、诊断页截图 |
| `tracker_daemon.py` | 7KB | **守護程序** — PID 管理、fork 后台、循环触发器 |
| `kimi_selector_probe.py` | 44KB | **诊断探针** — 5 策略下载测试、深度 DOM 诊断、Monaco API 检测 |
| `trace_minifier.py` | 10KB | **Trace 压缩** — 2MB trace.zip → 30KB summary JSON |

### 公用模块（3 个）

| 文件 | 用途 |
|------|------|
| `core_tracer.py` | **Tracer** — 事件记录、paired timing、export JSON、向后兼容 trace_minifier |
| `core_path_utils.py` | **路径工具** — 统一 skill 路径解析、`{baseDir}` 模板、目录创建 |
| `core_logger.py` | **Logger** — 结构化日志（INFO/WARN/ERROR/STEP/METRIC）、文件写入 |

### 配置文件

| 文件 | 用途 |
|------|------|
| `config/tracker_config.json` | Daemon 配置（poll interval / conversations / download_dir） |
| `config/conversations.json` | 运行时对话列表（Lister 输出，可重建） |
| `data/download_state.json` | 累计下载记录 + HTTP headers（ETag/SHA256/Content-Length，不可重建） |
| `data/batch_report_*.json` | 每周期下载报告 |

---

## 每个函数用途说明

### kimi_download_manager.py（15 tests / 15 passed）

| 函数 | 用途 |
|------|------|
| `load_tracker_config()` | 读取 `config/tracker_config.json` |
| `save_conversations_json(list)` | 保存对话列表到 `config/conversations.json` |
| `load_conversations_json()` | 读取对话列表 |
| `load_download_state()` | 读取 `data/download_state.json` |
| `save_download_state(dict)` | 保存下载状态 |
| `compute_sha256(path)` | 计算文件 SHA256（从 state_manager 合并） |
| `check_etag_match(state, filename, etag)` | 检查同名文件 ETag 是否已记录 |
| `update_download_state(state, url, title, results)` | 将 batch_report 结果写入 state，含 ETag/SHA256/Content-Length/file_path |
| `get_session_state(state)` | 获取 session 子状态 |
| `mark_session_expired(state, reason)` | 标记 session 过期 |
| `is_session_expired(state)` | 检查 session 是否过期 |
| `clear_session_expired(state)` | 清除过期标记 |
| `tracer_to_logger(tracer, log)` | 将 Tracer 事件压缩写入 Logger（`[TRACER]` 前缀） |
| `run_lister(auto_discover, target_url)` | 子进程启动 lister 或直接返回配置 URL |
| `run_downloader(json, max_files, visible, dir)` | 子进程启动 downloader，读取 batch_report |
| `run_login_flow(log, state)` | 子进程启动 login_manager，验证登入态 |
| `head_pre_check(url)` | HTTP HEAD 验证对话 URL 可达（含 SSL 旁路） |
| `step(log, id, msg) / metric(log, k, v)` | 结构化日志和指标记录 |
| `run_cycle(log, poll_interval)` | **主循环** — S001-S014 完整流程 |

### kimi_downloader.py（11 tests / 11 passed）

| 函数 | 用途 |
|------|------|
| `__init__(profile_dir, headless, download_dir, tracer)` | 初始化下载器，CORE_AVAILABLE=False 时 sys.exit |
| `_trace(event, **data)` | 向 Tracer 记录事件（支持对象 .record() / callable / 异常安全） |
| `_is_cached(fname)` | 检查文件是否已在 download_dir 中 |
| `_scan_py_links(page)` | 扫描页面 `<a>` 标签，提取 `.py` 文件（去重、长度检查） |
| `_click_file(page, finfo)` | 点击文件链接（name 匹配 + href fallback） |
| `_click_download_button(page)` | 点击 preview 面板中的 Download 按钮 |
| `_scroll_preview_to_load_full(page)` | 滚动 preview 面板触发懒加载（限定 `side-console-container` 范围） |
| `_extract_full_content(page)` | 从 preview 面板提取 `pre code` 内容（限定面板范围） |
| `_close_preview(page)` | 关闭 preview 面板（双 Escape + mouse click 探针验证模式） |
| `_download_file(page, finfo)` | **核心下载** — click → Download 按钮 → expect_download → HTTP header 捕获 → size 验证 |
| `_process_chat(page, chat, max_files)` | 处理单个对话 — reload → scan → 逐个下载 |
| `run_batch(json, max_files, limit_chats)` | 批量入口 — 启动浏览器 → 遍历对话 → 生成 batch_report |

### kimi_conversation_lister.py（10 tests / 10 passed）

| 函数 | 用途 |
|------|------|
| `__init__(profile_dir, headless, tracer)` | 初始化 lister，含 `_stats` 统计 |
| `_trace(event, **data)` | Tracer 事件记录 |
| `report_to_manager()` | 返回 `{chats_found, chats_valid, chats_invalid, total_elapsed}` |
| `extract_conversations(limit)` | 导航 `/chat/history` → 滚动懒加载 → 6 selector 匹配 → 提取对话 |
| `save_results(conversations, filename)` | 保存到 `data/conversation_list_*.json` |

### kimi_login_manager.py（10 tests / 10 passed）

| 函数 | 用途 |
|------|------|
| `_load_config()` | 加载 tracker_config.json，合并默认值 |
| `_resolve_path(tpl)` | 解析 `{baseDir}` 路径模板 |
| `_check_login_success(page, verbose)` | 复合判断：`.chat-info-item` / `.user-avatar` / `.user-name` |
| `validate_login(profile, visible)` | 快速验证登入态 |
| `login(profile, visible, stay_open, force_login)` | SMS 登入循环 |
| `diagnose_login_page(profile)` | 诊断登入页面（HTML dump + 截图） |

### core_tracer.py（10 tests / 10 passed）

| 函数 | 用途 |
|------|------|
| `Tracer.__init__(name)` | 创建 tracer |
| `Tracer.record(event, **data)` | 记录带时间戳的事件 |
| `Tracer.get_summary()` | 返回 `{total_events, unique_event_types, elapsed_total, paired_timings}` |
| `Tracer.get_timing(tag)` | 成对 timing `{tag}.start` / `{tag}.done` |
| `Tracer.export_json(path)` | 导出完整事件记录 |
| `Tracer.clear()` | 重置所有状态 |
| `DOMSummaryExtractor` | HTML trace 解析（向后兼容） |
| `minify_trace(zip)` | trace.zip → summary JSON |

### core_path_utils.py（10 tests / 10 passed）

| 函数 | 用途 |
|------|------|
| `get_skill_dir()` | 返回 `~/.workbuddy/skills/kimi-agent-tracker` |
| `get_config_dir()` / `get_data_dir()` / `get_logs_dir()` | 各子目录路径 |
| `get_tracker_config_path()` | `config/tracker_config.json` |
| `get_conversations_json_path()` | `config/conversations.json` |
| `get_download_state_path()` | `data/download_state.json` |
| `resolve_path(tpl)` | 解析 `{baseDir}` 和 `~/` 模板 |
| `ensure_dir(path)` | 确保目录存在 |

### core_logger.py（10 tests / 10 passed）

| 函数 | 用途 |
|------|------|
| `CoreLogger.__init__(log_file, component)` | 创建 logger（含文件/控制台双输出） |
| `info()` / `debug()` / `warn()` / `error()` / `fatal()` | 各级别日志 |
| `step(step_id, msg)` | `[STEP] [component] [S001] message` |
| `metric(name, value)` | `[METRIC] [component] name=value` |
| `get_default_logger(component)` | 默认 logger（log_dir/tracker.log） |

---

## 测试总览（76/76 ✅）

```bash
cd scripts
python3 core_tracer.py --test              # 10/10
python3 core_path_utils.py --test          # 10/10
python3 core_logger.py --test              # 10/10
python3 kimi_conversation_lister.py --test # 10/10
python3 kimi_downloader.py --test          # 11/11
python3 kimi_login_manager.py --test       # 10/10
python3 kimi_download_manager.py --test    # 15/15
```

---

## 状态文件体系

| 文件 | 属性 | 内容 |
|------|:---:|------|
| `config/conversations.json` | 可重建 | Lister 输出的对话列表 + finding 状态 |
| `data/download_state.json` | 不可重建 | 累计下载历史 + HTTP headers + SHA256 |
| `data/batch_report_*.json` | 每周期 | 下载报告（含 ETag / Content-Length / size_verified） |

### download_state.json 文件条目示例

```json
{
  "conversations": [{
    "url": "https://www.kimi.com/chat/...",
    "title": "auto-download-test",
    "files": [{
      "filename": "trace_minifier_v500.py",
      "status": "success",
      "sha256": "3dc7ab63...",
      "content_length": "10330",
      "etag": "\"1e437ddef1114a4bc51e21ce3fec8cb7\"",
      "last_modified": "Thu, 28 May 2026 02:33:17 GMT",
      "content_type": "text/x-python",
      "http_url": "https://prod-chat-kimi.tos-cn-beijing.volces.com/...",
      "file_path": "~/Downloads/trace_minifier_v500.py",
      "size_verified": true,
      "size": 10330,
      "downloaded_at": "2026-06-01T00:37:33"
    }]
  }],
  "session": {},
  "global_stats": {"total_downloaded": 2, "total_size_bytes": 22156}
}
```

---

## 版本历史

| Version | Date | Changes |
|---------|------|---------|
| v1.x | 2026-05-20~25 | 初始 login / lister / downloader / 5-strategy degradation |
| v2.0.0 | 2026-05-22 | Persistent profile |
| v3.0.0 | 2026-05-23 | Auto-download + preview extraction |
| v3.6.1 | 2026-05-26 | Daemon zero-config, file copy |
| v4.0.0 | 2026-05-26 | SMS login 重构 + selector 诊断 + WebSocket 反模式修复 |
| **v5.0.0** | **2026-06-01** | **重大重构：Download 按钮 + HTTP header 验证 + ETag 跳过 + tracer + download_manager + core_* 模块 + 全部 --test (76/76)** |

### v5.0.0 关键变更

| 变更 | 旧 (v4.x) | 新 (v5.0.0) |
|------|-----------|-------------|
| 下载方式 | Preview panel innerText 提取 | Download 按钮 → 浏览器原生下载 |
| 文件验证 | 无（直接保存） | Content-Length vs 实际大小，ETag 唯一性 |
| 多文件 | 连续 DOM 点击（文件 2/3 失败） | 每文件前 reload 页面恢复 DOM |
| Header 捕获 | 无 | 每文件独立 on("response") + finally 清理 |
| ETag 跳过 | 无 | check_etag_match → 秒级跳过已下载文件 |
| Session 管理 | 无 | expired → run_login_flow() → 失败则停止 |
| Tracer | 无 | 完整追踪 → 压缩到 Logger |
| State 文件 | downloads.json / pending.json | download_state.json（含 HTTP headers + SHA256） |
| 测试 | 无 | 全部脚本 --test，76/76 |

---

## 快速开始

```bash
# 1. 验证登入
python3 scripts/kimi_login_manager.py --validate --visible

# 2. 编辑配置（设置对话 URL 或使用 PLACEHOLDER 自动发现）
vim config/tracker_config.json

# 3. 启动 daemon（每 120s 循环）
python3 scripts/tracker_daemon.py --start --interval 120

# 4. 查看状态
python3 scripts/tracker_daemon.py --status

# 5. 查看日志
tail -f logs/tracker.log

# 6. 运行全部测试
cd scripts && for f in core_*.py kimi_*.py; do python3 $f --test; done
```

## Requirements

- Python 3.10+
- Playwright (`pip install playwright && playwright install chromium`)
- Persistent browser profile at `~/.kimi_auth/browser_profile_chromium/`
- Kimi 登入态（通过 login_manager 维护）

## License

MIT License — nervlin4444/ai.skills.incubation
