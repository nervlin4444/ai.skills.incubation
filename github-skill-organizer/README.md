---
title: "GitHub Skill Organizer - Project README"
name: github-skill-organizer
description: "Project overview for github-skill-organizer. Automated skill repository management for AI agents. v1.2.0."
version: "1.2.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-28T00:54:00+08:00"
fixes: []
auth_config:
  provider: github
  auth_method: delegated
  connector_skill: github-restful-api-connector
  connector_module: github_restful_core
file_mapping:
  local_path: "README.md"
  github_path: "github-skill-organizer/README.md"
---

# GitHub Skill Organizer

管理 AI 技能包的本地目录结构、版本控制与 GitHub 同步。

## 版本

v1.2.1 (2026-05-28)

## 核心功能

- **skill_uploader**: 上传技能到 GitHub (自动分类、参数标准化、base_path 边界排除)
- **skill_syncer**: 从 GitHub 下载/比较技能
- **file_scouter**: 扫描 Downloads 文件夹，识别文件身份
- **repo_skill_finder**: 发现 GitHub 仓库中的技能包
- **repo_skill_validator**: 验证声称的仓库是否真实存在
- **repo_skill_migrator**: 批量迁移 github_repository 字段
- **repo_issue_finder** (v1.2.0): 下载 GitHub Issues，支持过滤与分页
- **issue_extractor** (v1.2.0): 交叉检查本地 fixes 字段与 GitHub Issue 状态

## 快速开始

1. 配置 `.env` 文件
2. 确保 `github-restful-api-connector` 依赖技能已安装
3. 运行测试: `python3 scripts/test_imports_and_paths.py`

## 目录结构

```
github-skill-organizer/
|-- config/
|   |-- sync.config.json          # 统一配置 (排除规则 + 错误码 + 工作站默认)
|-- scripts/
|   |-- core_*.py                 # 5 个共用模块
|   |-- skill_uploader.py         # 上传
|   |-- skill_syncer.py           # 下载/比较
|   |-- file_scouter.py           # 扫描
|   |-- repo_skill_*.py           # 仓库相关
|   |-- repo_issue_finder.py      # Issue 下载 (v1.2.0)
|   |-- issue_extractor.py        # Fixes 交叉检查 (v1.2.0)
|   |-- ... (其余工具脚本)
|-- SKILL.md                      # LLM 执行指令
|-- README.md                     # 本文件
|-- USAGE.md                      # 详细使用教程
```

## 关键修复与新增

### v1.2.1 (2026-05-28)
- **新增 repo_issue_finder + issue_extractor**: 双脚本 Issue 交叉检查管道
- **新增 Agent Testing Protocol**: 上传前必须运行交叉检查
- **修复 scheduler_daemon**: 适配 v1.1.1 重构后的脚本名称
- **修复 daemon_health_check**: 适配 file_scouter 新名称

### v1.1.1 (2026-05-24)
- **.workbuddy 误杀修复**: 排除规则移除 `.` 前缀，增加 base_path 边界检查
- **配置合并**: config.json 合并入 sync.config.json，单一配置源
- **脚本拆分**: sync_engine 拆分为 skill_uploader + skill_syncer，职责清晰
- **Core 模块**: 提取 5 个共用模块，消除重复代码

## 许可证

MIT
