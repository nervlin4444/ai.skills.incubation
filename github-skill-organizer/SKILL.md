---
title: "GitHub Skill Organizer Execution Guide"
name: github-skill-organizer
description: "LLM 执行指令。管理技能包的本地目录结构、版本控制、GitHub 同步。v1.2.0 合并重构：sync_engine 拆分为 skill_uploader + skill_syncer，引入 core_* 共用模块，排除规则集中至 sync.config.json；新增 repo_issue_finder + issue_extractor 双脚本交叉检查管道。"
version: v1.2.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-24T20:14:00+08:00
fixes: []
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: .env
file_mapping:
  local_path: SKILL.md
  github_path: github-skill-organizer/SKILL.md
---

# github-skill-organizer v1.2.0 -- LLM 执行指令

> 本文件是 LLM 执行指令，不是人类说明书。
> LLM 读取后必须严格执行，禁止自由发挥。

---

## 身份分流

### 若你是 Sub-Agent (L1 / L2 / L3)
本文件与你无关。停止。关闭。执行你的任务。

### 若你是 Main Agent (L0)
继续。你是协调者，负责技能包的上传、下载、比较、安装、Issue 交叉检查。

---

## 核心架构 (v1.2.0)

### 目录结构

    github-skill-organizer/
    |-- SKILL.md                    # 本文件 (LLM 指令)
    |-- README.md                   # 人类阅读指南
    |-- CHANGELOG.md                # 版本变更记录
    |-- config/
    |   |-- sync.config.json        # 统一配置源 (身份+排除规则+错误码)
    |-- scripts/
    |   |-- core_*.py               # 5 个共用模块 (禁止跨目录引用)
    |   |-- skill_uploader.py       # 上传 (compare -> classify -> upload)
    |   |-- skill_syncer.py         # 同步 (download / compare / sync_changelog)
    |   |-- file_scouter.py         # 扫描 Downloads 识别文件身份
    |   |-- repo_skill_finder.py    # 远程发现 GitHub 仓库中的技能
    |   |-- repo_skill_validator.py # 验证声称的仓库是否存在
    |   |-- repo_skill_migrator.py  # 批量迁移 github_repository 字段
    |   |-- repo_issue_finder.py    # F001: 下载 GitHub Issues (v1.2.0)
    |   |-- issue_extractor.py      # F002-F006: 本地 fixes 交叉检查 (v1.2.0)
    |   |-- change_classifier.py    # 变更分类器 (未改名)
    |   |-- skill_installer.py      # 文件搬运工 (未改名)
    |   |-- scheduler_daemon.py     # 调度守护进程 (v1.2.0 修复引用)
    |   |-- daemon_health_check.py  # 健康检查 (v1.2.0 修复引用)
    |   |-- skill_issue_reporter.py # Issue 报告 (未改名)
    |   |-- invalid_file_notifier.py # 无效文件通知 (未改名)
    |   |-- ... (其余未改名脚本)
    |-- scripts/USAGE.md            # 人类教程

### 关键变更历史

| 版本 | 变更 |
|------|------|
| v1.0.15 | sync_engine 单体脚本 |
| v1.1.1 | 重构：拆分为 skill_uploader + skill_syncer，引入 core_* 模块，配置合并入 sync.config.json |
| v1.2.0 | 新增：repo_issue_finder (F001) + issue_extractor (F002-F006) 双脚本交叉检查管道；修复 daemon 引用 |

---

## 执行流程

### 流程 A: 上传技能到 GitHub

    Step 1: skill_syncer.compare_skill(skill_name) -> comparison dict
    Step 2: change_classifier.classify_change(comparison) -> classification dict
    Step 3: skill_uploader.upload_skill(skill_name, files=None, classification=None)
            # files=None 自动扫描
            # classification=None 自动补全 (内置 compare + classify)
    Step 4: 检查返回 dict["status"] == "uploaded"

### 流程 B: 从 GitHub 下载技能

    Step 1: skill_syncer.compare_skill(skill_name)
    Step 2: 若 action == "github_ahead" 或 "diverged":
            skill_syncer.download_from_github(owner, repo, local_dir)

