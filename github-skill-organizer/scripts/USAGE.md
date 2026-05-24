---
title: "GitHub Skill Organizer - Human Usage Guide"
name: github-skill-organizer
description: "Human-readable guide for using github-skill-organizer scripts. Covers installation, configuration, daily workflows, troubleshooting, and daemon management. v1.2.0 adds repo_issue_finder + issue_extractor pipeline."
version: "1.2.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-24T20:37:00+08:00"
fixes: []
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: "../.env"
file_mapping:
  local_path: "scripts/USAGE.md"
  github_path: "github-skill-organizer/scripts/USAGE.md"
---

# GitHub Skill Organizer -- 使用教程

## 环境配置

### 1. 安装依赖技能

确保 `github-restful-api-connector` 已安装:

```bash
# .env 中配置
DEPENDENCY_SKILL_PATH=~/.workbuddy/skills/github-restful-api-connector
```

### 2. 配置环境变量

创建 `github-skill-organizer/.env`:

```bash
USER_SKILLS_FOLDER=~/.workbuddy/skills
DEPENDENCY_SKILL_PATH=~/.workbuddy/skills/github-restful-api-connector
AGENT_NAME=your-agent
MODEL_NAME=your-model
```

## 测试验证

```bash
cd ~/.workbuddy/skills/github-skill-organizer/scripts
python3 test_imports_and_paths.py
```

预期全部 7 个测试通过。

## 各脚本使用说明

### skill_uploader.py -- 上传技能

```python
from skill_uploader import SkillUploader

uploader = SkillUploader()

# 方式 1: 全自动 (推荐)
result = uploader.upload_skill("github-skill-organizer")

# 方式 2: 指定文件
from pathlib import Path
files = [Path("SKILL.md"), Path("scripts/skill_uploader.py")]
result = uploader.upload_skill("github-skill-organizer", files=files)

# 方式 3: 预览模式
result = uploader.upload_skill("github-skill-organizer", dry_run=True)

# 返回结构
# {
#   "status": "uploaded" | "error" | "dry_run" | "pending_approval",
#   "error_code": "...",      # 错误时提供
#   "hint": "...",            # 修复建议
#   "fix_action": "...",      # 具体动作
#   "files_uploaded": [...]
# }
```

### skill_syncer.py -- 下载/比较技能

```python
from skill_syncer import SkillSyncer

syncer = SkillSyncer()

# 比较本地与远程
comparison = syncer.compare_skill("github-skill-organizer")
# 返回: action, modified_files, local_only_files, github_only_files

# 下载远程更新
syncer.download_from_github("nervlin4444", "ai.skills.incubation", local_dir)

# 同步 CHANGELOG
syncer.sync_changelog("github-skill-organizer")
```

### file_scouter.py -- 扫描 Downloads

```python
from file_scouter import FileScouter

scouter = FileScouter()
report = scouter.scan_and_report()

# 返回结构
# {
#   "total": 10,
#   "classified": 3,      # 有 frontmatter，可安装
#   "invalid": 2,         # 有 frontmatter 痕迹但解析失败
#   "unclassified": 5,    # 无 frontmatter
#   "summary": {
#     "ready_for_install": [...],
#     "needs_manual_review": [...],
#     "needs_classification": [...]
#   }
# }
```

### repo_issue_finder.py -- 下载 GitHub Issues (v1.2.0)

```bash
# 全量下载
python3 repo_issue_finder.py --state=all --output=/tmp/issues.json

# 按标签过滤
python3 repo_issue_finder.py --state=open --labels=bug,enhancement --output=/tmp/issues.json

# 按负责人过滤
python3 repo_issue_finder.py --assignee=nervlin4444 --output=/tmp/issues.json

# 按时间过滤
python3 repo_issue_finder.py --since=2026-05-01T00:00:00Z --output=/tmp/issues.json
```

### issue_extractor.py -- Fixes 交叉检查 (v1.2.0)

```bash
# 从文件分析 (推荐)
python3 issue_extractor.py --issues-file=/tmp/issues.json

# 查询特定技能
python3 issue_extractor.py --issues-file=/tmp/issues.json --skill-name github-skill-organizer

# 查询特定文件
python3 issue_extractor.py --issues-file=/tmp/issues.json --filename skill_uploader.py

# 查询特定函数
python3 issue_extractor.py --issues-file=/tmp/issues.json --function fetch_issues

# 自定义输出路径
python3 issue_extractor.py --issues-file=/tmp/issues.json --output ~/my-reports/extraction.json
```

### 一键管道 (v1.2.0)

```bash
# 下载 Issues + 交叉检查
python3 repo_issue_finder.py --state=all --output=/tmp/issues.json && python3 issue_extractor.py --issues-file=/tmp/issues.json --output=~/workbuddy/logs/extraction.json
```

## 配置说明 (sync.config.json)

### global_excludes -- 全局排除规则

```json
{
  "directories": [".backups", ".git", "__pycache__", ...],
  "files": ["LICENSE", "LICENSE.md"],
  "suffixes": [".pyc", ".pyo"],
  "prefixes": ["temp_", "tmp_"]
}
```

**注意**: `prefixes` 已移除 `.`，避免误杀 `.workbuddy` 等用户配置目录。

### script_profiles -- 脚本特定规则

| 脚本 | check_parents | base_path_boundary | 用途 |
|------|--------------|-------------------|------|
| skill_uploader | true | true | 防止父目录连坐排除 |
| skill_syncer | false | false | 下载时不需要边界 |
| file_scouter | false | false | 只检查文件本身 |
| repo_issue_finder | false | false | 纯数据获取，无本地文件操作 |
| issue_extractor | false | false | 纯本地分析，无 GitHub API 调用 |

### error_codes -- 错误码

Agent 收到错误时可根据 `error_code` 字段自修复:

- `PARAM_MISSING_SKILL_NAME`: 补传 skill_name
- `EXCLUDE_ALL_FILES`: 检查 global_excludes.prefixes 是否含 `.`
- `CLEAN_DIR_EMPTY`: 确认 base_path_boundary=true

## 故障排查

### Files uploaded: []

1. 检查 `sync.config.json` 中 `skill_uploader.base_path_boundary` 是否为 `true`
2. 检查 `global_excludes.prefixes` 是否包含 `.` (v1.1.1 已移除)
3. 检查 `skill_uploader.check_parents` 是否为 `true`

### No module named 'core_xxx'

确保所有 `core_*.py` 文件位于 `scripts/` 同一层目录，不在子目录中。

### 引号嵌套 SyntaxError

生成 .py 文件时采用分阶段组装策略：业务代码 -> frontmatter -> join 合并。
禁止在单一字符串块中同时包含外层 docstring 和内部示例代码。

### Issues 交叉检查异常类型

| 类型 | 含义 | 动作 |
|------|------|------|
| **Stale Fix** | Issue 已关闭但 frontmatter 仍引用 | 上报主人，确认后移除 fixes 字段 |
| **Pending Fix** | Issue 开放且正确引用 | 监控，无需动作 |
| **Orphan Issue** | Issue 存在但无本地文件引用 | 上报主人，建议添加 fixes 字段 |

## 守护进程管理

```bash
# 启动
python3 scripts/scheduler_daemon.py --start

# 停止
python3 scripts/scheduler_daemon.py --stop

# 状态
python3 scripts/scheduler_daemon.py --status

# 立即执行一次
python3 scripts/scheduler_daemon.py --sync-now

# 健康检查
python3 scripts/daemon_health_check.py
```
