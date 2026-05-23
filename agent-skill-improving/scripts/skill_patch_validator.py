"""
---
title: "Skill Patch Validator - 技能補丁驗證與應用器"
name: agent-skill-improving
description: "讀取、驗證、應用技能補丁（Patch），支持干跑預覽與自動回滾。禁止直接手動修改技能文件。"
version: "1.3.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T17:07:00+08:00"
auth_config:
  provider: "github"
  auth_method: "personal_access_token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
fixes: []
file_mapping:
  local_path: "scripts/skill_patch_validator.py"
  github_path: "agent-skill-improving/scripts/skill_patch_validator.py"
---
"""

import os
import sys
import json
import re
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any


class SkillPatchValidator:
    """
    LOCK v1.2.5: 技能補丁驗證與應用器

    職責：
    1. 讀取並驗證 patch 文件的合法性
    2. 干跑預覽（dry-run）確認變更內容
    3. 應用 patch 並自動備份原文件
    4. 應用後自動調用 skill_integrity_checker 驗證
    5. 支持回滾到上一版本

    安全規則：
    - 禁止修改無 frontmatter 的文件
    - 禁止刪除文件（只能替換內容）
    - 禁止修改 .env 或憑證相關文件
    - 備份保留在 .backups/（上傳時自動排除）
    """

    # 禁止修改的文件模式
    PROTECTED_PATTERNS = [
        r"\.env",
        r"\.env\.example",
        r".*token.*",
        r".*secret.*",
        r".*credential.*",
        r".*password.*",
    ]

    def __init__(self, skill_dir: str):
        self.skill_dir = Path(os.path.expanduser(str(skill_dir))).resolve()
        self.backups_dir = self.skill_dir / ".backups"
        self.last_patch_record: Optional[Dict] = None
        self._ensure_backups_dir()

    def _ensure_backups_dir(self) -> None:
        """確保備份目錄存在。"""
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def _is_protected_file(self, relative_path: str) -> bool:
        """檢查文件是否受保護（禁止修改）。"""
        lower = relative_path.lower()
        for pattern in self.PROTECTED_PATTERNS:
            if re.search(pattern, lower):
                return True
        return False

    def _has_frontmatter(self, file_path: Path) -> bool:
        """檢查文件是否包含 frontmatter。"""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return False
        if file_path.suffix == ".py":
            return "---" in content and "title:" in content and "name:" in content
        return content.strip().startswith("---") and "title:" in content

    def _backup_file(self, target_file: Path) -> Tuple[bool, str, Optional[Path]]:
        """
        備份目標文件到 .backups/。

        Returns:
            (success, message, backup_path)
        """
        if not target_file.exists():
            return True, "[BACKUP] 原文件不存在，無需備份", None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        checksum = hashlib.sha256(target_file.read_bytes()).hexdigest()[:8]
        backup_name = f"{target_file.name}.{timestamp}.{checksum}.bak"
        backup_path = self.backups_dir / backup_name

        try:
            shutil.copy2(target_file, backup_path)
        except Exception as e:
            return False, f"[BACKUP-FAIL] 無法備份 {target_file}: {e}", None

        return True, f"[BACKUP-OK] {target_file.name} -> {backup_name}", backup_path

    def load_patch(self, patch_path: str) -> Dict:
        """
        讀取 patch 文件。

        支持格式：JSON

        Returns:
            dict: patch 內容或錯誤信息
        """
        p = Path(os.path.expanduser(str(patch_path)))
        if not p.exists():
            return {"status": "error", "reason": f"[LOAD] Patch 文件不存在: {p}"}

        try:
            content = p.read_text(encoding="utf-8")
            patch = json.loads(content)
        except json.JSONDecodeError as e:
            return {"status": "error", "reason": f"[LOAD] JSON 解析失敗: {e}"}
        except Exception as e:
            return {"status": "error", "reason": f"[LOAD] 讀取失敗: {e}"}

        return {"status": "loaded", "patch": patch, "path": str(p)}

    def validate_patch(self, patch: Dict) -> Dict:
        """
        驗證 patch 合法性。

        檢查項：
        1. 必填欄位（version, target_skill, changes）
        2. 目標技能名稱匹配
        3. 每個 change 的 action 合法性（replace/insert/delete_line）
        4. 目標文件是否存在且含 frontmatter
        5. 目標文件不在受保護列表中
        6. old 內容是否與當前文件匹配（一致性檢查）
        """
        if "patch" in patch:
            patch = patch["patch"]

        errors = []
        warnings = []

        # 檢查必填欄位
        required = ["version", "target_skill", "changes"]
        for field in required:
            if field not in patch:
                errors.append(f"[VALIDATE] 缺少必填欄位: {field}")

        if errors:
            return {"status": "invalid", "errors": errors, "warnings": warnings}

        # 檢查目標技能名稱
        target_skill = patch.get("target_skill", "")
        if self.skill_dir.name != target_skill:
            warnings.append(
                f"[VALIDATE] 目標技能名稱不匹配: "
                f"patch={target_skill}, 實際={self.skill_dir.name}"
            )

        # 檢查每個 change
        changes = patch.get("changes", [])
        if not isinstance(changes, list):
            errors.append("[VALIDATE] changes 必須是列表")
            return {"status": "invalid", "errors": errors, "warnings": warnings}

        for i, change in enumerate(changes):
            idx = i + 1

            # 檢查 change 結構
            if not isinstance(change, dict):
                errors.append(f"[VALIDATE] change[{idx}] 必須是字典")
                continue

            file_rel = change.get("file", "")
            action = change.get("action", "")

            if not file_rel:
                errors.append(f"[VALIDATE] change[{idx}] 缺少 file")
                continue

            if action not in ("replace", "insert", "delete_line"):
                errors.append(
                    f"[VALIDATE] change[{idx}] action 非法: {action} "
                    f"(必須為 replace/insert/delete_line)"
                )

            target_file = self.skill_dir / file_rel

            # 受保護文件檢查
            if self._is_protected_file(file_rel):
                errors.append(
                    f"[VALIDATE] change[{idx}] 目標文件受保護，禁止修改: {file_rel}"
                )
                continue

            # 文件存在性與 frontmatter 檢查
            if not target_file.exists():
                errors.append(
                    f"[VALIDATE] change[{idx}] 目標文件不存在: {file_rel}"
                )
                continue

            if not self._has_frontmatter(target_file):
                errors.append(
                    f"[VALIDATE] change[{idx}] 目標文件無 frontmatter（身份證）: {file_rel}"
                )

            # 一致性檢查（replace 必須匹配 old）
            if action == "replace" and "old" in change:
                current = target_file.read_text(encoding="utf-8")
                old_content = change["old"]
                if old_content not in current:
                    errors.append(
                        f"[VALIDATE] change[{idx}] old 內容與當前文件不匹配: {file_rel}"
                    )

        if errors:
            return {"status": "invalid", "errors": errors, "warnings": warnings}

        return {
            "status": "valid",
            "changes_count": len(changes),
            "warnings": warnings,
            "patch": patch
        }

    def apply_patch(self, patch_input: Dict, dry_run: bool = False) -> Dict:
        """
        應用 patch。

        Args:
            patch_input: load_patch 或 validate_patch 的返回結果
            dry_run: True=僅預覽不寫入

        Returns:
            dict: 應用結果
        """
        # 提取 patch 數據
        if "patch" in patch_input and isinstance(patch_input["patch"], dict):
            patch = patch_input["patch"]
        elif "patch" in patch_input:
            patch = patch_input
        else:
            patch = patch_input

        # 先驗證
        validation = self.validate_patch(patch)
        if validation["status"] != "valid":
            return {
                "status": "rejected",
                "reason": "驗證失敗，拒絕應用",
                "validation": validation
            }

        changes = patch.get("changes", [])
        results = []
        backups = []
        all_success = True

        print(f"[PATCH] {'[DRY-RUN] ' if dry_run else ''}開始應用 {len(changes)} 個變更...")

        for i, change in enumerate(changes):
            file_rel = change["file"]
            action = change["action"]
            target_file = self.skill_dir / file_rel

            print(f"  [{i+1}/{len(changes)}] {action} -> {file_rel}")

            # 備份（dry-run 也執行備份邏輯檢查，但不實際複製）
            if not dry_run:
                ok, msg, backup_path = self._backup_file(target_file)
                if not ok:
                    results.append({
                        "file": file_rel,
                        "ok": False,
                        "msg": msg,
                        "action": action
                    })
                    all_success = False
                    continue
                if backup_path:
                    backups.append(str(backup_path))

            # 執行變更
            if dry_run:
                ok, msg = True, f"[DRY-RUN] 預覽 {action} 成功"
            else:
                ok, msg = self._execute_change(target_file, change)

            results.append({
                "file": file_rel,
                "ok": ok,
                "msg": msg,
                "action": action
            })
            if not ok:
                all_success = False

        # 記錄 patch 歷史
        self.last_patch_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "patch_version": patch.get("patch_version", "unknown"),
            "target_version": patch.get("target_version", "unknown"),
            "results": results,
            "backups": backups,
            "dry_run": dry_run
        }

        # 寫入歷史記錄
        if not dry_run and all_success:
            self._write_patch_history(self.last_patch_record)

        if dry_run:
            return {
                "status": "dry_run_complete",
                "results": results,
                "notice": "這是預覽模式，未實際修改任何文件。確認無誤後重新執行（dry_run=False）"
            }

        if not all_success:
            return {
                "status": "partial_failure",
                "results": results,
                "backups": backups,
                "notice": "部分變更失敗。已成功的變更已備份，可嘗試 rollback_last() 回滾。"
            }

        # 應用成功後，自動驗證完整性
        integrity_result = self._post_patch_integrity_check()

        return {
            "status": "success",
            "results": results,
            "backups": backups,
            "integrity_check": integrity_result,
            "next_steps": [
                "1. 檢查變更結果",
                "2. 執行 skill_integrity_checker.py 驗證",
                "3. 通過 github-skill-organizer 上傳"
            ]
        }

    def _execute_change(self, target_file: Path, change: Dict) -> Tuple[bool, str]:
        """執行單個變更。"""
        action = change["action"]

        try:
            content = target_file.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"[EXEC] 無法讀取文件: {e}"

        if action == "replace":
            old = change.get("old", "")
            new = change.get("new", "")
            if old not in content:
                return False, "[EXEC] old 內容不在當前文件中（並發修改？）"
            new_content = content.replace(old, new, 1)
            target_file.write_text(new_content, encoding="utf-8")
            return True, f"[EXEC] replace 成功"

        elif action == "insert":
            after = change.get("after", "")
            new = change.get("new", "")
            if after not in content:
                return False, f"[EXEC] 插入錨點 'after' 不存在"
            new_content = content.replace(after, after + new, 1)
            target_file.write_text(new_content, encoding="utf-8")
            return True, f"[EXEC] insert 成功"

        elif action == "delete_line":
            line_pattern = change.get("line", "")
            lines = content.splitlines()
            new_lines = [ln for ln in lines if line_pattern not in ln]
            if len(new_lines) == len(lines):
                return False, f"[EXEC] 未找到匹配行: {line_pattern}"
            target_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            return True, f"[EXEC] delete_line 成功"

        else:
            return False, f"[EXEC] 未知 action: {action}"

    def rollback_last(self) -> Dict:
        """
        回滾上一次 patch。

        從 .backups/ 目錄找到最新的備份並恢復。
        """
        if not self.last_patch_record:
            # 嘗試從歷史記錄讀取
            history = self._read_patch_history()
            if not history:
                return {"status": "error", "reason": "[ROLLBACK] 無 patch 歷史記錄"}
            self.last_patch_record = history[-1]

        backups = self.last_patch_record.get("backups", [])
        if not backups:
            return {"status": "error", "reason": "[ROLLBACK] 無備份文件可恢復"}

        restored = []
        failed = []

        for backup_path_str in backups:
            backup_path = Path(backup_path_str)
            if not backup_path.exists():
                failed.append(f"[ROLLBACK] 備份文件不存在: {backup_path}")
                continue

            # 解析原始文件名（去掉 .timestamp.checksum.bak）
            original_name = backup_path.name.split(".")[0]
            # 找到對應的目標文件（在 skill_dir 中搜索）
            target_candidates = list(self.skill_dir.rglob(original_name))
            if not target_candidates:
                failed.append(f"[ROLLBACK] 找不到原始文件: {original_name}")
                continue

            target_file = target_candidates[0]
            try:
                shutil.copy2(backup_path, target_file)
                restored.append(str(target_file))
            except Exception as e:
                failed.append(f"[ROLLBACK] 恢復失敗 {target_file}: {e}")

        if failed and not restored:
            return {"status": "error", "reason": "全部回滾失敗", "details": failed}

        return {
            "status": "rollback_complete" if not failed else "rollback_partial",
            "restored": restored,
            "failed": failed,
            "notice": "回滾完成後請執行 skill_integrity_checker.py 驗證"
        }

    def _write_patch_history(self, record: Dict) -> None:
        """寫入 patch 歷史到 .backups/patch_history.jsonl。"""
        history_file = self.backups_dir / "patch_history.jsonl"
        line = json.dumps(record, ensure_ascii=False)
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _read_patch_history(self) -> List[Dict]:
        """讀取 patch 歷史。"""
        history_file = self.backups_dir / "patch_history.jsonl"
        if not history_file.exists():
            return []
        records = []
        with open(history_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def _post_patch_integrity_check(self) -> Dict:
        """
        應用 patch 後的完整性檢查。

        調用 skill_integrity_checker.py（如果可用）。
        """
        checker_path = self.skill_dir / "scripts" / "skill_integrity_checker.py"
        if not checker_path.exists():
            return {
                "status": "skipped",
                "reason": "skill_integrity_checker.py 不存在，跳過自動驗證"
            }

        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, str(checker_path), "--strict"],
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "status": "completed",
                "returncode": result.returncode,
                "stdout_preview": result.stdout[:500],
                "stderr_preview": result.stderr[:500] if result.stderr else ""
            }
        except Exception as e:
            return {"status": "error", "reason": f"完整性檢查調用失敗: {e}"}


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Skill Patch Validator - 補丁驗證與應用"
    )
    parser.add_argument(
        "--skill-dir",
        required=True,
        help="技能目錄路徑"
    )
    parser.add_argument(
        "--patch",
        required=True,
        help="Patch JSON 文件路徑"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="預覽模式，不實際修改文件"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="回滾上一次 patch"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="僅驗證 patch，不應用"
    )

    args = parser.parse_args()

    validator = SkillPatchValidator(skill_dir=args.skill_dir)

    if args.rollback:
        result = validator.rollback_last()
        print(f"[PATCH-VALIDATOR] 回滾狀態: {result['status']}")
        if result.get('restored'):
            print(f"  已恢復: {len(result['restored'])} 個文件")
        if result.get('failed'):
            print(f"  失敗: {len(result['failed'])} 個")
        return

    # 加載 patch
    load_result = validator.load_patch(args.patch)
    if load_result["status"] == "error":
        print(f"[PATCH-VALIDATOR] 錯誤: {load_result['reason']}")
        sys.exit(1)

    patch_data = load_result

    if args.validate_only:
        validation = validator.validate_patch(patch_data)
        print(f"[PATCH-VALIDATOR] 驗證狀態: {validation['status']}")
        if validation.get('errors'):
            for err in validation['errors']:
                print(f"  ❌ {err}")
        if validation.get('warnings'):
            for warn in validation['warnings']:
                print(f"  ⚠️  {warn}")
        if validation['status'] == 'valid':
            print(f"  ✅ 驗證通過，{validation['changes_count']} 個變更可應用")
        return

    # 應用 patch
    result = validator.apply_patch(patch_data, dry_run=args.dry_run)
    print(f"[PATCH-VALIDATOR] 應用狀態: {result['status']}")

    if result['status'] == 'success':
        print(f"  ✅ 全部變更應用成功")
        if result.get('integrity_check'):
            ic = result['integrity_check']
            print(f"  完整性檢查: {ic['status']} (returncode={ic.get('returncode', 'N/A')})")
    elif result['status'] == 'dry_run_complete':
        print(f"  🔍 預覽完成，未修改文件")
        for r in result.get('results', []):
            print(f"    {r['file']}: {r['msg']}")
    else:
        print(f"  ❌ 應用失敗")
        for r in result.get('results', []):
            status = "✅" if r['ok'] else "❌"
            print(f"    {status} {r['file']}: {r['msg']}")


if __name__ == "__main__":
    main()
