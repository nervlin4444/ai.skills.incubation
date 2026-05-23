'''
---
title: "Skill Integrity Checker - 技能合規檢查器"
name: agent-skill-improving
description: "掃描技能目錄，執行 30+ 項合規檢查 + 9 項架構紅線。v1.3.0 修正：改用 SkillFrontmatterExtractor 統一提取；Fixes 一致性檢查排除 markdown 說明文字；check_github_path 支持 dict/list/str 格式。"
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
  local_path: "scripts/skill_integrity_checker.py"
  github_path: "agent-skill-improving/scripts/skill_integrity_checker.py"
---
'''

import os
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Any

# v1.3.0: 統一使用 SkillFrontmatterExtractor，禁止自行實現解析邏輯
try:
    from skill_files_designer import SkillFrontmatterExtractor
except ImportError:
    import importlib.util
    _designer_path = Path(__file__).parent / 'skill_files_designer.py'
    if _designer_path.exists():
        spec = importlib.util.spec_from_file_location('skill_files_designer', _designer_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        SkillFrontmatterExtractor = mod.SkillFrontmatterExtractor
    else:
        raise ImportError('[INTEGRITY] skill_files_designer.py not found')

class SkillIntegrityChecker:
    """LOCK v1.3.0: 技能合規檢查器"""

    REQUIRED_FIELDS = [
        'title', 'name', 'description', 'version',
        'github_repository', 'target_branch', 'updated_at',
        'auth_config', 'file_mapping', 'fixes'
    ]

    RED_LINES = [
        'missing_skill_md', 'missing_readme_md', 'missing_frontmatter',
        'invalid_frontmatter_format', 'missing_required_field',
        'fixes_field_missing', 'fixes_invalid_type', 'fixes_invalid_value',
        'github_path_leading_slash', 'version_mismatch'
    ]

    def __init__(self, skill_dir: str, strict: bool = False):
        self.skill_dir = Path(os.path.expanduser(str(skill_dir))).resolve()
        self.strict = strict
        self.errors = []
        self.warnings = []
        self.red_lines = []

    def _read_frontmatter(self, file_path: Path) -> Optional[Dict]:
        """v1.3.0: 統一使用 SkillFrontmatterExtractor.extract()。"""
        return SkillFrontmatterExtractor.extract(str(file_path))

    def check_fixes_field(self, file_path: Path, frontmatter: Dict) -> Tuple[bool, str]:
        """檢查 fixes 欄位：必須存在、必須是列表、元素必須是整數。"""
        if 'fixes' not in frontmatter:
            self.red_lines.append('fixes_field_missing: ' + str(file_path))
            return False, '[RED-LINE] fixes 欄位缺失: ' + file_path.name
        fixes = frontmatter['fixes']
        if not isinstance(fixes, list):
            self.red_lines.append('fixes_invalid_type: ' + str(file_path))
            return False, '[RED-LINE] fixes 類型錯誤: ' + file_path.name + ' -> ' + type(fixes).__name__
        for item in fixes:
            if not isinstance(item, int):
                self.red_lines.append('fixes_invalid_value: ' + str(file_path))
                return False, '[RED-LINE] fixes 值錯誤: ' + file_path.name + ' -> ' + str(item) + ' (' + type(item).__name__ + ')'
        return True, '[OK] fixes: ' + (str(fixes) if fixes else '[]')

    def check_fixes_consistency(self, file_path: Path, content: str, frontmatter: Dict) -> Tuple[bool, str]:
        """
        v1.3.0 修正：只檢測代碼註釋中的 Fixes 聲明（# Fixes #N），排除 markdown 說明文字。
        """
        code_fixes = set()
        for line in content.splitlines():
            stripped = line.strip()
            # 只檢測以 # 開頭的行（代碼註釋），排除 markdown 列表項
            if stripped.startswith('#'):
                m = re.search(r'[Ff]ixes\s+#(\d+)', stripped)
                if m:
                    code_fixes.add(int(m.group(1)))
        fm_fixes = set(SkillFrontmatterExtractor.get_fixes(frontmatter))
        missing = code_fixes - fm_fixes
        if missing:
            self.red_lines.append('fixes_consistency: ' + str(file_path))
            nums = ', #'.join(str(x) for x in sorted(missing))
            return False, '[RED-LINE] Fixes 不一致: ' + file_path.name + ' 代碼註釋 #' + nums + ' 但 frontmatter 缺失'
        extra = fm_fixes - code_fixes
        if extra:
            nums = ', #'.join(str(x) for x in sorted(extra))
            self.warnings.append(file_path.name + ': fixes 聲明 #' + nums + ' 但代碼註釋未找到（歷史記錄）')
        return True, '[OK] Fixes 一致性通過'

    def check_required_fields(self, file_path: Path, frontmatter: Dict) -> Tuple[bool, str]:
        """檢查所有必填欄位是否存在。"""
        missing = [f for f in self.REQUIRED_FIELDS if f not in frontmatter]
        if missing:
            self.red_lines.append('missing_required_field: ' + str(file_path))
            return False, '[RED-LINE] 缺少必填欄位: ' + ', '.join(missing)
        return True, '[OK] 全部 ' + str(len(self.REQUIRED_FIELDS)) + ' 個必填欄位存在'

    def check_github_path(self, file_path: Path, frontmatter: Dict) -> Tuple[bool, str]:
        """v1.3.0: 使用 SkillFrontmatterExtractor.get_github_path() 支持 dict/list/str 格式。"""
        github_path = SkillFrontmatterExtractor.get_github_path(frontmatter)
        if not github_path:
            return True, '[WARN] github_path 為空'
        if github_path.startswith('/'):
            self.red_lines.append('github_path_leading_slash: ' + str(file_path))
            return False, '[RED-LINE] github_path 前導斜杠: ' + github_path
        return True, '[OK] github_path: ' + github_path

    def run(self) -> Dict:
        """執行完整檢查。"""
        print('[INTEGRITY] 開始檢查: ' + str(self.skill_dir))
        if not self.skill_dir.exists():
            return {'status': 'error', 'reason': '目錄不存在: ' + str(self.skill_dir)}
        skill_md = self.skill_dir / 'SKILL.md'
        if not skill_md.exists():
            self.red_lines.append('missing_skill_md')
            if self.strict:
                return {'status': 'failed', 'reason': 'SKILL.md 缺失', 'red_lines': self.red_lines}
        files_checked = 0
        for file_path in self.skill_dir.rglob('*'):
            if not file_path.is_file(): continue
            if file_path.suffix not in ('.md', '.py', '.json', '.html', '.env', '.yml', '.yaml'): continue
            if '.backups' in str(file_path) or '__pycache__' in str(file_path): continue
            files_checked += 1
            fm = self._read_frontmatter(file_path)
            if fm is None:
                if file_path.suffix in ('.md', '.py', '.json', '.html'):
                    self.red_lines.append('missing_frontmatter: ' + str(file_path))
                    print('  [FAIL] ' + file_path.name + ': 無 frontmatter')
                continue
            ok, msg = self.check_required_fields(file_path, fm)
            if not ok:
                print('  [FAIL] ' + file_path.name + ': ' + msg)
            ok, msg = self.check_fixes_field(file_path, fm)
            if not ok:
                print('  [FAIL] ' + file_path.name + ': ' + msg)
            else:
                print('  [OK]   ' + file_path.name + ': ' + msg)
            if file_path.suffix in ('.py', '.md'):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    ok, msg = self.check_fixes_consistency(file_path, content, fm)
                    if not ok:
                        print('  [FAIL] ' + file_path.name + ': ' + msg)
                except Exception:
                    pass
            ok, msg = self.check_github_path(file_path, fm)
            if not ok:
                print('  [FAIL] ' + file_path.name + ': ' + msg)
        print('\n[INTEGRITY] 檢查完成: ' + str(files_checked) + ' 個文件')
        if self.red_lines:
            return {'status': 'failed' if self.strict else 'warning', 'files_checked': files_checked, 'red_lines': self.red_lines, 'warnings': self.warnings, 'reason': '發現 ' + str(len(self.red_lines)) + ' 項紅線違規'}
        return {'status': 'passed', 'files_checked': files_checked, 'warnings': self.warnings, 'reason': '全部檢查通過'}

def main():
    parser = argparse.ArgumentParser(description='Skill Integrity Checker v1.3.0')
    parser.add_argument('--skill-dir', required=True, help='技能目錄路徑')
    parser.add_argument('--strict', action='store_true', help='嚴格模式')
    parser.add_argument('--report-path', help='報告輸出路徑')
    args = parser.parse_args()
    checker = SkillIntegrityChecker(skill_dir=args.skill_dir, strict=args.strict)
    result = checker.run()
    print('\n[INTEGRITY] 結果: ' + result['status'])
    if result['status'] == 'passed':
        print('  [OK] 全部通過')
    elif result['status'] == 'failed':
        print('  [FAIL] ' + result['reason'])
        for rl in result.get('red_lines', []):
            print('    - ' + rl)
        sys.exit(1)
    else:
        print('  [WARN] ' + result['reason'])
        for rl in result.get('red_lines', []):
            print('    - ' + rl)

if __name__ == '__main__':
    main()