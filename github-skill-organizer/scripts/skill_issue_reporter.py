"""
---
title: "Skill Issue Reporter - 標準 Issue 報告生成與上傳器"
name: github-skill-organizer
description: "強制按 CONTRIBUTING.md 規範生成標準 Issue 報告，支持本地預覽與直接上傳 GitHub Issues。使用標準庫 urllib.request 獨立實現，不依賴 github-restful-api-connector。"
version: "1.0.12"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-22T17:13:09+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "scripts/skill_issue_reporter.py"
  github_path: "github-skill-organizer/scripts/skill_issue_reporter.py"
---
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


class SkillIssueReporter:
    """
    LOCK v1.0.12: 標準 Issue 報告生成與上傳器

    核心原則：
    1. Agent 禁止自由發揮撰寫 Issue，必須通過此腳本生成
    2. 不同 LLM 調用此腳本，輸出完全一致的格式和內容
    3. 自動分類 [FRAMEWORK] / [RUNTIME] / [AGENT-BUG]
    4. 強制驗證每 Section >= 50 個中文字符
    5. 支持本地生成（默認）或直接上傳 GitHub Issues（--upload）

    上傳實現：使用標準庫 urllib.request，不依賴 github-restful-api-connector。
    只共享環境變數 GITHUB_TOKEN。
    """

    CLASSIFICATIONS = ["[FRAMEWORK]", "[RUNTIME]", "[AGENT-BUG]"]
    MIN_CHINESE_CHARS = 50
    MIN_ENGLISH_CHARS = 100
    MAX_TITLE_LEN = 80
    TEMPLATE_VERSION = "v1.0.12"

    def __init__(self, skill_dir: str, output_dir: str = "./improve/issues"):
        self.skill_dir = Path(os.path.expanduser(str(skill_dir))).resolve()
        self.output_dir = Path(os.path.expanduser(str(output_dir)))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._validate_skill_dir()

    def _validate_skill_dir(self) -> None:
        if not self.skill_dir.exists():
            raise FileNotFoundError(f"[REPORTER] 技能目錄不存在: {self.skill_dir}")
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"[REPORTER] SKILL.md 不存在: {skill_md}")

    def _detect_skill_info(self) -> Dict:
        skill_md = self.skill_dir / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        info = {"name": self.skill_dir.name, "version": "unknown", "github_repository": ""}
        for line in content.splitlines()[:30]:
            stripped = line.strip()
            if stripped.startswith("name:"):
                val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                if val:
                    info["name"] = val
            elif stripped.startswith("version:"):
                val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                if val:
                    info["version"] = val
            elif stripped.startswith("github_repository:"):
                val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                if val:
                    info["github_repository"] = val
        return info

    def _count_chinese_chars(self, text: str) -> int:
        return len(re.findall(r'[\u4e00-\u9fff]', text))

    def _count_total_chars(self, text: str) -> int:
        return len(text.replace(" ", "").replace("\n", "").replace("\t", ""))

    def _validate_section_length(self, text: str, section_name: str) -> Tuple[bool, str]:
        chinese = self._count_chinese_chars(text)
        total = self._count_total_chars(text)
        if chinese >= self.MIN_CHINESE_CHARS:
            return True, f"[OK] {section_name}: {chinese} 中文字符"
        if total >= self.MIN_ENGLISH_CHARS:
            return True, f"[OK] {section_name}: {total} 字符（純英文）"
        return False, (
            f"[REJECTED] {section_name}: 僅 {chinese} 中文字符 / {total} 總字符。"
            f"要求 >= {self.MIN_CHINESE_CHARS} 中文 或 >= {self.MIN_ENGLISH_CHARS} 總字符"
        )

    def _auto_classify(self, problem_desc: str, location: str) -> str:
        desc_lower = problem_desc.lower()
        loc_lower = location.lower()
        framework_kw = [
            "架構", "framework", "規範", "制度", "新增文件類型", "semantic-release",
            "配置", "決策", "原則", "身份證", "frontmatter 規範", "目錄結構",
            "是否需要", "應不應該", "怎樣設計"
        ]
        agentbug_kw = [
            "agent 生成", "agent 輸出", "agent 違反", "缺少 frontmatter",
            "沒有身份證", "命名錯誤", "路徑錯誤", "擅自", "未經確認"
        ]
        for kw in framework_kw:
            if kw in desc_lower or kw in loc_lower:
                return "[FRAMEWORK]"
        for kw in agentbug_kw:
            if kw in desc_lower or kw in loc_lower:
                return "[AGENT-BUG]"
        return "[RUNTIME]"

    def _create_github_issue(self, owner: str, repo: str, title: str, body: str) -> Dict:
        """
        使用標準庫 urllib.request 直接創建 GitHub Issue。
        不依賴 github-restful-api-connector，只共享 GITHUB_TOKEN 環境變數。
        """
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            return {"status": "error", "reason": "[UPLOAD] GITHUB_TOKEN not set"}

        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "skill_issue_reporter/1.0.12"
        }
        payload = json.dumps({"title": title, "body": body}).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "status": "created",
                    "issue_number": data.get("number"),
                    "issue_url": data.get("html_url"),
                    "issue_id": data.get("id")
                }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if hasattr(e, "read") else ""
            return {
                "status": "failed",
                "reason": f"[UPLOAD] GitHub API error {e.code}: {error_body[:200]}"
            }
        except Exception as e:
            return {"status": "failed", "reason": f"[UPLOAD] Network error: {e}"}

    def generate(
        self,
        classification: str,
        summary: str,
        reproduction_steps: List[Dict],
        root_cause: Dict,
        attempted_fixes: List[Dict],
        proposed_fix: Dict,
        verification: Optional[Dict] = None,
        dry_run: bool = False,
        upload: bool = False
    ) -> Dict:
        if classification not in self.CLASSIFICATIONS:
            return {
                "status": "rejected",
                "reason": f"[INVALID] 分類必須為 {self.CLASSIFICATIONS}，收到: {classification}"
            }

        skill_info = self._detect_skill_info()
        skill_name = skill_info["name"]
        version = skill_info["version"]
        github_repo = skill_info.get("github_repository", "")

        # 驗證各 Section 字數
        validations = []
        all_pass = True

        full_summary = f"{classification} {skill_name} {version} - {summary}"
        ok, msg = self._validate_section_length(full_summary, "Section 1 問題摘要")
        validations.append({"section": "1", "ok": ok, "msg": msg})
        if not ok:
            all_pass = False

        repro_text = "\n".join([
            f"{s['step']}. 操作: {s.get('action', '')} 參數: {s.get('parameters', '')} 結果: {s.get('result', '')}"
            for s in reproduction_steps
        ])
        ok, msg = self._validate_section_length(repro_text, "Section 2 復現步驟")
        validations.append({"section": "2", "ok": ok, "msg": msg})
        if not ok:
            all_pass = False

        rc_text = (
            f"位置: {root_cause.get('location', '')} "
            f"現象: {root_cause.get('phenomenon', '')} "
            f"問題: {root_cause.get('problem', '')} "
            f"後果: {root_cause.get('consequence', '')}"
        )
        ok, msg = self._validate_section_length(rc_text, "Section 3 根因分析")
        validations.append({"section": "3", "ok": ok, "msg": msg})
        if not ok:
            all_pass = False

        pf_text = (
            f"方案: {proposed_fix.get('solution', '')} "
            f"影響: {proposed_fix.get('impact_scope', '')} "
            f"風險: {proposed_fix.get('risk', '')} "
            f"預期: {proposed_fix.get('expected_result', '')}"
        )
        ok, msg = self._validate_section_length(pf_text, "Section 5 建議修復")
        validations.append({"section": "5", "ok": ok, "msg": msg})
        if not ok:
            all_pass = False

        if not all_pass:
            return {
                "status": "rejected",
                "reason": "[VALIDATION-FAILED] 部分 Section 字數不足，請擴充內容",
                "validations": validations,
                "notice": "請根據上面的 [REJECTED] 提示擴充對應 Section，然後重新調用本腳本"
            }

        title = f"{classification} {skill_name} {version} - {summary}"[:self.MAX_TITLE_LEN]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 構建 Markdown
        md_lines = [
            f"<!-- Issue Template Version: {self.TEMPLATE_VERSION} -->",
            f"<!-- Generated by: skill_issue_reporter.py -->",
            f"<!-- Timestamp: {timestamp} -->",
            "",
            f"# {title}",
            "",
            "## Section 1: 問題摘要",
            "",
            full_summary,
            "",
            "## Section 2: 復現步驟",
            "",
        ]
        for step in reproduction_steps:
            md_lines.extend([
                f"{step['step']}. 操作: {step.get('action', '')}",
                f"   參數: {step.get('parameters', '')}",
                f"   結果: {step.get('result', '')}",
                "",
            ])

        md_lines.extend([
            "## Section 3: 根因分析",
            "",
            f"**位置:** {root_cause.get('location', '')}",
            f"**現象:** {root_cause.get('phenomenon', '')}",
            f"**問題:** {root_cause.get('problem', '')}",
            f"**後果:** {root_cause.get('consequence', '')}",
            "",
            "## Section 4: 已嘗試的修復",
            "",
        ])
        if attempted_fixes:
            for i, af in enumerate(attempted_fixes, 1):
                md_lines.extend([
                    f"嘗試 {i}:",
                    f"  方法: {af.get('method', '無')}",
                    f"  結果: {af.get('result', '無')}",
                    "",
                ])
        else:
            md_lines.append("無")
            md_lines.append("")

        md_lines.extend([
            "## Section 5: 建議修復方案",
            "",
            f"**方案:** {proposed_fix.get('solution', '')}",
            f"**影響範圍:** {proposed_fix.get('impact_scope', '')}",
            f"**風險:** {proposed_fix.get('risk', '')}",
            f"**預期結果:** {proposed_fix.get('expected_result', '')}",
            "",
            "## Section 6: 分類",
            "",
        ])
        for cls in self.CLASSIFICATIONS:
            checked = "[x]" if cls == classification else "[ ]"
            md_lines.append(f"- {checked} {cls}")
        md_lines.append("")

        if verification:
            md_lines.extend([
                "## Section 7: 驗證結果",
                "",
                f"**修復版本:** {verification.get('fix_version', '')}",
                f"**測試用例:** {verification.get('test_case', '')}",
                f"**結果:** {verification.get('result', '')}",
                f"**證據:** {verification.get('evidence', '')}",
                "",
            ])

        md_lines.extend([
            "---",
            f"*本 Issue 由 skill_issue_reporter.py v{self.TEMPLATE_VERSION} 生成*",
            f"*驗證結果: {'全部通過' if all_pass else '有項目未通過'}*",
        ])

        markdown_content = "\n".join(md_lines)

        # 構建 JSON
        json_data = {
            "issue_template_version": self.TEMPLATE_VERSION,
            "classification": classification,
            "skill_name": skill_name,
            "skill_version": version,
            "generated_at": timestamp,
            "section_1_summary": {"skill_name": skill_name, "version": version, "description": summary},
            "section_2_reproduction": reproduction_steps,
            "section_3_root_cause": root_cause,
            "section_4_attempted_fixes": attempted_fixes if attempted_fixes else [],
            "section_5_proposed_fix": proposed_fix,
            "section_6_classification": classification,
            "section_7_verification": verification if verification else {},
            "validation_results": validations,
            "title": title,
        }

        # 解析 github_repository 提取 owner/repo
        owner, repo = "", ""
        if github_repo and "/" in github_repo:
            parts = github_repo.split("/", 1)
            owner, repo = parts[0], parts[1]

        # 上傳模式
        upload_result = None
        if upload and owner and repo:
            upload_result = self._create_github_issue(owner, repo, title, markdown_content)
        elif upload and (not owner or not repo):
            upload_result = {"status": "skipped", "reason": "SKILL.md 缺少 github_repository，無法上傳"}

        if dry_run:
            return {
                "status": "dry_run_passed",
                "validations": validations,
                "title": title,
                "skill_name": skill_name,
                "skill_version": version,
                "upload_preview": upload_result,
                "notice": "驗證通過，這是預覽模式。確認無誤後重新執行（dry_run=False）"
            }

        # 寫入本地文件
        safe_name = re.sub(r'[^\w\-]', '_', title)[:60]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        md_path = self.output_dir / f"ISSUE_{safe_name}_{ts}.md"
        json_path = self.output_dir / f"ISSUE_{safe_name}_{ts}.json"

        md_path.write_text(markdown_content, encoding="utf-8")
        json_path.write_text(
            json.dumps(json_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        result = {
            "status": "success",
            "title": title,
            "skill_name": skill_name,
            "skill_version": version,
            "markdown_path": str(md_path),
            "json_path": str(json_path),
            "validations": validations,
            "next_steps": [
                "1. 審查生成的 Markdown 內容",
                "2. 主人確認 [FRAMEWORK] 問題（如適用）",
            ]
        }

        if upload_result:
            result["upload_result"] = upload_result
            if upload_result.get("status") == "created":
                result["next_steps"].append(
                    f"3. Issue 已創建: #{upload_result['issue_number']} {upload_result['issue_url']}"
                )
                result["next_steps"].append(
                    f"4. 修復後 Commit 包含 Fixes #{upload_result['issue_number']} 自動關閉"
                )
            else:
                result["next_steps"].append(
                    f"3. [UPLOAD-FAILED] {upload_result.get('reason', '')}"
                )
                result["next_steps"].append(
                    "4. 手動在 GitHub 上創建 Issue（貼上 Markdown 內容）"
                )
        else:
            result["next_steps"].append("3. 在 GitHub 上創建 Issue（貼上 Markdown 內容）")
            result["next_steps"].append("4. 修復後 Commit 包含 Fixes #{issue_number} 自動關閉")

        return result

    def interactive_generate(self) -> Dict:
        print("=" * 60)
        print("Skill Issue Reporter - 交互式 Issue 生成")
        print("=" * 60)
        print(f"目標技能: {self._detect_skill_info()['name']}")
        print()

        print("[Section 1] 問題摘要（一句話描述，>=50中文字符）:")
        summary = input("> ").strip()

        auto_cls = self._auto_classify(summary, "")
        print(f"\n[自動分類推薦] {auto_cls}")
        print("請確認或修改:")
        for i, cls in enumerate(self.CLASSIFICATIONS, 1):
            print(f"  {i}. {cls}")
        cls_choice = input("> ").strip()
        try:
            classification = self.CLASSIFICATIONS[int(cls_choice) - 1]
        except (ValueError, IndexError):
            classification = auto_cls

        print("\n[Section 2] 復現步驟（至少2步，每步包含操作+參數+結果）")
        steps = []
        step_num = 1
        while True:
            print(f"\n步驟 {step_num}:")
            action = input("  操作: ").strip()
            if not action:
                break
            params = input("  參數: ").strip()
            result = input("  結果: ").strip()
            steps.append({"step": step_num, "action": action, "parameters": params, "result": result})
            step_num += 1
            if step_num > 2:
                more = input("  添加更多步驟? (y/n): ").strip().lower()
                if more != 'y':
                    break

        print("\n[Section 3] 根因分析")
        location = input("  位置（文件路徑+行號）: ").strip()
        phenomenon = input("  現象（觀察到的代碼邏輯）: ").strip()
        problem = input("  問題（邏輯錯誤點）: ").strip()
        consequence = input("  後果（導致的結果）: ").strip()
        root_cause = {"location": location, "phenomenon": phenomenon, "problem": problem, "consequence": consequence}

        print("\n[Section 4] 已嘗試的修復（無則直接回車）")
        attempted = []
        while True:
            method = input("  方法: ").strip()
            if not method:
                break
            result = input("  結果: ").strip()
            attempted.append({"method": method, "result": result})

        print("\n[Section 5] 建議修復方案")
        solution = input("  方案: ").strip()
        impact = input("  影響範圍: ").strip()
        risk = input("  風險（低/中/高）: ").strip()
        expected = input("  預期結果: ").strip()
        proposed_fix = {"solution": solution, "impact_scope": impact, "risk": risk, "expected_result": expected}

        return self.generate(
            classification=classification,
            summary=summary,
            reproduction_steps=steps,
            root_cause=root_cause,
            attempted_fixes=attempted,
            proposed_fix=proposed_fix
        )


def main():
    parser = argparse.ArgumentParser(description="Skill Issue Reporter - 標準 Issue 報告生成與上傳器")
    parser.add_argument("--skill-dir", required=True, help="技能目錄路徑（必須包含 SKILL.md）")
    parser.add_argument("--output-dir", default="./improve/issues", help="Issue 輸出目錄")
    parser.add_argument("--interactive", action="store_true", help="交互式模式")
    parser.add_argument("--dry-run", action="store_true", help="預覽模式：驗證輸入但不寫入文件")
    parser.add_argument("--upload", action="store_true", help="直接上傳到 GitHub Issues（需要 GITHUB_TOKEN）")
    parser.add_argument("--classification", help="[FRAMEWORK] / [RUNTIME] / [AGENT-BUG]")
    parser.add_argument("--summary", help="問題摘要")
    parser.add_argument("--repro-json", help="復現步驟 JSON 文件路徑")
    parser.add_argument("--root-cause-json", help="根因分析 JSON 文件路徑")
    parser.add_argument("--proposed-fix-json", help="建議修復 JSON 文件路徑")
    parser.add_argument("--attempted-json", help="已嘗試修復 JSON 文件路徑（可選）")
    parser.add_argument("--verification-json", help="驗證結果 JSON 文件路徑（可選）")
    parser.add_argument("--from-stdin", action="store_true", help="從 stdin 讀取完整 JSON 輸入（Agent 推薦方式）")

    args = parser.parse_args()
    reporter = SkillIssueReporter(skill_dir=args.skill_dir, output_dir=args.output_dir)

    if args.interactive:
        result = reporter.interactive_generate()
    elif args.from_stdin:
        import sys
        input_data = json.load(sys.stdin)
        result = reporter.generate(
            classification=input_data.get("classification", "[RUNTIME]"),
            summary=input_data.get("summary", ""),
            reproduction_steps=input_data.get("reproduction_steps", []),
            root_cause=input_data.get("root_cause", {}),
            attempted_fixes=input_data.get("attempted_fixes", []),
            proposed_fix=input_data.get("proposed_fix", {}),
            verification=input_data.get("verification"),
            dry_run=args.dry_run,
            upload=args.upload
        )
    elif args.classification and args.summary:
        repro = []
        if args.repro_json:
            with open(args.repro_json, "r", encoding="utf-8") as f:
                repro = json.load(f)
        root_cause = {}
        if args.root_cause_json:
            with open(args.root_cause_json, "r", encoding="utf-8") as f:
                root_cause = json.load(f)
        proposed = {}
        if args.proposed_fix_json:
            with open(args.proposed_fix_json, "r", encoding="utf-8") as f:
                proposed = json.load(f)
        attempted = []
        if args.attempted_json:
            with open(args.attempted_json, "r", encoding="utf-8") as f:
                attempted = json.load(f)
        verification = None
        if args.verification_json:
            with open(args.verification_json, "r", encoding="utf-8") as f:
                verification = json.load(f)

        result = reporter.generate(
            classification=args.classification,
            summary=args.summary,
            reproduction_steps=repro,
            root_cause=root_cause,
            attempted_fixes=attempted,
            proposed_fix=proposed,
            verification=verification,
            dry_run=args.dry_run,
            upload=args.upload
        )
    else:
        print("[REPORTER] 錯誤: 必須指定 --interactive, --from-stdin, 或 --classification + --summary")
        sys.exit(1)

    print(f"\n[REPORTER] 狀態: {result['status']}")
    if result['status'] == 'success':
        print(f"  標題: {result['title']}")
        print(f"  Markdown: {result['markdown_path']}")
        print(f"  JSON: {result['json_path']}")
        if result.get('upload_result'):
            ur = result['upload_result']
            if ur.get('status') == 'created':
                print(f"  Issue: #{ur['issue_number']} {ur['issue_url']}")
            else:
                print(f"  [UPLOAD-FAILED] {ur.get('reason', '')}")
        for step in result.get('next_steps', []):
            print(f"  {step}")
    elif result['status'] == 'dry_run_passed':
        print(f"  標題: {result['title']}")
        print(f"  驗證: 全部通過")
        if result.get('upload_preview'):
            print(f"  上傳預覽: {result['upload_preview']}")
        print(f"  {result['notice']}")
    else:
        print(f"  原因: {result.get('reason', '未知')}")
        if 'validations' in result:
            for v in result['validations']:
                status = "✅" if v['ok'] else "❌"
                print(f"    {status} {v['msg']}")
        if 'notice' in result:
            print(f"  提示: {result['notice']}")


if __name__ == "__main__":
    main()
