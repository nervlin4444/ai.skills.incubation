'''
---
title: "Skill Files Designer - 技能文件設計器"
name: agent-skill-improving
description: "生成標準 frontmatter，攔截直接寫入操作，自動檢測 Fixes 聲明。v1.3.0 合併 SkillFrontmatterExtractor：統一文件讀取與生成入口，支持 .md/.py/.json/.html/.env frontmatter 提取。修正 _parse_yaml 列表/字典嵌套 bug。"
version: "1.3.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T16:10:00+08:00"
fixes: []
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "scripts/skill_files_designer.py"
  github_path: "agent-skill-improving/scripts/skill_files_designer.py"
---
'''

import os
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any

class SkillFrontmatterExtractor:
    """
    v1.3.0: 統一 frontmatter 提取模組
    支持 .md / .py / .json / .html / .yaml / .yml / .env 文件格式
    """

    @staticmethod
    def extract(file_path: str) -> Optional[Dict]:
        """統一提取接口：根據後綴自動選擇提取方式。"""
        p = Path(os.path.expanduser(str(file_path))).resolve()
        if not p.exists():
            return None
        try:
            content = p.read_text(encoding='utf-8')
        except Exception:
            return None
        suffix = p.suffix.lower()
        if suffix == '.py':
            return SkillFrontmatterExtractor._extract_py(content)
        elif suffix in ('.md', '.json', '.yaml', '.yml', '.env'):
            return SkillFrontmatterExtractor._extract_standard(content)
        elif suffix == '.html':
            return SkillFrontmatterExtractor._extract_html(content)
        else:
            return None

    @staticmethod
    def _extract_standard(content: str) -> Optional[Dict]:
        """提取標準 YAML frontmatter（--- 開頭）。"""
        stripped = content.strip()
        if not stripped.startswith('---'):
            return None
        end = stripped.find('---', 3)
        if end == -1:
            return None
        return SkillFrontmatterExtractor._parse_yaml(stripped[3:end])

    @staticmethod
    def _extract_py(content: str) -> Optional[Dict]:
        """提取 .py docstring 中的 YAML frontmatter。"""
        m = re.search(r'"""\s*\n(---.*?---)\s*\n"""', content, re.DOTALL)
        if not m:
            m = re.search(r"'''\s*\n(---.*?---)\s*\n'''", content, re.DOTALL)
        if m:
            return SkillFrontmatterExtractor._parse_yaml(m.group(1))
        return None

    @staticmethod
    def _extract_html(content: str) -> Optional[Dict]:
        """提取 HTML 註釋中的 YAML frontmatter。"""
        m = re.search(r'<!--\s*---\s*(.*?)\s*---\s*-->', content, re.DOTALL)
        if m:
            return SkillFrontmatterExtractor._parse_yaml(m.group(1))
        return None

    @staticmethod
    def _parse_yaml(yaml_text: str) -> Dict:
        """
        簡易 YAML 解析器（支持一層 + 列表字典項 + 字典嵌套）。
        v1.3.0 修正：當 key 的值為空時，自動根據子項初始化為列表或字典。
        """
        result = {}
        current_key = None
        list_item_dict = None
        for raw_line in yaml_text.splitlines():
            line = raw_line.rstrip()
            if not line.strip() or line.strip().startswith('#'):
                continue
            # 檢測列表項字典（- key: value 格式）
            if line.strip().startswith('- ') and ':' in line:
                key_part = line.strip()[2:]
                if ':' in key_part:
                    k, v = key_part.split(':', 1)
                    k = k.strip()
                    v = v.strip().strip(chr(34)).strip("'")
                    if current_key:
                        # 如果 current_key 的值不是列表，自動初始化為列表
                        if not isinstance(result.get(current_key), list):
                            result[current_key] = []
                        if list_item_dict is None:
                            list_item_dict = {}
                            result[current_key].append(list_item_dict)
                        list_item_dict[k] = v
                    continue
            # 檢測縮進行（列表項的屬性或字典的屬性）
            indent = len(line) - len(line.lstrip())
            if indent >= 2 and current_key:
                stripped = line.strip()
                if ':' in stripped:
                    k, v = stripped.split(':', 1)
                    k = k.strip()
                    v = v.strip().strip(chr(34)).strip("'")
                    # 如果 current_key 的值是空字符串，初始化為字典（支持 dict 嵌套）
                    if isinstance(result.get(current_key), str) and result.get(current_key) == '':
                        result[current_key] = {}
                        list_item_dict = None
                    # 如果是字典，直接設置屬性
                    if isinstance(result.get(current_key), dict):
                        result[current_key][k] = v
                        continue
                    # 如果是列表，處理列表項屬性
                    if isinstance(result.get(current_key), list) and list_item_dict is not None:
                        list_item_dict[k] = v
                        continue
            # 標準 key: value 行
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip().strip(chr(34)).strip("'")
                if val.startswith('[') and val.endswith(']'):
                    inner = val[1:-1].strip()
                    if inner:
                        result[key] = [int(x.strip()) for x in inner.split(',') if x.strip().isdigit()]
                    else:
                        result[key] = []
                    list_item_dict = None
                elif val.lower() in ('true', 'false'):
                    result[key] = val.lower() == 'true'
                    list_item_dict = None
                else:
                    result[key] = val
                    list_item_dict = None
                current_key = key
        return result

    @staticmethod
    def get_github_path(frontmatter: Dict) -> str:
        """從 frontmatter 提取 github_path，支持 dict/list/str 格式。"""
        fm = frontmatter.get('file_mapping', '')
        if isinstance(fm, dict):
            return fm.get('github_path', '')
        elif isinstance(fm, list):
            if fm and isinstance(fm[0], dict):
                return fm[0].get('github_path', '')
            for item in fm:
                if isinstance(item, str) and 'github_path:' in item:
                    parts = item.split('github_path:')
                    if len(parts) > 1:
                        return parts[1].strip().strip(chr(34)).strip("'")
        return ''

    @staticmethod
    def get_fixes(frontmatter: Dict) -> List[int]:
        """從 frontmatter 提取 fixes，支持 list/int/str 格式。"""
        fixes = frontmatter.get('fixes', [])
        if isinstance(fixes, list):
            return [int(x) for x in fixes if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]
        elif isinstance(fixes, int):
            return [fixes]
        elif isinstance(fixes, str):
            if fixes.isdigit():
                return [int(fixes)]
            if fixes.startswith('[') and fixes.endswith(']'):
                inner = fixes[1:-1].strip()
                return [int(x.strip()) for x in inner.split(',') if x.strip().isdigit()]
        return []

    @staticmethod
    def validate(frontmatter: Dict) -> Tuple[bool, List[str]]:
        """驗證 frontmatter 必填欄位。"""
        required = ['title', 'name', 'description', 'version',
                    'github_repository', 'target_branch', 'updated_at',
                    'auth_config', 'file_mapping', 'fixes']
        missing = [f for f in required if f not in frontmatter]
        if missing:
            return False, missing
        return True, []

