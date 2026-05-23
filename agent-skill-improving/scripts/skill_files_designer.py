"""
---
title: "Skill Files Designer - 技能文件設計器"
name: agent-skill-improving
description: "生成標準 frontmatter，攔截直接寫入操作，自動檢測 Fixes 聲明並寫入 frontmatter。所有技能文件必須通過此腳本生成，禁止直接 open()/write_text()。v1.2.5 新增 fixes 欄位：必須存在，可為空列表 []，表示無關聯 Issue。"
version: "1.2.5"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-22T18:46:26+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "scripts/skill_files_designer.py"
  github_path: "agent-skill-improving/scripts/skill_files_designer.py"
---
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any

class SkillFileWriter:
    """
    LOCK v1.2.5: 技能文件設計器（上下文管理器）
    
    核心機制：
    1. Agent 禁止直接 open()/write_text() 創建 .md/.py/.json/.html
    2. 必須通過 SkillFileWriter 生成 frontmatter 後再寫入業務內容
    3. 自動檢測代碼中的 Fixes 聲明並寫入 frontmatter fixes 欄位
    4. fixes 欄位必須存在（key 必須在），值可為空列表 []
    
    使用範例：
    with SkillFileWriter(
        file_path="scripts/new_module.py",
        skill_name="github-skill-organizer",
        description="Core logic"
    ) as writer:
        writer.write("import os\n# business code...")
        # 自動在文件開頭插入 docstring 包裹的 YAML frontmatter
    """

    REQUIRED_FIELDS = [
        "title", "name", "description", "version",
        "github_repository", "target_branch", "updated_at",
        "auth_config", "file_mapping", "fixes"
    ]

    def __init__(
        self,
        file_path: str,
        skill_name: str,
        description: str,
        version: str = "1.0.0",
        github_repo: str = "nervlin4444/ai.skills.incubation",
        target_branch: str = "main",
        fixes: Optional[List[int]] = None
    ):
        self.file_path = Path(os.path.expanduser(str(file_path)))
        self.skill_name = skill_name
        self.description = description
        self.version = version
        self.github_repo = github_repo
        self.target_branch = target_branch
        self.fixes = fixes if fixes is not None else []
        self.content_buffer = []
        self._validate_paths()

    def _validate_paths(self) -> None:
        """確保文件路徑安全。"""
        if self.file_path.exists():
            raise FileExistsError(f"[GUARD] 文件已存在，禁止覆蓋: {self.file_path}")
        # 確保父目錄存在
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _generate_frontmatter(self) -> str:
        """生成標準 YAML frontmatter。fixes 欄位必須存在，可為空列表。"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        github_path = f"{self.skill_name}/{self.file_path.name}"
        
        # fixes 欄位：必須存在，值為整數列表（可空）
        fixes_str = "[]"
        if self.fixes:
            fixes_str = ", ".join(str(f) for f in self.fixes)
            fixes_str = f"[{fixes_str}]"
        
        fm = f"""---
title: "{self.description}"
name: {self.skill_name}
description: "{self.description}"
version: "{self.version}"
github_repository: "{self.github_repo}"
target_branch: "{self.target_branch}"
updated_at: "2026-05-22T18:46:26+08:00"
fixes: {fixes_str}
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "{self.file_path.name}"
  github_path: "{github_path}"
---
"""
        return fm

    def _generate_py_docstring_frontmatter(self) -> str:
        """生成 Python docstring 格式的 YAML frontmatter。"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        github_path = f"{self.skill_name}/{self.file_path.name}"
        
        fixes_str = "[]"
        if self.fixes:
            fixes_str = ", ".join(str(f) for f in self.fixes)
            fixes_str = f"[{fixes_str}]"
        
        q = chr(34) * 3  # 三重引號，避免嵌套解析錯誤
        docstring_lines = [
            q,
            "---",
            f'title: "{self.description}"',
            f"name: {self.skill_name}",
            f'description: "{self.description}"',
            f'version: "{self.version}"',
            f'github_repository: "{self.github_repo}"',
            f'target_branch: "{self.target_branch}"',
            f'updated_at: "{now}"',
            f"fixes: {fixes_str}",
            "auth_config:",
            '  provider: "github"',
            '  auth_method: "token"',
            '  token_env_var: "GITHUB_TOKEN"',
            '  env_file_path: ".env"',
            "file_mapping:",
            f'  local_path: "{self.file_path.name}"',
            f'  github_path: "{github_path}"',
            "---",
            q,
            "",
        ]
        return "\n".join(docstring_lines)

    def write(self, content: str) -> None:
        """累積業務內容。"""
        self.content_buffer.append(content)

    def _auto_detect_fixes(self, content: str) -> List[int]:
        """
        自動從代碼內容檢測 Fixes 聲明。
        檢測模式：Fixes #N / Fixed #N / Closes #N / 修復 Issue #N / 修復 #N
        返回：整數列表（去重排序）
        """
        patterns = [
            r"[Ff]ixes\s+#(\d+)",
            r"[Ff]ixed\s+#(\d+)",
            r"[Cc]loses\s+#(\d+)",
            r"修復\s*[Ii]ssue\s*#?(\d+)",
            r"修復\s*#(\d+)",
        ]
        found = set()
        for p in patterns:
            for m in re.finditer(p, content):
                found.add(int(m.group(1)))
        return sorted(found)

    def __enter__(self):
        """上下文管理器入口。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口：寫入 frontmatter + 業務內容。
        
        規則：
        1. 如果 self.fixes 為空且業務內容中有 Fixes 聲明 → 自動補充
        2. fixes 欄位必須存在（key 必須在），值可為空列表 []
        3. 寫入後驗證 frontmatter 完整性
        """
        if exc_type is not None:
            return False  # 異常時不寫入
        
        business_content = "\n".join(self.content_buffer)
        
        # 自動檢測：如果沒有顯式傳入 fixes，從業務內容中檢測
        if not self.fixes:
            detected = self._auto_detect_fixes(business_content)
            if detected:
                self.fixes = detected
                print(f"[FILES-DESIGNER] 自動檢測到 Fixes 聲明: {detected}")
        
        # 生成 frontmatter
        if self.file_path.suffix == ".py":
            frontmatter = self._generate_py_docstring_frontmatter()
        else:
            frontmatter = self._generate_frontmatter()
        
        full_content = frontmatter + "\n" + business_content
        
        # 寫入文件
        try:
            self.file_path.write_text(full_content, encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"[GUARD] 寫入失敗: {self.file_path} - {e}")
        
        # 驗證：確保 fixes 欄位存在
        written = self.file_path.read_text(encoding="utf-8")
        if "fixes:" not in written:
            self.file_path.unlink()
            raise RuntimeError(f"[GUARD] 寫入後驗證失敗（fixes 欄位缺失）: {self.file_path}")
        
        print(f"[FILES-DESIGNER] 已創建: {self.file_path} (fixes: {self.fixes})")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skill Files Designer - 技能文件設計器")
    parser.add_argument("--file-path", required=True, help="文件路徑")
    parser.add_argument("--skill-name", required=True, help="技能名稱")
    parser.add_argument("--description", required=True, help="文件描述")
    parser.add_argument("--version", default="1.0.0", help="版本號")
    parser.add_argument("--fixes", nargs="+", type=int, default=None, help="關聯的 Issue 編號列表（可選）")
    parser.add_argument("--content", default="", help="業務內容（可選，默認空）")
    args = parser.parse_args()
    
    with SkillFileWriter(
        file_path=args.file_path,
        skill_name=args.skill_name,
        description=args.description,
        version=args.version,
        fixes=args.fixes
    ) as writer:
        if args.content:
            writer.write(args.content)
    
    print("[FILES-DESIGNER] 完成")


if __name__ == "__main__":
    main()