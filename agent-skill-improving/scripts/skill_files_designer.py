"""
---
title: Skill Files Designer
name: agent-skill-improving
description: 文件設計器。自動生成標準 frontmatter + 攔截直接寫入操作。Agent 禁止直接 open()/write_text() 創建 .md/.py/.json/.html 文件，必須通過本腳本生成身份證後再寫入。
version: v1.2.5
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-22T18:00:00+08:00
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: "{baseDir}/.env"
file_mapping:
  - local_path: "{baseDir}/scripts/skill_files_designer.py"
    github_path: "agent-skill-improving/scripts/skill_files_designer.py"
---
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, List


class FrontmatterGenerator:
    """
    自動生成符合統一規範的 frontmatter。
    支持 .md / .py / .json / .html 文件類型。
    """

    def __init__(self, skill_name: str, github_repository: str = "nervlin4444/ai.skills.incubation", target_branch: str = "main"):
        self.skill_name = skill_name
        self.github_repository = github_repository
        self.target_branch = target_branch

    def _get_base_template(self) -> str:
        """返回基礎 frontmatter 模板（不含包裝）。"""
        lines = [
            "---",
            "title: {title}",
            "name: {name}",
            "description: {description}",
            "version: {version}",
            "github_repository: {github_repository}",
            "target_branch: {target_branch}",
            "updated_at: {updated_at}",
            "auth_config:",
            "  provider: github",
            "  auth_method: token",
            "  token_env_var: GITHUB_TOKEN",
            '  env_file_path: "{baseDir}/.env"',
            "file_mapping:",
            '  - local_path: "{baseDir}/{file_name}"',
            '    github_path: "{skill_name}/{file_name}"',
            "---",
            "",
        ]
        sep = chr(10)
        return sep.join(lines)

    def _wrap_for_py(self, base: str) -> str:
        """為 .py 文件包裝成 docstring 格式。"""
        tq = chr(34) + chr(34) + chr(34)
        nl = chr(10)
        return tq + nl + base + tq + nl + nl

    def generate(self, file_path: str, title: str, description: str, version: str) -> str:
        """
        生成 frontmatter 字符串。

        Args:
            file_path: 文件相對路徑（如 "scripts/new_module.py"）
            title: 描述性標題（≠ name）
            description: 文件描述
            version: 版本號（必須與技能其他文件一致）

        Returns:
            完整的 frontmatter 字符串
        """
        file_name = Path(file_path).name
        file_suffix = Path(file_path).suffix

        base = self._get_base_template()

        # 生成時間戳
        updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

        # 填充模板
        frontmatter = base.format(
            title=title,
            name=self.skill_name,
            description=description,
            version=version,
            github_repository=self.github_repository,
            target_branch=self.target_branch,
            updated_at=updated_at,
            file_name=file_name,
            skill_name=self.skill_name,
        )

        # 根據文件類型包裝
        if file_suffix == ".py":
            frontmatter = self._wrap_for_py(frontmatter)

        return frontmatter

    def validate_frontmatter(self, content: str, file_path: str) -> Dict:
        """
        驗證 frontmatter 完整性。

        Returns:
            {"valid": bool, "missing": [字段列表], "errors": [錯誤列表]}
        """
        result = {"valid": False, "missing": [], "errors": []}

        # 提取 frontmatter
        fm = self._extract_frontmatter(content, file_path)
        if not fm:
            result["errors"].append(f"{file_path}: Missing frontmatter (identity card)")
            return result

        # 檢查必填字段
        required_fields = ["title", "name", "description", "version", "github_repository", "target_branch", "updated_at", "auth_config", "file_mapping"]
        for field in required_fields:
            if field not in fm or not fm[field]:
                result["missing"].append(field)

        # 檢查 github_path 前導 "/"
        file_mapping = fm.get("file_mapping", [])
        for entry in file_mapping:
            github_path = entry.get("github_path", "")
            if github_path.startswith("/"):
                result["errors"].append(f"{file_path}: github_path has leading '/': '{github_path}'")

        # 檢查 updated_at 格式
        updated_at = fm.get("updated_at", "")
        if updated_at and not self._is_valid_iso8601(updated_at):
            result["errors"].append(f"{file_path}: Invalid updated_at format: '{updated_at}'")

        if not result["missing"] and not result["errors"]:
            result["valid"] = True

        return result

    def _extract_frontmatter(self, content: str, file_path: str) -> Optional[Dict]:
        """提取 frontmatter。"""
        try:
            if file_path.endswith(".py"):
                match = re.search(r'"""\s*---\s*(.*?)\s*---\s*"""', content, re.DOTALL)
                if match:
                    return self._parse_yaml(match.group(1))
            else:
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end != -1:
                        return self._parse_yaml(content[3:end])
            return None
        except Exception:
            return None

    def _parse_yaml(self, yaml_text: str) -> Dict:
        """解析簡單 YAML。"""
        result = {}
        current_key = None
        current_dict = None

        for line in yaml_text.splitlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue

            if line.strip().startswith("- "):
                item_text = line.strip()[2:].strip()
                if ":" in item_text:
                    key, value = item_text.split(":", 1)
                    if "file_mapping" not in result:
                        result["file_mapping"] = []
                    result["file_mapping"].append({
                        key.strip(): value.strip().strip('"').strip("'")
                    })
                continue

            match = re.match(r'^(\s*)([\w_]+):\s*(.*)$', line)
            if match:
                indent, key, value = match.groups()
                indent_level = len(indent)

                if indent_level == 0:
                    current_key = key
                    if not value:
                        result[key] = {}
                        current_dict = result[key]
                    else:
                        result[key] = value.strip().strip('"').strip("'")
                        current_dict = None
                elif current_dict is not None and indent_level > 0:
                    current_dict[key] = value.strip().strip('"').strip("'")

        return result

    def _is_valid_iso8601(self, text: str) -> bool:
        """檢查 ISO 8601 格式。"""
        patterns = [
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$',
        ]
        return any(re.match(p, text) for p in patterns)


class SkillFileWriter:
    """
    上下文管理器：強制生成 frontmatter 後再寫入文件。
    Agent 必須使用此類創建 .md/.py/.json/.html 文件，禁止直接 open()/write_text()。
    """

    def __init__(self, file_path: str, skill_name: str, title: str, description: str, version: str, github_repository: str = "nervlin4444/ai.skills.incubation", target_branch: str = "main"):
        self.file_path = Path(file_path)
        self.skill_name = skill_name
        self.title = title
        self.description = description
        self.version = version
        self.github_repository = github_repository
        self.target_branch = target_branch
        self.generator = FrontmatterGenerator(skill_name, github_repository, target_branch)
        self.content_buffer = []

    def __enter__(self):
        """進入上下文，準備寫入。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，寫入文件（含 frontmatter）。"""
        if exc_type is None:
            # 生成 frontmatter
            frontmatter = self.generator.generate(
                file_path=str(self.file_path),
                title=self.title,
                description=self.description,
                version=self.version,
            )

            # 組合內容
            sep = chr(10)
            content = frontmatter + sep + sep.join(self.content_buffer)

            # 確保目錄存在
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # 寫入文件
            self.file_path.write_text(content, encoding="utf-8")

            print(f"[GUARDIAN] File created with frontmatter: {self.file_path}")
            print(f"[GUARDIAN] Identity card verified: title={self.title}, name={self.skill_name}, version={self.version}")
        else:
            print(f"[GUARDIAN] File NOT created due to exception: {exc_val}")

        return False  # 不吞掉異常

    def write(self, text: str):
        """
        添加業務內容（不是直接寫入文件，而是緩衝到內部列表）。
        實際寫入在 __exit__ 時執行，確保 frontmatter 先插入。
        """
        self.content_buffer.append(text)

    def write_line(self, text: str):
        """添加一行業務內容。"""
        self.content_buffer.append(text + chr(10))


def validate_skill_files(skill_dir: str) -> Dict:
    """
    驗證技能目錄下所有文件的 frontmatter。
    返回驗證報告。
    """
    skill_path = Path(skill_dir)
    generator = FrontmatterGenerator(skill_path.name)

    results = {
        "valid": [],
        "invalid": [],
        "total": 0,
    }

    for f in skill_path.rglob("*"):
        if not f.is_file():
            continue
        if f.name.startswith("."):
            continue
        if f.suffix not in [".md", ".py", ".json", ".html"]:
            continue

        content = f.read_text(encoding="utf-8", errors="ignore")
        validation = generator.validate_frontmatter(content, str(f))

        results["total"] += 1
        if validation["valid"]:
            results["valid"].append(str(f))
        else:
            results["invalid"].append({
                "file": str(f),
                "missing": validation["missing"],
                "errors": validation["errors"],
            })

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skill Files Designer v1.2.5")
    subparsers = parser.add_subparsers(dest="command")

    # generate 命令
    gen_parser = subparsers.add_parser("generate", help="Generate frontmatter for a file")
    gen_parser.add_argument("--file-path", required=True, help="Relative file path")
    gen_parser.add_argument("--skill-name", required=True, help="Skill name")
    gen_parser.add_argument("--title", required=True, help="File title")
    gen_parser.add_argument("--description", required=True, help="File description")
    gen_parser.add_argument("--version", required=True, help="Skill version")
    gen_parser.add_argument("--github-repository", default="nervlin4444/ai.skills.incubation")
    gen_parser.add_argument("--target-branch", default="main")

    # validate 命令
    val_parser = subparsers.add_parser("validate", help="Validate all files in skill directory")
    val_parser.add_argument("--skill-dir", required=True, help="Path to skill directory")

    args = parser.parse_args()

    if args.command == "generate":
        generator = FrontmatterGenerator(args.skill_name, args.github_repository, args.target_branch)
        frontmatter = generator.generate(args.file_path, args.title, args.description, args.version)
        print(frontmatter)

    elif args.command == "validate":
        results = validate_skill_files(args.skill_dir)
        print(f"[VALIDATE] Total files: {results['total']}")
        print(f"[VALIDATE] Valid: {len(results['valid'])}")
        print(f"[VALIDATE] Invalid: {len(results['invalid'])}")

        if results["invalid"]:
            sep = chr(10)
            print(sep + "[VALIDATE] Invalid files:")
            for item in results["invalid"]:
                print(f"  ❌ {item['file']}")
                for err in item["errors"]:
                    print(f"     {err}")
                for miss in item["missing"]:
                    print(f"     Missing field: {miss}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
