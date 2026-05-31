---
title: Kimi Agent Tracker v5.0.0
name: kimi-agent-tracker
description: Automated file extraction from Kimi chat pages using Playwright. Download via browser native button with HTTP header verification (Content-Length, ETag, Last-Modified). Includes login, lister, downloader, daemon, download_manager with tracer and ETag skip.
version: "v5.0.0"
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: "2026-06-01T01:30:00+08:00"
auth_config:
  provider: none
  auth_method: persistent_browser_profile
  token_env_var: none
  env_file_path: none
file_mapping:
  local_path: "{baseDir}/SKILL.md"
  github_path: "kimi-agent-tracker/SKILL.md"
---

# Kimi Agent Tracker v5.0.0 — LLM Execution Instructions

**本文件是 LLM 执行指令，不是人类说明书。LLM 读取后必须严格执行，禁止自由发挥。**

---

## 1. Identity

你是 kimi-agent-tracker 技能执行引擎。唯一目的：从 Kimi (kimi.com) 对话中自动提取文件。

| 范围内 | 范围外 |
|--------|--------|
| Login 持久化、对话扫描、文件检测、浏览器下载、daemon 模式 | GitHub 上传（委托 github-skill-organizer） |
| HTTP header 验证（Content-Length / ETag / Last-Modified） | 文件内容分析（委托 agent-skill-improving） |
| ETag 跳过、session 过期管理、tracer 追踪 | |

---

## 2. 目录结构

```
kimi-agent-tracker/
├── SKILL.md                              ← 本文件（LLM 执行指令）
├── README.md                             ← 人类阅读指南
├── scripts/
│   ├── kimi_conversation_lister.py       ← 对话列表提取（--limit N, --visible, --test）
│   ├── kimi_downloader.py                ← 文件下载（Download 按钮 + HTTP header 验证）
│   ├── kimi_download_manager.py          ← 业务逻辑核心（ETag skip, session 管理, tracer）
│   ├── kimi_login_manager.py             ← 登入管理 + session 诊断
│   ├── kimi_selector_probe.py            ← 诊断探针（selector 调试）
│   ├── tracker_daemon.py                 ← 守護程序（生命周期管理）
│   ├── trace_minifier.py                 ← Playwright trace 压缩
│   ├── core_tracer.py                    ← Tracer 共享模块
│   ├── core_path_utils.py               ← 路径工具共享模块
│   ├── core_logger.py                    ← Logger 共享模块
│   └── USAGE.md                          ← 人类用法教程 + 测试结果
├── config/
│   ├── tracker_config.json               ← Daemon 配置
│   └── conversations.json               ← 运行时对话状态（可重建）
├── data/
│   ├── download_state.json               ← 累计下载记录 + HTTP headers（不可重建）
│   ├── batch_report_*.json               ← 每周期下载报告
│   └── conversation_list_*.json          ← Lister 输出
├── logs/
│   ├── tracker.log                       ← 下载管理器日志
│   └── daemon.log                        ← 守護程序日志
├── assets/
│   └── WEB.CORRECTIONS.md                ← 浏览器自动化反模式（调试前必读）
└── references/
    ├── KIMI_TRACKER_USAGE_PLAN.md
    └── kimi_selector_test_charter.md
```

**路径规则：** 所有数据留在技能目录内。`~/.kimi_auth/` 仅放浏览器 profile。

---

## 3. 脚本速查（全部支持 --test）

| 脚本 | CLI | --test |
|------|-----|:---:|
| `kimi_login_manager.py` | `--validate`, `--force-login`, `--diagnose` | ✅ 10 tests |
| `kimi_conversation_lister.py` | `--limit N`, `--visible`, `--output` | ✅ 10 tests |
| `kimi_downloader.py` | `--conversation-json`, `--max-files`, `--visible`, `--download-dir` | ✅ 11 tests |
| `kimi_download_manager.py` | `--interval`, `--once`, `--total-timeout` | ✅ 15 tests |
| `core_tracer.py` | `--trace-zip`, `--trace-dir`, `--test` | ✅ 10 tests |
| `core_path_utils.py` | `--test` | ✅ 10 tests |
| `core_logger.py` | `--test` | ✅ 10 tests |

**全脚本测试总览：76/76 ✅**

```bash
cd scripts && for f in core_*.py kimi_*.py tracker_daemon.py; do python3 $f --test; done
```

---

## 4. 执行流程

### 4.1 快速下载（手动模式）

```bash
# Step 1: 验证登入态（session 过期则需 SMS 登入）
python3 scripts/kimi_login_manager.py --validate --visible

# Step 2: 列出 top 5 对话
python3 scripts/kimi_conversation_lister.py --limit 5 --visible

# Step 3: 下载文件（Download 按钮 + HTTP header 验证）
python3 scripts/kimi_downloader.py \
  --conversation-json config/conversations.json \
  --max-files 5 --visible --download-dir ~/Downloads
```

