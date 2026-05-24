'''
---
title: "Skill Issue Reporter - Standard Issue Report Generator"
name: github-skill-organizer
description: "Mandatory standard Issue report generator per CONTRIBUTING.md v1.2.5. Interactive collection, auto-classification, word count validation, dual Markdown+JSON output. v1.3.1 adds --create-issue via github-restful-api-connector interface isolation."
version: "1.3.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-24T01:45:00+08:00"
fixes: []
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"
file_mapping:
  local_path: "scripts/skill_issue_reporter.py"
  github_path: "github-skill-organizer/scripts/skill_issue_reporter.py"
---
'''

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

class SkillIssueReporter:
    # LOCK v1.2.5: Standard Issue Report Generator
    # Core Principles:
    #   1. Agent MUST NOT freestyle Issue writing. Use this script.
    #   2. Any LLM calling this script produces identical output.
    #   3. Auto-classify [FRAMEWORK] / [RUNTIME] / [AGENT-BUG]
    #   4. Force validate each Section >= 50 Chinese chars
    #   5. Output Markdown + JSON dual format
    #   6. v1.3.1: Create GitHub Issue via github-restful-api-connector
    #      (interface isolation: organizer decides, connector transmits)

    CLASSIFICATIONS = ["[FRAMEWORK]", "[RUNTIME]", "[AGENT-BUG]"]
    MIN_CHINESE_CHARS = 50
    MIN_ENGLISH_CHARS = 100
    MAX_TITLE_LEN = 256
    TEMPLATE_VERSION = "v1.2.5"
    CONNECTOR_PATH = "~/.workbuddy/skills/github-restful-api-connector/scripts/github_restful_core.py"

    def __init__(self, skill_dir: str, output_dir: str = "./improve/issues"):
        self.skill_dir = Path(os.path.expanduser(str(skill_dir))).resolve()
        self.output_dir = Path(os.path.expanduser(str(output_dir)))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._validate_skill_dir()

    def _validate_skill_dir(self) -> None:
        if not self.skill_dir.exists():
            raise FileNotFoundError(f"[REPORTER] Skill dir missing: {self.skill_dir}")
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"[REPORTER] SKILL.md missing: {skill_md}")

    def _detect_skill_info(self) -> Dict:
        # Extract name and version from SKILL.md frontmatter
        skill_md = self.skill_dir / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        info = {"name": self.skill_dir.name, "version": "unknown"}
        for line in content.splitlines()[:30]:
            stripped = line.strip()
            if stripped.startswith("name:"):
                val = stripped.split(":", 1)[1].strip().strip(chr(34)).strip(chr(39))
                if val:
                    info["name"] = val
            elif stripped.startswith("version:"):
                val = stripped.split(":", 1)[1].strip().strip(chr(34)).strip(chr(39))
                if val:
                    info["version"] = val
        return info

    def _read_skill_frontmatter(self) -> Dict:
        # Read full frontmatter from SKILL.md
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            return {}
        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return {}
        end = content.find("---", 3)
        if end == -1:
            return {}
        fm_text = content[3:end].strip()
        result = {}
        for line in fm_text.splitlines():
            if ":" in line and not line.strip().startswith("#"):
                key, val = line.split(":", 1)
                result[key.strip()] = val.strip().strip(chr(34)).strip(chr(39))
        return result

    def _resolve_github_config(
        self,
        owner: Optional[str],
        repo: Optional[str],
        token: Optional[str]
    ) -> Tuple[str, str, str]:
        # Resolve GitHub config from CLI args -> env -> .env -> frontmatter
        #
        # Priority order for TOKEN:
        #   1. --github-token CLI arg
        #   2. GITHUB_TOKEN environment variable
        #   3. .env file (skill_dir/.env or organizer/.env)
        #
        # Priority order for OWNER/REPO:
        #   1. --github-owner / --github-repo CLI args
        #   2. SKILL.md frontmatter github_repository field
        #   3. .env file GITHUB_OWNER / GITHUB_REPO
        resolved_token = token or os.getenv("GITHUB_TOKEN", "")
        if not resolved_token:
            for env_candidate in [
                self.skill_dir / ".env",
                Path(os.path.expanduser("~/.workbuddy/skills/github-skill-organizer/.env"))
            ]:
                if env_candidate.exists():
                    for line in env_candidate.read_text(encoding="utf-8").splitlines():
                        if line.startswith("GITHUB_TOKEN="):
                            resolved_token = line.split("=", 1)[1].strip().strip(chr(34)).strip(chr(39))
                            break
                if resolved_token:
                    break

        resolved_owner = owner or ""
        resolved_repo = repo or ""

        if not resolved_owner or not resolved_repo:
            fm = self._read_skill_frontmatter()
            gh_repo = fm.get("github_repository", "")
            if gh_repo and "/" in gh_repo:
                parts = gh_repo.split("/")
                if len(parts) == 2:
                    resolved_owner = resolved_owner or parts[0]
                    resolved_repo = resolved_repo or parts[1]

        if not resolved_owner or not resolved_repo:
            for env_candidate in [
                self.skill_dir / ".env",
                Path(os.path.expanduser("~/.workbuddy/skills/github-skill-organizer/.env"))
            ]:
                if env_candidate.exists():
                    for line in env_candidate.read_text(encoding="utf-8").splitlines():
                        if line.startswith("GITHUB_OWNER=") and not resolved_owner:
                            resolved_owner = line.split("=", 1)[1].strip().strip(chr(34)).strip(chr(39))
                        elif line.startswith("GITHUB_REPO=") and not resolved_repo:
                            resolved_repo = line.split("=", 1)[1].strip().strip(chr(34)).strip(chr(39))
                if resolved_owner and resolved_repo:
                    break

        return resolved_owner, resolved_repo, resolved_token

    def _count_chinese_chars(self, text: str) -> int:
        return len(re.findall(r"[\u4e00-\u9fff]", text))

    def _count_total_chars(self, text: str) -> int:
        return len(text.replace(" ", "").replace("\n", "").replace("\t", ""))

    def _validate_section_length(self, text: str, section_name: str) -> Tuple[bool, str]:
        chinese = self._count_chinese_chars(text)
        total = self._count_total_chars(text)
        if chinese >= self.MIN_CHINESE_CHARS:
            return True, f"[OK] {section_name}: {chinese} Chinese chars"
        if total >= self.MIN_ENGLISH_CHARS:
            return True, f"[OK] {section_name}: {total} chars (English)"
        return False, (
            f"[REJECTED] {section_name}: only {chinese} Chinese / {total} total. "
            f"Require >= {self.MIN_CHINESE_CHARS} Chinese or >= {self.MIN_ENGLISH_CHARS} total"
        )

    def _auto_classify(self, problem_desc: str, location: str) -> str:
        desc_lower = problem_desc.lower()
        loc_lower = location.lower()
        framework_kw = [
            "架构", "framework", "规范", "制度", "semantic-release",
            "配置", "决策", "原则", "身份证", "frontmatter", "目录结构"
        ]
        agentbug_kw = [
            "agent 生成", "agent 输出", "agent 违反", "缺少 frontmatter",
            "没有身份证", "命名错误", "路径错误", "擅自", "未经确认"
        ]
        for kw in framework_kw:
            if kw in desc_lower or kw in loc_lower:
                return "[FRAMEWORK]"
        for kw in agentbug_kw:
            if kw in desc_lower or kw in loc_lower:
                return "[AGENT-BUG]"
        return "[RUNTIME]"

    def _build_issue_body(
        self,
        markdown_content: str,
        json_data: Dict,
        attach_body: bool,
        attach_json: bool
    ) -> str:
        # Build GitHub Issue body with optional Markdown + JSON attachments
        parts = []
        if attach_body:
            parts.append(markdown_content)
        if attach_json:
            json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
            parts.append("\n\n<details>\n<summary>Structured Data (JSON)</summary>\n\n```json\n" + json_str + "\n```\n\n</details>")
        return "\n".join(parts)

    def _create_github_issue_via_connector(
        self,
        title: str,
        body: str,
        owner: str,
        repo: str,
        token: str
    ) -> Dict:
        # Create GitHub Issue via github-restful-api-connector.
        #
        # GitHub REST API Create Issue endpoint:
        #   POST /repos/{owner}/{repo}/issues
        #   Payload: {"title": "...", "body": "...", "labels": [...]}
        #
        # Success response (HTTP 201):
        #   Returns Issue object. MUST contain:
        #     - number: int (Issue number, e.g. 1347)
        #     - html_url: str (Issue URL, e.g. https://github.com/owner/repo/issues/1347)
        #     - id: int, state: str, title: str, body: str, created_at: str, etc.
        #
        # Error response (HTTP 401/403/404/422):
        #   Returns error object. MUST contain:
        #     - message: str (e.g. "Bad credentials", "Validation Failed")
        #     - documentation_url: str (optional)
        #     - errors: list (optional, for 422 validation errors)
        #
        # Connector rest_request() signature:
        #   rest_request(method: str, endpoint: str, payload: dict = None) -> dict
        #   - Returns response.json() directly (raw GitHub API response, no wrapper)
        #   - NO headers parameter (connector handles auth internally via load_env/get_session)
        #   - NO json_data parameter (use payload)
        #   - On HTTP error: may raise exception OR return error dict with "message"
        try:
            import importlib.util
            connector_path = Path(os.path.expanduser(self.CONNECTOR_PATH))
            if not connector_path.exists():
                return {
                    "status": "error",
                    "reason": "[CONNECTOR-NOT-FOUND] github-restful-api-connector not installed. "
                              "Install at ~/.workbuddy/skills/github-restful-api-connector/"
                }

            spec = importlib.util.spec_from_file_location(
                "github_restful_core", str(connector_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "rest_request"):
                return {
                    "status": "error",
                    "reason": "[CONNECTOR-API-MISSING] github_restful_core.py missing rest_request()"
                }

            # Pass token via env for connector to pick up
            if token:
                os.environ["GITHUB_TOKEN"] = token
            if hasattr(module, "load_env"):
                module.load_env()

            # Call connector: rest_request(method, endpoint, payload)
            result = module.rest_request(
                method="POST",
                endpoint="/repos/" + owner + "/" + repo + "/issues",
                payload={"title": title, "body": body}
            )

            # GitHub API error check: response contains "message" field
            if isinstance(result, dict) and "message" in result:
                return {
                    "status": "error",
                    "reason": "[GITHUB-API-ERROR] " + str(result.get("message", "Unknown error"))
                }

            # GitHub API success check: response contains "number" (int) and "html_url" (str)
            if isinstance(result, dict) and isinstance(result.get("number"), int):
                return {
                    "status": "created",
                    "issue_url": result.get("html_url", ""),
                    "issue_number": result.get("number", 0),
                    "title": title
                }

            # Unexpected format
            return {
                "status": "error",
                "reason": "[GITHUB-API-ERROR] Unexpected response: " + str(result)[:200]
            }

        except Exception as e:
            return {
                "status": "error",
                "reason": "[CONNECTOR-ERROR] " + str(e)
            }

    def generate(
        self,
        classification: str,
        summary: str,
        reproduction_steps: List[Dict],
        root_cause: Dict,
        attempted_fixes: List[Dict],
        proposed_fix: Dict,
        verification: Optional[Dict] = None,
        file_name: str = "",
        method_name: str = "",
        dry_run: bool = False,
        # v1.3.1: GitHub Issue creation params
        create_issue: bool = False,
        github_owner: str = "",
        github_repo: str = "",
        github_token: str = "",
        attach_body: bool = True,
        attach_json: bool = False,
        dry_run_create: bool = False
    ) -> Dict:
        # Generate standard Issue report. Optionally create GitHub Issue via connector.

        if classification not in self.CLASSIFICATIONS:
            return {
                "status": "rejected",
                "reason": "[INVALID] Classification must be " + str(self.CLASSIFICATIONS) + ", got: " + classification
            }

        skill_info = self._detect_skill_info()
        skill_name = skill_info["name"]
        version = skill_info["version"]

        validations = []
        all_pass = True

        full_summary = classification + " " + skill_name + " " + version + " - " + summary
        ok, msg = self._validate_section_length(full_summary, "Section 1 Summary")
        validations.append({"section": "1", "ok": ok, "msg": msg})
        if not ok:
            all_pass = False

        repro_text = "\n".join([
            str(s["step"]) + ". Action: " + s.get("action", "") + " Params: " + s.get("parameters", "") + " Result: " + s.get("result", "")
            for s in reproduction_steps
        ])
        ok, msg = self._validate_section_length(repro_text, "Section 2 Reproduction")
        validations.append({"section": "2", "ok": ok, "msg": msg})
        if not ok:
            all_pass = False

        rc_text = (
            "Location: " + root_cause.get("location", "") + " "
            + "Phenomenon: " + root_cause.get("phenomenon", "") + " "
            + "Problem: " + root_cause.get("problem", "") + " "
            + "Consequence: " + root_cause.get("consequence", "")
        )
        ok, msg = self._validate_section_length(rc_text, "Section 3 Root Cause")
        validations.append({"section": "3", "ok": ok, "msg": msg})
        if not ok:
            all_pass = False

        pf_text = (
            "Solution: " + proposed_fix.get("solution", "") + " "
            + "Impact: " + proposed_fix.get("impact_scope", "") + " "
            + "Risk: " + proposed_fix.get("risk", "") + " "
            + "Expected: " + proposed_fix.get("expected_result", "")
        )
        ok, msg = self._validate_section_length(pf_text, "Section 5 Proposed Fix")
        validations.append({"section": "5", "ok": ok, "msg": msg})
        if not ok:
            all_pass = False

        if not all_pass:
            return {
                "status": "rejected",
                "reason": "[VALIDATION-FAILED] Some sections too short. Expand content.",
                "validations": validations,
                "notice": "Expand the [REJECTED] sections and retry."
            }

        priority_str = classification.ljust(10)
        skill_str = skill_name.ljust(40)
        file_str = file_name.ljust(40) if file_name else "".ljust(40)
        method_str = method_name + " - " if method_name else ""
        title = ("[" + priority_str + "] [" + skill_str + "] [" + file_str + "] " + method_str + summary)[:self.MAX_TITLE_LEN]

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        md_lines = [
            "<!-- Issue Template Version: " + self.TEMPLATE_VERSION + " -->",
            "<!-- Generated by: skill_issue_reporter.py -->",
            "<!-- Timestamp: " + timestamp + " -->",
            "",
            "# " + title,
            "",
            "## Section 1: Summary",
            "",
            full_summary,
            "",
            "## Section 2: Reproduction Steps",
            "",
        ]
        for step in reproduction_steps:
            md_lines.append(str(step["step"]) + ". Action: " + step.get("action", ""))
            md_lines.append("   Parameters: " + step.get("parameters", ""))
            md_lines.append("   Result: " + step.get("result", ""))
            md_lines.append("")

        md_lines.extend([
            "## Section 3: Root Cause Analysis",
            "",
            "**Location:** " + root_cause.get("location", ""),
            "**Phenomenon:** " + root_cause.get("phenomenon", ""),
            "**Problem:** " + root_cause.get("problem", ""),
            "**Consequence:** " + root_cause.get("consequence", ""),
            "",
            "## Section 4: Attempted Fixes",
            "",
        ])
        if attempted_fixes:
            for i, af in enumerate(attempted_fixes, 1):
                md_lines.append("Attempt " + str(i) + ":")
                md_lines.append("  Method: " + af.get("method", "None"))
                md_lines.append("  Result: " + af.get("result", "None"))
                md_lines.append("")
        else:
            md_lines.append("None")
            md_lines.append("")

        md_lines.extend([
            "## Section 5: Proposed Fix",
            "",
            "**Solution:** " + proposed_fix.get("solution", ""),
            "**Impact Scope:** " + proposed_fix.get("impact_scope", ""),
            "**Risk:** " + proposed_fix.get("risk", ""),
            "**Expected Result:** " + proposed_fix.get("expected_result", ""),
            "",
            "## Section 6: Classification",
            "",
        ])
        for cls in self.CLASSIFICATIONS:
            checked = "[x]" if cls == classification else "[ ]"
            md_lines.append("- " + checked + " " + cls)
        md_lines.append("")

        if verification:
            md_lines.extend([
                "## Section 7: Verification",
                "",
                "**Fix Version:** " + verification.get("fix_version", ""),
                "**Test Case:** " + verification.get("test_case", ""),
                "**Result:** " + verification.get("result", ""),
                "**Evidence:** " + verification.get("evidence", ""),
                "",
            ])

        md_lines.extend([
            "---",
            "*Generated by skill_issue_reporter.py " + self.TEMPLATE_VERSION + "*",
            "*Validation: " + ("All passed" if all_pass else "Some failed") + "*",
        ])

        markdown_content = "\n".join(md_lines)

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

        if dry_run:
            return {
                "status": "dry_run_passed",
                "validations": validations,
                "title": title,
                "skill_name": skill_name,
                "skill_version": version,
                "notice": "Validation passed. Preview mode. Re-run with dry_run=False to write files."
            }

        safe_name = re.sub(r"[^\w\-]", "_", title)[:60]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        md_path = self.output_dir / ("ISSUE_" + safe_name + "_" + ts + ".md")
        json_path = self.output_dir / ("ISSUE_" + safe_name + "_" + ts + ".json")

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
                "1. Review generated Markdown",
                "2. Owner confirms [FRAMEWORK] issues if applicable",
                "3. Create GitHub Issue (paste Markdown or use --create-issue)",
                "4. After fix, commit with Fixes #{issue_number} to auto-close"
            ]
        }

        # v1.3.1: Optional GitHub Issue creation via connector
        if create_issue:
            owner, repo, token = self._resolve_github_config(github_owner, github_repo, github_token)

            if not token:
                result["github_issue"] = {
                    "status": "error",
                    "reason": "[TOKEN-MISSING] GITHUB_TOKEN not found. Provide via --github-token, GITHUB_TOKEN env, or .env file. "
                              "Required scope: repo (read/write Issues). Without token: API returns 401 Unauthorized."
                }
            elif not owner or not repo:
                result["github_issue"] = {
                    "status": "error",
                    "reason": "[REPO-MISSING] github_owner/repo not found. Provide via --github-owner/--github-repo, frontmatter, or .env file"
                }
            else:
                issue_body = self._build_issue_body(markdown_content, json_data, attach_body, attach_json)
                if dry_run_create:
                    result["github_issue"] = {
                        "status": "dry_run",
                        "title": title,
                        "body_preview": (issue_body[:500] + "...") if len(issue_body) > 500 else issue_body,
                        "owner": owner,
                        "repo": repo
                    }
                else:
                    issue_result = self._create_github_issue_via_connector(title, issue_body, owner, repo, token)
                    result["github_issue"] = issue_result
                    if issue_result.get("status") == "created":
                        result["next_steps"].append("5. GitHub Issue created: " + issue_result.get("issue_url", ""))

        return result

    def interactive_generate(self) -> Dict:
        print("=" * 60)
        print("Skill Issue Reporter - Interactive Issue Generation")
        print("=" * 60)
        print("Target skill: " + self._detect_skill_info()["name"])
        print()
        print("[Section 1] Summary (one sentence, >=50 Chinese chars):")
        summary = input("> ").strip()

        auto_cls = self._auto_classify(summary, "")
        print("\n[Auto-classify] " + auto_cls)
        print("Confirm or modify:")
        for i, cls in enumerate(self.CLASSIFICATIONS, 1):
            print("  " + str(i) + ". " + cls)
        cls_choice = input("> ").strip()
        try:
            classification = self.CLASSIFICATIONS[int(cls_choice) - 1]
        except (ValueError, IndexError):
            classification = auto_cls

        print("\n[Section 2] Reproduction (min 2 steps, each: action+params+result)")
        steps = []
        step_num = 1
        while True:
            print("\nStep " + str(step_num) + ":")
            action = input("  Action: ").strip()
            if not action:
                break
            params = input("  Parameters: ").strip()
            result = input("  Result: ").strip()
            steps.append({"step": step_num, "action": action, "parameters": params, "result": result})
            step_num += 1
            if step_num > 2:
                more = input("  Add more? (y/n): ").strip().lower()
                if more != "y":
                    break

        print("\n[Section 3] Root Cause Analysis")
        location = input("  Location (file+line): ").strip()
        phenomenon = input("  Phenomenon (observed logic): ").strip()
        problem = input("  Problem (logic error): ").strip()
        consequence = input("  Consequence (result): ").strip()
        root_cause = {
            "location": location,
            "phenomenon": phenomenon,
            "problem": problem,
            "consequence": consequence
        }

        print("\n[Section 4] Attempted Fixes (Enter=skip)")
        attempted = []
        while True:
            method = input("  Method: ").strip()
            if not method:
                break
            result = input("  Result: ").strip()
            attempted.append({"method": method, "result": result})

        print("\n[Section 5] Proposed Fix")
        solution = input("  Solution: ").strip()
        impact = input("  Impact scope: ").strip()
        risk = input("  Risk (low/medium/high): ").strip()
        expected = input("  Expected result: ").strip()
        proposed_fix = {
            "solution": solution,
            "impact_scope": impact,
            "risk": risk,
            "expected_result": expected
        }

        return self.generate(
            classification=classification,
            summary=summary,
            reproduction_steps=steps,
            root_cause=root_cause,
            attempted_fixes=attempted,
            proposed_fix=proposed_fix
        )