### 流程 C: 扫描 Downloads 安装技能

    Step 1: file_scouter.scan_and_report() -> report
    Step 2: skill_installer.install_skill(file_path) -> 搬运到 skills/

### 流程 D: Issues 交叉检查 (v1.2.0 新增)

    Step 1: repo_issue_finder.find_issues(state="all") -> issues list
    Step 2: issue_extractor.run(issues) -> crosscheck report
    Step 3: 检查 report["fixes_analysis"]["stale_fixes"] -> 上报主人确认清理
    Step 4: 检查 report["fixes_analysis"]["orphan_issues"] -> 建议添加 fixes 字段

---

## 绝对禁令 (LOCK 规则)

| 禁令 | 违反后果 |
|------|---------|
| 禁止直接 open()/write_text() 写入 .md/.py/.json/.html | 文件无 frontmatter (身份证)，上传时被标记非法 |
| 禁止调用旧名称脚本 (sync_engine / local_scanner / repo_inventory / repo_validator / repo_migrator) | 使用过时逻辑，重复 v1.0.4-1.0.15 的 bug |
| 禁止修改 sync.config.json 中的 github_repository / target_branch | 全局配置，需上报主人决策 |
| 禁止创建 config.json (独立配置源) | 配置分裂，Agent 可能读取错误 |
| 禁止将 core_*.py 放入子目录或跨目录引用 | Python import 失败 (点号分隔被解析为包路径) |
| 禁止在 .py 文件中使用中文注释/全角标点 (LOCK-016) | Windows cp950 vs Linux UTF-8 编码不一致 |
| 禁止基于交叉检查结果自动修改 fixes 字段或关闭 Issue (LOCK-011) | 未经授权修改，必须上报主人确认 |

---

## Core 模块引用规范

所有脚本必须位于 scripts/ 同一层，import 模式统一:

    try:
        from skill_organizer_config import load_config
        from core_exclude_engine import ExcludeEngine
        from core_frontmatter import FrontmatterExtractor
        from core_path_utils import normalize_path
        from core_logger import log
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.absolute()))
        from skill_organizer_config import load_config
        from core_exclude_engine import ExcludeEngine
        from core_frontmatter import FrontmatterExtractor
        from core_path_utils import normalize_path
        from core_logger import log

---

## 错误码对照 (Agent 自修复)

| 错误码 | 触发条件 | Agent 修复动作 |
|--------|---------|--------------|
| PARAM_MISSING_SKILL_NAME | skill_name 为空 | 补传 skill_name |
| PARAM_INVALID_FILES | 文件路径不存在 | 传 files=None 自动扫描 |
| CLASSIFICATION_INCOMPLETE | classification 缺字段 | 传 compare_skill 返回值，自动补全 |
| EXCLUDE_ALL_FILES | 全部文件被排除 | 检查 sync.config.json global_excludes.prefixes 是否含 "." |
| CLI_NOT_FOUND | github_repo_sync.py 未找到 | 安装 github-restful-api-connector 依赖技能 |
| GITHUB_AUTH_FAIL | Token 无效 | 更新 GITHUB_TOKEN |
| CLEAN_DIR_EMPTY | 清理后目录为空 | 确认 skill_uploader profile 的 base_path_boundary=true |
| FRONTMATTER_MISSING | 文件缺少 frontmatter | 使用 skill_files_designer 重新生成 |

---

## 接口隔离 (核心原则)

所有 github.com API 调用必须通过 github-restful-api-connector 的 rest_request() 统一接口。
本地文件管理由 github-skill-organizer 处理。
远程上传由 connector 处理。
禁止任何技能脚本直接使用 urllib.request 或 requests 访问 GitHub API。

---

## 版本锁定

LOCK v1.2.0 PERMANENT -- 目录结构、脚本命名、core 模块位置、接口隔离、配置单一源、.py 强制 ASCII、Issue 交叉检查管道。

*本文件是 LLM 执行指令，不是人类说明书。*
