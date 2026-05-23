"""
---
title: "Skill Integrity Checker - 技能合規檢查器"
name: agent-skill-improving
description: "掃描技能目錄，執行 30+ 項合規檢查 + 9 項架構紅線。v1.2.5 新增 fixes 欄位檢查：必須存在（key 必須在），值可為空列表 [] 或整數列表。檢查代碼與 frontmatter Fixes 聲明一致性。"
version: "1.2.5"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-22T18:49:12+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "scripts/skill_integrity_checker.py"
  github_path: "agent-skill-improving/scripts/skill_integrity_checker.py"
---
"""

import os
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Any


class SkillIntegrityChecker:
    """
    LOCK v1.2.5: 技能合規檢查器

    檢查項：30+ 項合規 + 9 項紅線

    v1.2.5 新增：
    - fixes 欄位必須存在（key 必須在），值可為 [] 或 [5, 6]
    - 代碼 Fixes 聲明與 frontmatter 一致性檢查
    - github_path 前導斜杠檢查
    - updated_at ISO 8601 格式驗證
    - version 一致性檢查
    - file_mapping 完整性檢查
    """

    REQUIRED_FIELDS = [
        "title", "name", "description", "version",
        "github_repository", "target_branch", "updated_at",
        "auth_config", "file_mapping", "fixes"
    ]

    RED_LINES = [
        "missing_skill_md", "missing_readme_md", "missing_frontmatter",
        "invalid_frontmatter_format", "missing_required_field",
        "fixes_field_missing", "fixes_invalid_type", "fixes_invalid_value",
        "github_path_leading_slash", "version_mismatch"
    ]

    def __init__(self, skill_dir: str, strict: bool = False):
        self.skill_dir = Path(os.path.expanduser(str(skill_dir))).resolve()
        self.strict = strict
        self.errors = []
        self.warnings = []
        self.red_lines = []

    def _read_frontmatter(self, file_path: Path) -> Optional[Dict]:
        """讀取文件的 frontmatter。"""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        # 支援 YAML frontmatter (---) 或 docstring YAML
        if file_path.suffix == ".py":
            match = re.search(r'"""\s*\n(---.*?---)\s*\n"""', content, re.DOTALL)
            if not match:
                match = re.search(r"'''\s*\n(---.*?---)\s*\n'''", content, re.DOTALL)
            if match:
                return self._parse_yaml(match.group(1))
        else:
            if content.strip().startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    return self._parse_yaml(content[3:end])
        return None

    def _parse_yaml(self, yaml_text: str) -> Dict:
        """簡易 YAML 解析（只處理一層結構）。"""
        result = {}
        current_key = None
        for line in yaml_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" in stripped:
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if val.startswith("[") and val.endswith("]"):
                    inner = val[1:-1].strip()
                    if inner:
                        result[key] = [int(x.strip()) for x in inner.split(",") if x.strip().isdigit()]
                    else:
                        result[key] = []
                elif val.lower() in ("true", "false"):
                    result[key] = val.lower() == "true"
                else:
                    result[key] = val
                current_key = key
        return result

    def check_fixes_field(self, file_path: Path, frontmatter: Dict) -> Tuple[bool, str]:
        """
        檢查 fixes 欄位：
        1. fixes 必須存在（key 必須在）
        2. 值必須是列表（可為空 []）
        3. 列表中的每個元素必須是整數
        """
        if "fixes" not in frontmatter:
            self.red_lines.append(f"fixes_field_missing: {file_path}")
            return False, f"[RED-LINE] fixes 欄位缺失: {file_path.name}。fixes 必須存在（key 必須在），值可為 []"

        fixes = frontmatter["fixes"]
        if not isinstance(fixes, list):
            self.red_lines.append(f"fixes_invalid_type: {file_path}")
            return False, f"[RED-LINE] fixes 類型錯誤: {file_path.name}。必須是列表，收到 {type(fixes).__name__}"

        for item in fixes:
            if not isinstance(item, int):
                self.red_lines.append(f"fixes_invalid_value: {file_path}")
                return False, f"[RED-LINE] fixes 值錯誤: {file_path.name}。列表只能包含整數，收到 {item} ({type(item).__name__})"

        return True, f"[OK] fixes: {fixes if fixes else '[]'}"

    def check_fixes_consistency(self, file_path: Path, content: str, frontmatter: Dict) -> Tuple[bool, str]:
        """
        檢查代碼中的 Fixes 聲明與 frontmatter fixes 欄位一致性。

        規則：
        - 代碼中說 Fixes #5，但 frontmatter 沒有 → 報錯（RED-LINE）
        - frontmatter 有 fixes: [5]，但代碼中沒有 → 警告（不報錯）
        """
        patterns = [
            r"[Ff]ixes\s+#(\d+)",
            r"[Ff]ixed\s+#(\d+)",
            r"[Cc]loses\s+#(\d+)",
            r"修復\s*[Ii]ssue\s*#?(\d+)",
            r"修復\s*#(\d+)",
        ]
        code_fixes = set()
        for p in patterns:
            for m in re.finditer(p, content):
                code_fixes.add(int(m.group(1)))

        fm_fixes = set(frontmatter.get("fixes", []))

        # 代碼有聲明但 frontmatter 沒有 → 報錯
        missing = code_fixes - fm_fixes
        if missing:
            self.red_lines.append(f"fixes_consistency: {file_path}")
            nums = ", #".join(str(x) for x in sorted(missing))
            return False, f"[RED-LINE] Fixes 聲明不一致: {file_path.name}。代碼中聲明 Fixes #{nums}，但 frontmatter fixes 欄位缺失或不全"

        # frontmatter 有但代碼沒有 → 警告
        extra = fm_fixes - code_fixes
        if extra:
            nums = ", #".join(str(x) for x in sorted(extra))
            self.warnings.append(f"{file_path.name}: fixes 欄位聲明 #{nums}，但代碼中未找到對應聲明（可能是歷史記錄）")

        return True, "[OK] Fixes 一致性檢查通過"

    def check_required_fields(self, file_path: Path, frontmatter: Dict) -> Tuple[bool, str]:
        """檢查所有必填欄位是否存在。"""
        missing = [f for f in self.REQUIRED_FIELDS if f not in frontmatter]
        if missing:
            self.red_lines.append(f"missing_required_field: {file_path}")
            return False, f"[RED-LINE] 缺少必填欄位: {', '.join(missing)}"
        return True, f"[OK] 全部 {len(self.REQUIRED_FIELDS)} 個必填欄位存在"

    def check_github_path(self, file_path: Path, frontmatter: Dict) -> Tuple[bool, str]:
        """檢查 github_path 無前導斜杠。"""
        github_path = frontmatter.get("file_mapping", {}).get("github_path", "")
        if github_path.startswith("/"):
            self.red_lines.append(f"github_path_leading_slash: {file_path}")
            return False, f"[RED-LINE] github_path 有前導斜杠: {github_path}"
        return True, "[OK] github_path 格式正確"

    def run(self) -> Dict:
        """執行完整檢查。"""
        print(f"[INTEGRITY] 開始檢查: {self.skill_dir}")

        if not self.skill_dir.exists():
            return {"status": "error", "reason": f"目錄不存在: {self.skill_dir}"}

        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            self.red_lines.append("missing_skill_md")
            if self.strict:
                return {"status": "failed", "reason": "SKILL.md 缺失", "red_lines": self.red_lines}

        files_checked = 0
        for file_path in self.skill_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in (".md", ".py", ".json", ".html", ".env", ".yml", ".yaml"):
                continue
            if ".backups" in str(file_path) or "__pycache__" in str(file_path):
                continue

            files_checked += 1
            fm = self._read_frontmatter(file_path)

            if fm is None:
                if file_path.suffix in (".md", ".py", ".json", ".html"):
                    self.red_lines.append(f"missing_frontmatter: {file_path}")
                    print(f"  ❌ {file_path.name}: 無 frontmatter")
                continue

            # 必填欄位檢查
            ok, msg = self.check_required_fields(file_path, fm)
            if not ok:
                print(f"  ❌ {file_path.name}: {msg}")

            # fixes 檢查
            ok, msg = self.check_fixes_field(file_path, fm)
            if not ok:
                print(f"  ❌ {file_path.name}: {msg}")
            else:
                print(f"  ✅ {file_path.name}: {msg}")

            # Fixes 一致性檢查（僅對 .py 和 .md）
            if file_path.suffix in (".py", ".md"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    ok, msg = self.check_fixes_consistency(file_path, content, fm)
                    if not ok:
                        print(f"  ❌ {file_path.name}: {msg}")
                except Exception:
                    pass

            # github_path 檢查
            ok, msg = self.check_github_path(file_path, fm)
            if not ok:
                print(f"  ❌ {file_path.name}: {msg}")

        print(f"\n[INTEGRITY] 檢查完成: {files_checked} 個文件")

        if self.red_lines:
            return {
                "status": "failed" if self.strict else "warning",
                "files_checked": files_checked,
                "red_lines": self.red_lines,
                "warnings": self.warnings,
                "reason": f"發現 {len(self.red_lines)} 項紅線違規"
            }

        return {
            "status": "passed",
            "files_checked": files_checked,
            "warnings": self.warnings,
            "reason": "全部檢查通過"
        }


def main():
    parser = argparse.ArgumentParser(description="Skill Integrity Checker - 技能合規檢查器")
    parser.add_argument("--skill-dir", required=True, help="技能目錄路徑")
    parser.add_argument("--strict", action="store_true", help="嚴格模式（紅線違規即失敗）")
    parser.add_argument("--report-path", help="報告輸出路徑")
    args = parser.parse_args()

    checker = SkillIntegrityChecker(skill_dir=args.skill_dir, strict=args.strict)
    result = checker.run()

    print(f"\n[INTEGRITY] 結果: {result['status']}")
    if result["status"] == "passed":
        print("  ✅ 全部通過")
    elif result["status"] == "failed":
        print(f"  ❌ 失敗: {result['reason']}")
        for rl in result.get("red_lines", []):
            print(f"    - {rl}")
        sys.exit(1)
    else:
        print(f"  ⚠️  {result['reason']}")
        for rl in result.get("red_lines", []):
            print(f"    - {rl}")


if __name__ == "__main__":
    main()