class SkillFileWriter:
    """
    LOCK v1.3.0: 技能文件設計器（上下文管理器）

    核心機制：
    1. Agent 禁止直接 open()/write_text() 創建 .md/.py/.json/.html
    2. 必須通過 SkillFileWriter 生成 frontmatter 後再寫入業務內容
    3. 自動檢測代碼中的 Fixes 聲明並寫入 frontmatter fixes 欄位
    4. fixes 欄位必須存在（key 必須在），值可為空列表 []
    """

    REQUIRED_FIELDS = [
        'title', 'name', 'description', 'version',
        'github_repository', 'target_branch', 'updated_at',
        'auth_config', 'file_mapping', 'fixes'
    ]

    def __init__(
        self,
        file_path: str,
        skill_name: str,
        description: str,
        version: str = '1.0.0',
        github_repo: str = 'nervlin4444/ai.skills.incubation',
        target_branch: str = 'main',
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
            raise FileExistsError('[GUARD] 文件已存在，禁止覆蓋: ' + str(self.file_path))
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _generate_frontmatter(self) -> str:
        """生成標準 YAML frontmatter。fixes 欄位必須存在。"""
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+08:00')
        github_path = self.skill_name + '/' + self.file_path.name
        fixes_str = '[]'
        if self.fixes:
            fixes_str = '[' + ', '.join(str(f) for f in self.fixes) + ']'
        lines = ['---',
                 'title: ' + chr(34) + self.description + chr(34),
                 'name: ' + self.skill_name,
                 'description: ' + chr(34) + self.description + chr(34),
                 'version: ' + chr(34) + self.version + chr(34),
                 'github_repository: ' + chr(34) + self.github_repo + chr(34),
                 'target_branch: ' + chr(34) + self.target_branch + chr(34),
                 'updated_at: ' + chr(34) + now + chr(34),
                 'fixes: ' + fixes_str,
                 'auth_config:',
                 '  provider: ' + chr(34) + 'github' + chr(34),
                 '  auth_method: ' + chr(34) + 'token' + chr(34),
                 '  token_env_var: ' + chr(34) + 'GITHUB_TOKEN' + chr(34),
                 '  env_file_path: ' + chr(34) + '.env' + chr(34),
                 'file_mapping:',
                 '  local_path: ' + chr(34) + self.file_path.name + chr(34),
                 '  github_path: ' + chr(34) + github_path + chr(34),
                 '---']
        return '\n'.join(lines)

    def _generate_py_docstring_frontmatter(self) -> str:
        """生成 Python docstring 格式的 YAML frontmatter。"""
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+08:00')
        github_path = self.skill_name + '/' + self.file_path.name
        fixes_str = '[]'
        if self.fixes:
            fixes_str = '[' + ', '.join(str(f) for f in self.fixes) + ']'
        q = chr(34) * 3
        docstring_lines = [
            q,
            '---',
            'title: ' + chr(34) + self.description + chr(34),
            'name: ' + self.skill_name,
            'description: ' + chr(34) + self.description + chr(34),
            'version: ' + chr(34) + self.version + chr(34),
            'github_repository: ' + chr(34) + self.github_repo + chr(34),
            'target_branch: ' + chr(34) + self.target_branch + chr(34),
            'updated_at: ' + chr(34) + now + chr(34),
            'fixes: ' + fixes_str,
            'auth_config:',
            '  provider: ' + chr(34) + 'github' + chr(34),
            '  auth_method: ' + chr(34) + 'token' + chr(34),
            '  token_env_var: ' + chr(34) + 'GITHUB_TOKEN' + chr(34),
            '  env_file_path: ' + chr(34) + '.env' + chr(34),
            'file_mapping:',
            '  local_path: ' + chr(34) + self.file_path.name + chr(34),
            '  github_path: ' + chr(34) + github_path + chr(34),
            '---',
            q,
            '',
        ]
        return '\n'.join(docstring_lines)

    def write(self, content: str) -> None:
        """累積業務內容。"""
        self.content_buffer.append(content)

    def _auto_detect_fixes(self, content: str) -> List[int]:
        """自動從代碼內容檢測 Fixes 聲明。"""
        patterns = [
            r'[Ff]ixes\s+#(\d+)',
            r'[Ff]ixed\s+#(\d+)',
            r'[Cc]loses\s+#(\d+)',
            r'修復\s*[Ii]ssue\s*#?(\d+)',
            r'修復\s*#(\d+)',
        ]
        found = set()
        for p in patterns:
            for m in re.finditer(p, content):
                found.add(int(m.group(1)))
        return sorted(found)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口：寫入 frontmatter + 業務內容。"""
        if exc_type is not None:
            return False
        business_content = '\n'.join(self.content_buffer)
        if not self.fixes:
            detected = self._auto_detect_fixes(business_content)
            if detected:
                self.fixes = detected
                print('[FILES-DESIGNER] 自動檢測到 Fixes 聲明: ' + str(detected))
        if self.file_path.suffix == '.py':
            frontmatter = self._generate_py_docstring_frontmatter()
        else:
            frontmatter = self._generate_frontmatter()
        full_content = frontmatter + '\n' + business_content
        try:
            self.file_path.write_text(full_content, encoding='utf-8')
        except Exception as e:
            raise RuntimeError('[GUARD] 寫入失敗: ' + str(self.file_path) + ' - ' + str(e))
        written = self.file_path.read_text(encoding='utf-8')
        if 'fixes:' not in written:
            self.file_path.unlink()
            raise RuntimeError('[GUARD] 寫入後驗證失敗（fixes 欄位缺失）: ' + str(self.file_path))
        print('[FILES-DESIGNER] 已創建: ' + str(self.file_path) + ' (fixes: ' + str(self.fixes) + ')')

def main():
    parser = argparse.ArgumentParser(description='Skill Files Designer v1.3.0')
    parser.add_argument('--file-path', required=True, help='文件路徑')
    parser.add_argument('--skill-name', required=True, help='技能名稱')
    parser.add_argument('--description', required=True, help='文件描述')
    parser.add_argument('--version', default='1.0.0', help='版本號')
    parser.add_argument('--fixes', nargs='+', type=int, default=None, help='關聯 Issue 編號')
    parser.add_argument('--content', default='', help='業務內容')
    parser.add_argument('--extract-only', action='store_true', help='僅提取指定文件的 frontmatter')
    args = parser.parse_args()

    if args.extract_only:
        extractor = SkillFrontmatterExtractor()
        fm = extractor.extract(args.file_path)
        if fm:
            print('--- Extracted Frontmatter ---')
            for k, v in fm.items():
                print(str(k) + ': ' + str(v))
            ok, missing = extractor.validate(fm)
            if ok:
                print('驗證: 通過')
            else:
                print('驗證: 失敗 - 缺少: ' + ', '.join(missing))
        else:
            print('[ERROR] 無法提取 frontmatter')
        return

    with SkillFileWriter(
        file_path=args.file_path,
        skill_name=args.skill_name,
        description=args.description,
        version=args.version,
        fixes=args.fixes
    ) as writer:
        if args.content:
            writer.write(args.content)
    print('[FILES-DESIGNER] 完成')

if __name__ == '__main__':
    main()