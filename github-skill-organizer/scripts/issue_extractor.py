"""
---
title: Issue Extractor
name: github-skill-organizer
description: Scans local skill files, extracts frontmatter fixes fields, cross-references against GitHub issue lists (from repo_issue_finder), detects stale/pending/orphan fixes, and matches issue descriptions to local skill names, filenames, and function names. v1.0.0 refactored to use core modules.
version: "1.2.0"
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: "2026-05-24T09:22:14+08:00"
fixes: []
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: scripts/issue_extractor.py
  github_path: github-skill-organizer/scripts/issue_extractor.py
---
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    from core_frontmatter import FrontmatterExtractor
    from core_path_utils import normalize_path
    from core_logger import log
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from core_frontmatter import FrontmatterExtractor
    from core_path_utils import normalize_path
    from core_logger import log


class IssueExtractor:
    """
    Issue Extractor v1.0.0
    Single responsibility: Analyze local skill files against a given issue list.
    No GitHub API calls. No remote operations.
    Input: issue list (from repo_issue_finder or JSON file) + local skills directory.
    Output: structured cross-reference report.
    """

    def __init__(self, skills_base_dir: str = None):
        if skills_base_dir:
            self.skills_base_dir = normalize_path(skills_base_dir)
        else:
            self.skills_base_dir = normalize_path(Path.home() / ".workbuddy" / "skills")
        self.skills_base_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # F002: Scan Local Skills & Extract Fixes
    # ============================================================

    def scan_local_skills(self) -> Dict[str, Dict]:
        results = {}
        if not self.skills_base_dir.exists():
            log("ISSUE_EXTRACTOR", "Skills base dir not found: {}".format(self.skills_base_dir), "ERROR")
            return results

        for skill_dir in self.skills_base_dir.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            skill_name = skill_dir.name
            for file_path in skill_dir.rglob("*"):
                if not file_path.is_file() or file_path.name.startswith("."):
                    continue
                if file_path.suffix not in [".md", ".py", ".json", ".html", ".env", ".yaml", ".yml"]:
                    continue
                fm = FrontmatterExtractor.extract(file_path)
                fixes = FrontmatterExtractor.extract_fixes(fm)
                if fm or fixes:
                    rel_path = str(file_path.relative_to(self.skills_base_dir))
                    results[rel_path] = {
                        "absolute_path": str(file_path),
                        "skill_name": skill_name,
                        "filename": file_path.name,
                        "frontmatter": fm,
                        "fixes": fixes,
                        "content_preview": self._get_content_preview(file_path),
                    }
        log("ISSUE_EXTRACTOR", "Scanned {} files with frontmatter/fixes".format(len(results)))
        return results

    def _get_content_preview(self, file_path: Path, max_lines: int = 50) -> str:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()[:max_lines]
            return "\n".join(lines)
        except Exception:
            return ""

    # ============================================================
    # F003: Fixes Matching (Stale / Pending / Orphan)
    # ============================================================

    def match_fixes(self, issues: List[Dict], local_files: Dict[str, Dict]) -> Dict:
        issue_by_number = {i["number"]: i for i in issues}
        all_local_fixes = set()
        file_fixes_map = {}
        for rel_path, info in local_files.items():
            for fix_num in info["fixes"]:
                all_local_fixes.add(fix_num)
                if fix_num not in file_fixes_map:
                    file_fixes_map[fix_num] = []
                file_fixes_map[fix_num].append({
                    "file": rel_path,
                    "skill_name": info["skill_name"],
                    "filename": info["filename"],
                })
        stale_fixes = []
        pending_fixes = []
        orphan_issues = []
        for fix_num in sorted(all_local_fixes):
            issue = issue_by_number.get(fix_num)
            if issue is None:
                stale_fixes.append({
                    "issue_number": fix_num,
                    "issue_state": "not_found",
                    "files": file_fixes_map.get(fix_num, []),
                    "reason": "Issue not found on GitHub. May have been deleted or number is incorrect.",
                })
                continue
            if issue["state"] == "closed":
                stale_fixes.append({
                    "issue_number": fix_num,
                    "issue_state": "closed",
                    "issue_title": issue["title"],
                    "issue_html_url": issue["html_url"],
                    "files": file_fixes_map.get(fix_num, []),
                    "closed_at": issue["closed_at"],
                    "reason": "Issue #{} is closed but still referenced in file frontmatter.".format(fix_num),
                })
            else:
                pending_fixes.append({
                    "issue_number": fix_num,
                    "issue_state": "open",
                    "issue_title": issue["title"],
                    "issue_html_url": issue["html_url"],
                    "files": file_fixes_map.get(fix_num, []),
                    "reason": "Issue #{} is open and referenced in file frontmatter.".format(fix_num),
                })
        issue_numbers_in_files = all_local_fixes
        for issue in issues:
            if issue["number"] not in issue_numbers_in_files:
                orphan_issues.append({
                    "issue_number": issue["number"],
                    "issue_state": issue["state"],
                    "issue_title": issue["title"],
                    "issue_html_url": issue["html_url"],
                    "labels": issue["labels"],
                    "reason": "Issue #{} exists but no local skill file references it in fixes field.".format(issue["number"]),
                })
        return {
            "stale_fixes": stale_fixes,
            "pending_fixes": pending_fixes,
            "orphan_issues": orphan_issues,
            "summary": {
                "total_issues_checked": len(issues),
                "total_files_scanned": len(local_files),
                "total_fix_references": len(all_local_fixes),
                "stale_count": len(stale_fixes),
                "pending_count": len(pending_fixes),
                "orphan_count": len(orphan_issues),
            }
        }

    # ============================================================
    # F004: Description Matching (Skill / File / Function)
    # ============================================================

    def match_descriptions(
        self,
        issues: List[Dict],
        local_files: Dict[str, Dict],
        query_skill_name: str = None,
        query_filename: str = None,
        query_function: str = None,
    ) -> List[Dict]:
        matches = []
        for issue in issues:
            title_lower = issue["title"].lower()
            body_lower = issue["body"].lower()
            combined = title_lower + " " + body_lower
            match_info = {
                "issue_number": issue["number"],
                "issue_title": issue["title"],
                "issue_state": issue["state"],
                "issue_html_url": issue["html_url"],
                "matched_skills": [],
                "matched_files": [],
                "matched_functions": [],
                "relevance_score": 0,
                "match_reasons": [],
            }
            for rel_path, info in local_files.items():
                skill_name = info["skill_name"]
                if skill_name.lower() in combined:
                    if skill_name not in [m["skill_name"] for m in match_info["matched_skills"]]:
                        match_info["matched_skills"].append({"skill_name": skill_name, "files_in_skill": []})
                    match_info["relevance_score"] += 10
                    match_info["match_reasons"].append("Skill name '{}' found in issue".format(skill_name))
            for rel_path, info in local_files.items():
                filename = info["filename"]
                if filename.lower() in combined:
                    match_info["matched_files"].append({"filename": filename, "skill_name": info["skill_name"], "relative_path": rel_path})
                    match_info["relevance_score"] += 15
                    match_info["match_reasons"].append("Filename '{}' found in issue".format(filename))
            if query_function:
                func_pattern = re.compile(r"\b" + re.escape(query_function.lower()) + r"\b")
                if func_pattern.search(combined):
                    match_info["matched_functions"].append({"function_name": query_function, "found_in": "issue_title_or_body"})
                    match_info["relevance_score"] += 20
                    match_info["match_reasons"].append("Function '{}' found in issue".format(query_function))
            for rel_path, info in local_files.items():
                if info["filename"].endswith(".py"):
                    funcs = self._extract_function_names(info.get("content_preview", ""))
                    for func in funcs:
                        if func.lower() in combined and len(func) > 3:
                            if func not in [m["function_name"] for m in match_info["matched_functions"]]:
                                match_info["matched_functions"].append({"function_name": func, "found_in": "local_file:{}".format(rel_path)})
                                match_info["relevance_score"] += 12
                                match_info["match_reasons"].append("Function '{}' from {} mentioned in issue".format(func, rel_path))
            if query_skill_name:
                if not any(m["skill_name"] == query_skill_name for m in match_info["matched_skills"]):
                    continue
            if query_filename:
                if not any(m["filename"] == query_filename for m in match_info["matched_files"]):
                    continue
            if query_function:
                if not any(m["function_name"] == query_function for m in match_info["matched_functions"]):
                    continue
            if match_info["relevance_score"] > 0:
                matches.append(match_info)
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matches

    def _extract_function_names(self, content: str) -> List[str]:
        pattern = re.compile(r"^\s*def\s+(\w+)\s*\(", re.MULTILINE)
        return pattern.findall(content)

    # ============================================================
    # F005: Report Generation
    # ============================================================

    def generate_report(
        self,
        fixes_result: Dict,
        matches: List[Dict] = None,
        output_path: str = None,
    ) -> Dict:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tool_version": "1.0.0",
            "skills_base_dir": str(self.skills_base_dir),
            "fixes_analysis": fixes_result,
            "description_matches": matches or [],
            "recommendations": self._generate_recommendations(fixes_result),
        }
        if output_path:
            out_path = normalize_path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            log("ISSUE_EXTRACTOR", "Report written to: {}".format(out_path))
        return report

    def _generate_recommendations(self, fixes_result: Dict) -> List[str]:
        recs = []
        summary = fixes_result.get("summary", {})
        if summary.get("stale_count", 0) > 0:
            recs.append("[ACTION REQUIRED] Found {} stale fix reference(s). These issues are closed but still referenced in file frontmatter. Remove fixes field from frontmatter and re-upload to clean up.".format(summary["stale_count"]))
        if summary.get("pending_count", 0) > 0:
            recs.append("[INFO] Found {} pending fix reference(s). These issues are open and correctly referenced. Monitor for closure.".format(summary["pending_count"]))
        if summary.get("orphan_count", 0) > 0:
            recs.append("[NOTICE] Found {} orphan issue(s). These issues exist on GitHub but no local file references them. If fixing, add fixes: [{issue_number}] to the relevant file frontmatter.".format(summary["orphan_count"]))
        if summary.get("stale_count", 0) == 0 and summary.get("pending_count", 0) == 0:
            recs.append("[OK] No fix reference issues detected. All fixes fields are clean.")
        recs.append("[AGENT INSTRUCTION] To test each related function: 1) Read the skill SKILL.md for component list, 2) Verify each script version matches the SKILL.md version table, 3) Run the script with --help or dry-run mode, 4) Check that frontmatter extraction works for .md and .py files.")
        return recs

    # ============================================================
    # F006: Full Extraction Workflow
    # ============================================================

    def run(
        self,
        issues: List[Dict],
        query_skill_name: str = None,
        query_filename: str = None,
        query_function: str = None,
        output_path: str = None,
    ) -> Dict:
        log("ISSUE_EXTRACTOR", "=" * 60)
        log("ISSUE_EXTRACTOR", "ISSUE EXTRACTOR v1.0.0")
        log("ISSUE_EXTRACTOR", "Skills dir: {}".format(self.skills_base_dir))
        log("ISSUE_EXTRACTOR", "=" * 60)
        local_files = self.scan_local_skills()
        fixes_result = self.match_fixes(issues, local_files)
        matches = self.match_descriptions(issues, local_files, query_skill_name, query_filename, query_function)
        report = self.generate_report(fixes_result, matches, output_path)
        self._print_summary(report)
        return report

    def run_from_file(
        self,
        issues_file: str,
        query_skill_name: str = None,
        query_filename: str = None,
        query_function: str = None,
        output_path: str = None,
    ) -> Dict:
        file_path = normalize_path(issues_file)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "issues" in data:
            issues = data["issues"]
        elif isinstance(data, list):
            issues = data
        else:
            raise ValueError("Invalid issues file format. Expected {issues: [...]} or raw list.")
        log("ISSUE_EXTRACTOR", "Loaded {} issues from {}".format(len(issues), file_path))
        return self.run(issues, query_skill_name, query_filename, query_function, output_path)

    def _print_summary(self, report: Dict):
        summary = report["fixes_analysis"]["summary"]
        log("ISSUE_EXTRACTOR", "=" * 60)
        log("ISSUE_EXTRACTOR", "EXTRACTION SUMMARY")
        log("ISSUE_EXTRACTOR", "=" * 60)
        log("ISSUE_EXTRACTOR", "Total issues checked:    {}".format(summary["total_issues_checked"]))
        log("ISSUE_EXTRACTOR", "Total files scanned:     {}".format(summary["total_files_scanned"]))
        log("ISSUE_EXTRACTOR", "Total fix references:    {}".format(summary["total_fix_references"]))
        log("ISSUE_EXTRACTOR", "Stale fixes (need cleanup): {}".format(summary["stale_count"]))
        log("ISSUE_EXTRACTOR", "Pending fixes (monitor):    {}".format(summary["pending_count"]))
        log("ISSUE_EXTRACTOR", "Orphan issues (unlinked):   {}".format(summary["orphan_count"]))
        log("ISSUE_EXTRACTOR", "Description matches:        {}".format(len(report["description_matches"])))
        log("ISSUE_EXTRACTOR", "=" * 60)
        if report["fixes_analysis"]["stale_fixes"]:
            log("ISSUE_EXTRACTOR", "[STALE FIXES] - Remove from frontmatter and re-upload:")
            for sf in report["fixes_analysis"]["stale_fixes"]:
                files_str = ", ".join(f["file"] for f in sf.get("files", []))
                log("ISSUE_EXTRACTOR", "  #{} {} -> [{}]".format(sf["issue_number"], sf.get("issue_title", "N/A"), files_str))
        if report["fixes_analysis"]["pending_fixes"]:
            log("ISSUE_EXTRACTOR", "[PENDING FIXES] - Monitor for closure:")
            for pf in report["fixes_analysis"]["pending_fixes"]:
                files_str = ", ".join(f["file"] for f in pf.get("files", []))
                log("ISSUE_EXTRACTOR", "  #{} {} -> [{}]".format(pf["issue_number"], pf.get("issue_title", "N/A"), files_str))
        if report["fixes_analysis"]["orphan_issues"]:
            log("ISSUE_EXTRACTOR", "[ORPHAN ISSUES] - Consider adding fixes field:")
            for oi in report["fixes_analysis"]["orphan_issues"][:5]:
                log("ISSUE_EXTRACTOR", "  #{} [{}] {}".format(oi["issue_number"], oi["issue_state"], oi["issue_title"]))
            if len(report["fixes_analysis"]["orphan_issues"]) > 5:
                log("ISSUE_EXTRACTOR", "  ... and {} more".format(len(report["fixes_analysis"]["orphan_issues"]) - 5))
        log("ISSUE_EXTRACTOR", "[RECOMMENDATIONS]")
        for rec in report["recommendations"]:
            log("ISSUE_EXTRACTOR", "  {}".format(rec))
        log("ISSUE_EXTRACTOR", "=" * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Issue Extractor - Cross-reference local skills against GitHub issues")
    parser.add_argument("--issues-file", help="Path to JSON file with issues (from repo_issue_finder)")
    parser.add_argument("--issues-json", help="Raw JSON string of issues list")
    parser.add_argument("--skill-name", help="Filter matches by skill name")
    parser.add_argument("--filename", help="Filter matches by filename")
    parser.add_argument("--function", help="Filter matches by function name")
    parser.add_argument("--output", default="~/workbuddy/logs/extraction_report.json", help="Output JSON report path")
    parser.add_argument("--skills-dir", help="Override skills base directory")
    parser.add_argument("--version", action="store_true", help="Show version")
    args = parser.parse_args()
    if args.version:
        print("issue_extractor.py v1.0.0")
        sys.exit(0)
    extractor = IssueExtractor(skills_base_dir=args.skills_dir)
    if args.issues_file:
        report = extractor.run_from_file(args.issues_file, args.skill_name, args.filename, args.function, args.output)
    elif args.issues_json:
        issues = json.loads(args.issues_json)
        report = extractor.run(issues, args.skill_name, args.filename, args.function, args.output)
    else:
        log("ISSUE_EXTRACTOR", "ERROR: Must provide --issues-file or --issues-json", "ERROR")
        sys.exit(1)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