def main():
    parser = argparse.ArgumentParser(
        description="Skill Issue Reporter - Standard Issue Report Generator"
    )
    parser.add_argument("--skill-dir", required=True, help="Skill directory path (must contain SKILL.md)")
    parser.add_argument("--output-dir", default="./improve/issues", help="Issue output directory")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--dry-run", action="store_true", help="Preview mode: validate input without writing files")
    parser.add_argument("--classification", help="[FRAMEWORK] / [RUNTIME] / [AGENT-BUG]")
    parser.add_argument("--summary", help="Problem summary")
    parser.add_argument("--repro-json", help="Reproduction steps JSON file path")
    parser.add_argument("--root-cause-json", help="Root cause JSON file path")
    parser.add_argument("--proposed-fix-json", help="Proposed fix JSON file path")
    parser.add_argument("--attempted-json", help="Attempted fixes JSON file path (optional)")
    parser.add_argument("--verification-json", help="Verification JSON file path (optional)")
    parser.add_argument("--from-stdin", action="store_true", help="Read full JSON input from stdin (Agent recommended)")

    # v1.3.1: GitHub Issue creation params
    parser.add_argument("--create-issue", action="store_true",
                        help="Create GitHub Issue via github-restful-api-connector (interface isolation)")
    parser.add_argument("--github-owner", help="GitHub repository owner (fallback: .env / frontmatter)")
    parser.add_argument("--github-repo", help="GitHub repository name (fallback: .env / frontmatter)")
    parser.add_argument("--github-token",
                        help="GitHub Personal Access Token (fallback: GITHUB_TOKEN env / .env).")
    parser.add_argument("--attach-body", action="store_true", default=True,
                        help="Attach Markdown content to Issue body (default: True)")
    parser.add_argument("--attach-json", action="store_true",
                        help="Attach JSON data as collapsible <details> block in Issue body")
    parser.add_argument("--dry-run-create", action="store_true",
                        help="Preview Issue content for GitHub without creating (validate connector config)")

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
            file_name=input_data.get("file_name", ""),
            method_name=input_data.get("method_name", ""),
            dry_run=args.dry_run,
            create_issue=input_data.get("create_issue", args.create_issue),
            github_owner=input_data.get("github_owner", args.github_owner),
            github_repo=input_data.get("github_repo", args.github_repo),
            github_token=input_data.get("github_token", args.github_token),
            attach_body=input_data.get("attach_body", args.attach_body),
            attach_json=input_data.get("attach_json", args.attach_json),
            dry_run_create=input_data.get("dry_run_create", args.dry_run_create)
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
            create_issue=args.create_issue,
            github_owner=args.github_owner,
            github_repo=args.github_repo,
            github_token=args.github_token,
            attach_body=args.attach_body,
            attach_json=args.attach_json,
            dry_run_create=args.dry_run_create
        )
    else:
        print("[REPORTER] ERROR: Must specify --interactive, --from-stdin, or --classification + --summary")
        sys.exit(1)

    print("\n[REPORTER] Status: " + result["status"])
    if result['status'] == 'success':
        print("  Title: " + result["title"])
        print("  Markdown: " + result["markdown_path"])
        print("  JSON: " + result["json_path"])
        if "github_issue" in result:
            gh = result["github_issue"]
            print("  GitHub Issue: " + gh.get("status", "N/A"))
            if gh.get("status") == "created":
                print("    URL: " + gh.get("issue_url", ""))
                print("    Number: #" + str(gh.get("issue_number", 0)))
            elif gh.get("status") == "error":
                print("    ERROR: " + gh.get("reason", "Unknown"))
            elif gh.get("status") == "dry_run":
                print("    PREVIEW: " + gh.get("body_preview", "")[:200] + "...")
        for step in result.get("next_steps", []):
            print("  " + step)
    elif result['status'] == 'dry_run_passed':
        print("  Title: " + result["title"])
        print("  Validation: All passed")
        print("  " + result["notice"])
    else:
        print("  Reason: " + result.get("reason", "Unknown"))
        if "validations" in result:
            for v in result['validations']:
                status = "OK" if v["ok"] else "FAIL"
                print("    " + status + " " + v["msg"])
        if "notice" in result:
            print("  Hint: " + result["notice"])


if __name__ == "__main__":
    main()