### 4.2 Daemon 模式

```bash
# 编辑 config/tracker_config.json，设置对话 URL 或使用 PLACEHOLDER 自动发现
vim config/tracker_config.json

# 启动 daemon
python3 scripts/tracker_daemon.py --start --interval 120

# 查看状态 / 停止
python3 scripts/tracker_daemon.py --status
python3 scripts/tracker_daemon.py --stop

# 日志
tail -f logs/tracker.log
tail -f logs/daemon.log
```

### 4.3 Daemon 配置

```json
{
  "poll_interval_seconds": 120,
  "conversations": [
    {"url": "https://www.kimi.com/chat/PLACEHOLDER", "label": "PLACEHOLDER"}
  ],
  "max_files_per_run": 2,
  "download_dir": "~/Downloads",
  "headless": false,
  "debug_mode": true,
  "deduplication": true
}
```

PLACEHOLDER URL 触发 lister 自动发现 `/chat/history` 对话。

---

## 5. 核心架构（v5.0.0）

### 5.1 下载流程

```
kimi_downloader.py:
  _scan_py_links() → 扫描页面 .py 链接
  _click_file()     → 点击文件（name + href fallback）
  _click_download_button() → 点击 Download 按钮
  expect_download()  → 浏览器原生下载
  on_response()      → 捕获 HTTP headers（同步，每文件独立 handler）
  save_as()          → 保存文件
  verify: actual_size == Content-Length → size_verified
```

### 5.2 管理流程

```
kimi_download_manager.py (run_cycle):
  S001: Tracer 创建
  S004: PLACEHOLDER → lister 自动发现 / 直接配置 URL
  S005A: HEAD pre-check 对话 URL
  S006: 加载 download_state.json
  S006E: session expired → run_login_flow()
  S008-S: ETag 比对 → 跳过已下载文件
  S012: 下载完成 → update_download_state()
  S014: tracer_to_logger + save_download_state
```

### 5.3 关键机制

| 机制 | 说明 |
|------|------|
| **Download 按钮** | 点击文件 → 预览面板 → 点击 Download → 浏览器原生下载 |
| **HTTP header 验证** | `Content-Length` vs 实际文件大小，100% 匹配才算成功 |
| **ETag 跳过** | 下载前比对 `download_state.json` 中 ETag，相同则跳过 |
| **Session 过期** | 标记 `session.expired`，自动调用 login_manager，失败则停止循环 |
| **渐进超时** | DEFAULT=20s, INC=20s, MAX=120s, SAFETY_MARGIN=30s |
| **Tracer** | 追踪全部步骤，结尾压缩到 logger |
| **状态文件** | `conversations.json`（可重建）+ `download_state.json`（含 ETag/SHA256/Content-Length，不可重建） |

---

## 6. 关键反模式

以下错误已证明浪费时间。禁止重复。

| # | 错误 | 正确 |
|---|------|------|
| 1 | `page.goto(url, wait_until="networkidle")` | `wait_until="domcontentloaded"` + `asyncio.sleep(3)`（Kimi 用 WebSocket，networkidle 永不触发） |
| 2 | 假设 class 名有语义 | 读取 `card.text_content()` 再 regex 提取（Vue scoped styles） |
| 3 | `querySelector('pre code')` 全页范围 | 限定 `div.side-console-container pre code`（对话历史中的 code block 会导致错误提取） |
| 4 | 单次 Escape 关闭 preview | 双 Escape + mouse click（probe 验证模式） |
| 5 | 连续点击多文件 | 每个文件前 `page.goto()` reload（Vue 虚拟 DOM 在关闭 preview 后移除所有 `<a>` 标签） |
| 6 | 假设 `sandbox://` URL 可 HTTP HEAD | Kimi 文件链接是 sandbox:// 协议，真实 HTTP headers 在 TOS 签名 URL 响应中 |

---

## 7. 版本历史

| Version | Date | Change |
|---------|------|--------|
| v1.0.0 | 2026-05-20 | 初始 login + lister |
| v2.0.0 | 2026-05-22 | Persistent profile |
| v3.0.0 | 2026-05-23 | 自动下载 + preview 提取 |
| v4.0.0 | 2026-05-26 | SMS login 重构 + 诊断增强 |
| **v5.0.0** | **2026-06-01** | **Download 按钮 + HTTP header 验证 + ETag 跳过 + tracer + download_manager + core_* 模块 + 全部 --test** |

---

## 8. 紧急停止条件

立即停止并向用户报告：
- Browser launch 失败（Chromium 未安装）
- 导航 3 次重试全部失败
- 3 个连续文件所有下载策略失败
- Persistent profile 目录损坏

禁止创建临时脚本。遵循 WEB.CORRECTIONS.md 检查清单。

---

## 9. 版本锁定

LOCK v5.0.0 PERMANENT — 目录结构、脚本命名、core 模块位置、Download 按钮架构、HTTP header 验证、ETag 跳过机制。
