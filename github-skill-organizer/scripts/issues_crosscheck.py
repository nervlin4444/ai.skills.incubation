#!/usr/bin/env python3
"""
---
title: "Issues Crosscheck - GitHub Issue vs Local Skill Fixes Validator"
name: github-skill-organizer
description: "Cross-checks GitHub Issues against local skill files frontmatter fixes field. Detects stale fixes, pending fixes, orphan issues. Matches issue descriptions to local skill names, filenames, and function names for agent context retrieval. v1.0.0 initial release."
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-24T13:30:00+08:00"
fixes: []
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: "../.env"
file_mapping:
  local_path: "scripts/issues_crosscheck.py"
  github_path: "github-skill-organizer/scripts/issues_crosscheck.py"
---
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set


# =====================================================================
# Interface Isolation: Dynamic import of github-restful-api-connector
# =====================================================================

def _import_connector():
    """Import github-restful-api-connector rest_request with fallback paths."""
    try:
        from github_restful_core import rest_request, get_owner, get_repo
        return rest_request, get_owner, get_repo
    except ImportError:
        search_paths = [
            Path.home() / ".workbuddy" / "skills" / "github-restful-api-connector" / "scripts",
            Path.home() / ".openclaw" / "skills" / "github-restful-api-connector" / "scripts",
            Path(__file__).parent.parent.parent / "github-restful-api-connector" / "scripts",
        ]
        for sp in search_paths:
            if sp.exists() and str(sp) not in sys.path:
                sys.path.insert(0, str(sp))
                try:
                    from github_restful_core import rest_request, get_owner, get_repo
                    return rest_request, get_owner, get_repo
                except ImportError:
                    continue
    raise ImportError(
        "[CROSSCHECK] github-restful-api-connector not found. "
        "Please ensure github-restful-api-connector/scripts/github_restful_core.py exists.")


class IssuesCrosscheck:
    """
    Issues Crosscheck Engine v1.0.0

    Core functions:
    1. Download GitHub issues with configurable filters
    2. Scan local skill directories and extract frontmatter fixes fields
    3. Match fixes references against actual issue states
    4. Match issue descriptions against local skill names, filenames, functions
    5. Generate structured report for user review (NO auto-modification)

    Architecture compliance:
    - ALL GitHub API calls go through github-restful-api-connector rest_request()
    - Frontmatter extraction uses built-in parser (no external YAML lib)
    - Read-only operation on local files (no write)
    """

    def __init__(self, owner: str = None, repo: str = None, token: str = None,
                 skills_base_dir: str = None):
        self.rest_request, self._get_owner, self._get_repo = _import_connector()
        self.owner = owner or self._get_owner()
        self.repo = repo or self._get_repo()
        self.token = token or os.environ.get("GITHUB_TOKEN", "")

        if skills_base_dir:
            self.skills_base_dir = Path(os.path.expanduser(str(skills_base_dir))).resolve()
        else:
            self.skills_base_dir = Path.home() / ".workbuddy" / "skills"

        self._ensure_dirs()

    def _ensure_dirs(self):
        self.skills_base_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # F-001: Download GitHub Issues
    # ============================================================

    def fetch_issues(self, state: str = "open", labels: List[str] = None,
                     per_page: int = 100, max_pages: int = 10) -> List[Dict]:
        """
        Fetch GitHub issues with filtering.

        Args:
            state: "open", "closed", or "all"
            labels: List of label names to filter
            per_page: Items per page (max 100)
            max_pages: Max pages to fetch (safety limit)

        Returns:
            List of issue dicts with normalized fields
        """
        issues = []
        page = 1

        while page <= max_pages:
            endpoint = "/repos/{}/{}".format(self.owner, self.repo) + "/issues"
            params = ["state={}".format(state), "per_page={}".format(per_page), "page={}".format(page)]
            if labels:
                params.append("labels={}".format(",".join(labels)))

            url_suffix = "?" + "&".join(params)

            try:
                result = self.rest_request("GET", endpoint + url_suffix)
            except Exception as e:
                print("[CROSSCHECK] API error on page {}: {}".format(page, e))
                break

            if not isinstance(result, list):
                print("[CROSSCHECK] Unexpected response type: {}".format(type(result)))
                break

            if not result:
                break

            for issue in result:
                if "pull_request" in issue:
                    continue

                normalized = {
                    "number": issue.get("number"),
                    "title": issue.get("title", ""),
                    "body": issue.get("body", "") or "",
                    "state": issue.get("state", "unknown"),
                    "labels": [l.get("name", "") for l in issue.get("labels", [])],
                    "created_at": issue.get("created_at", ""),
                    "updated_at": issue.get("updated_at", ""),
                    "closed_at": issue.get("closed_at", ""),
                    "html_url": issue.get("html_url", ""),
                    "user_login": issue.get("user", {}).get("login", ""),
                }
                issues.append(normalized)

            issue_count = len([i for i in result if "pull_request" not in i])
            print("[CROSSCHECK] Fetched page {}: {} items, {} issues".format(page, len(result), issue_count))
            page += 1

        print("[CROSSCHECK] Total issues fetched: {}".format(len(issues)))
        return issues

    # ============================================================
    # F-002: Scan Local Skills & Extract Fixes
    # ============================================================

    def scan_local_skills(self) -> Dict[str, Dict]:
        """
        Scan all skill directories under skills_base_dir.
        Extract frontmatter and fixes field from each file.

        Returns:
            Dict mapping file_path -> {skill_name, frontmatter, fixes, content_preview}
        """
        results = {}

        if not self.skills_base_dir.exists():
            print("[CROSSCHECK] Skills base dir not found: {}".format(self.skills_base_dir))
            return results

        for skill_dir in self.skills_base_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith("."):
                continue

            skill_name = skill_dir.name

            for file_path in skill_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.name.startswith("."):
                    continue
                if file_path.suffix not in [".md", ".py", ".json", ".html", ".env", ".yaml", ".yml"]:
                    continue

                fm = self._extract_frontmatter(file_path)
                fixes = self._extract_fixes(fm)

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

        print("[CROSSCHECK] Scanned {} files with frontmatter/fixes".format(len(results)))
        return results

    def _extract_frontmatter(self, file_path: Path) -> Optional[Dict]:
        """Extract frontmatter without external YAML library."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        if file_path.suffix == ".md" and content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                return self._parse_simple_yaml(content[3:end])

        if file_path.suffix == ".py":
            for quote in ['"""', chr(39)*3]:
                pattern = re.compile(
                    re.escape(quote) + r"\s*---\s*(.*?)\s*---\s*" + re.escape(quote),
                    re.DOTALL
                )
                match = pattern.search(content)
                if match:
                    return self._parse_simple_yaml(match.group(1))

        if file_path.suffix == ".json":
            try:
                data = json.loads(content)
                if "_meta" in data:
                    return data["_meta"]
            except json.JSONDecodeError:
                pass

        return None

    def _parse_simple_yaml(self, yaml_text: str) -> Dict:
        """Parse simple YAML subset."""
        result = {}
        current_key = None
        current_dict = None

        for line in yaml_text.splitlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue

            match = re.match(r"^(\s*)([\w_]+):\s*(.*)$", line)
            if match:
                indent, key, value = match.groups()
                indent_level = len(indent)

                if indent_level == 0:
                    current_key = key
                    if not value:
                        result[key] = {}
                        current_dict = result[key]
                    else:
                        val = value.strip().strip(chr(34)).strip(chr(39))
                        if val.startswith("[") and val.endswith("]"):
                            inner = val[1:-1].strip()
                            if not inner:
                                result[key] = []
                            else:
                                items = [x.strip().strip(chr(34)).strip(chr(39)) for x in inner.split(",")]
                                parsed = []
                                for item in items:
                                    try:
                                        parsed.append(int(item))
                                    except ValueError:
                                        parsed.append(item)
                                result[key] = parsed
                        else:
                            result[key] = val
                        current_dict = None
                elif current_dict is not None and indent_level > 0:
                    val = value.strip().strip(chr(34)).strip(chr(39))
                    current_dict[key] = val

        return result

    def _extract_fixes(self, frontmatter: Optional[Dict]) -> List[int]:
        """Extract fixes as list of integers."""
        if not frontmatter:
            return []
        fixes = frontmatter.get("fixes", [])
        if isinstance(fixes, int):
            return [fixes]
        if isinstance(fixes, str):
            try:
                return [int(fixes)]
            except ValueError:
                return []
        if isinstance(fixes, list):
            result = []
            for f in fixes:
                try:
                    result.append(int(f))
                except (ValueError, TypeError):
                    pass
            return result
        return []

    def _get_content_preview(self, file_path: Path, max_lines: int = 50) -> str:
        """Get first N lines for function name extraction."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()[:max_lines]
            return "
".join(lines)
        except Exception:
            return ""

    # ============================================================
    # F-003: Fixes Matching (Stale / Pending / Orphan)
    # ============================================================

    def match_fixes(self, issues: List[Dict], local_files: Dict[str, Dict]) -> Dict:
        """
        Cross-reference local fixes against GitHub issue states.

        Returns:
            {
                "stale_fixes": [...],
                "pending_fixes": [...],
                "orphan_issues": [...],
                "summary": {...}
            }
        """
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
    # F-004: Description Matching (Skill / File / Function)
    # ============================================================

    def match_descriptions(self, issues: List[Dict], local_files: Dict[str, Dict],
                          query_skill_name: str = None,
                          query_filename: str = None,
                          query_function: str = None) -> List[Dict]:
        """
        Match issue descriptions against local skill context.

        Args:
            query_skill_name: Filter by specific skill name
            query_filename: Filter by specific filename
            query_function: Filter by function name mentioned in issue

        Returns:
            List of matched issues with relevance scores and matching context
        """
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
                        match_info["matched_skills"].append({
                            "skill_name": skill_name,
                            "files_in_skill": [],
                        })
                    match_info["relevance_score"] += 10
                    match_info["match_reasons"].append("Skill name '{}' found in issue".format(skill_name))

            for rel_path, info in local_files.items():
                filename = info["filename"]
                if filename.lower() in combined:
                    match_info["matched_files"].append({
                        "filename": filename,
                        "skill_name": info["skill_name"],
                        "relative_path": rel_path,
                    })
                    match_info["relevance_score"] += 15
                    match_info["match_reasons"].append("Filename '{}' found in issue".format(filename))

            if query_function:
                func_pattern = re.compile(r"" + re.escape(query_function.lower()) + r"")
                if func_pattern.search(combined):
                    match_info["matched_functions"].append({
                        "function_name": query_function,
                        "found_in": "issue_title_or_body",
                    })
                    match_info["relevance_score"] += 20
                    match_info["match_reasons"].append("Function '{}' found in issue".format(query_function))

            for rel_path, info in local_files.items():
                if info["filename"].endswith(".py"):
                    funcs = self._extract_function_names(info.get("content_preview", ""))
                    for func in funcs:
                        if func.lower() in combined and len(func) > 3:
                            if func not in [m["function_name"] for m in match_info["matched_functions"]]:
                                match_info["matched_functions"].append({
                                    "function_name": func,
                                    "found_in": "local_file:{}".format(rel_path),
                                })
                                match_info["relevance_score"] += 12
                                match_info["match_reasons"].append("Function '{}' from {} mentioned in issue".format(func, rel_path))

            if query_skill_name:
                skill_match = any(m["skill_name"] == query_skill_name for m in match_info["matched_skills"])
                if not skill_match:
                    continue

            if query_filename:
                file_match = any(m["filename"] == query_filename for m in match_info["matched_files"])
                if not file_match:
                    continue

            if query_function:
                func_match = any(m["function_name"] == query_function for m in match_info["matched_functions"])
                if not func_match:
                    continue

            if match_info["relevance_score"] > 0:
                matches.append(match_info)

        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matches

    def _extract_function_names(self, content: str) -> List[str]:
        """Extract function names from Python content."""
        pattern = re.compile(r"^\s*def\s+(\w+)\s*\(", re.MULTILINE)
        return pattern.findall(content)

    # ============================================================
    # F-005: Report Generation
    # ============================================================

    def generate_report(self, fixes_result: Dict, matches: List[Dict] = None,
                        output_path: str = None) -> Dict:
        """
        Generate comprehensive crosscheck report.

        Returns:
            Report dict with all findings. If output_path provided, also writes JSON.
        """
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tool_version": "1.0.0",
            "repository": "{}/{}".format(self.owner, self.repo),
            "skills_base_dir": str(self.skills_base_dir),
            "fixes_analysis": fixes_result,
            "description_matches": matches or [],
            "recommendations": self._generate_recommendations(fixes_result),
        }

        if output_path:
            out_path = Path(os.path.expanduser(str(output_path)))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print("[CROSSCHECK] Report written to: {}".format(out_path))

        return report

    def _generate_recommendations(self, fixes_result: Dict) -> List[str]:
        """Generate human-readable recommendations."""
        recs = []
        summary = fixes_result.get("summary", {})

        if summary.get("stale_count", 0) > 0:
            recs.append(
                "[ACTION REQUIRED] Found {} stale fix reference(s). "
                "These issues are closed but still referenced in file frontmatter. "
                "Remove fixes field from frontmatter and re-upload to clean up.".format(summary["stale_count"])
            )

        if summary.get("pending_count", 0) > 0:
            recs.append(
                "[INFO] Found {} pending fix reference(s). "
                "These issues are open and correctly referenced. Monitor for closure.".format(summary["pending_count"])
            )

        if summary.get("orphan_count", 0) > 0:
            recs.append(
                "[NOTICE] Found {} orphan issue(s). "
                "These issues exist on GitHub but no local file references them. "
                "If fixing, add fixes: [{issue_number}] to the relevant file frontmatter.".format(summary["orphan_count"])
            )

        if summary.get("stale_count", 0) == 0 and summary.get("pending_count", 0) == 0:
            recs.append("[OK] No fix reference issues detected. All fixes fields are clean.")

        recs.append(
            "[AGENT INSTRUCTION] To test each related function: "
            "1) Read the skill SKILL.md for component list, "
            "2) Verify each script version matches the SKILL.md version table, "
            "3) Run the script with --help or dry-run mode, "
            "4) Check that frontmatter extraction works for .md and .py files."
        )

        return recs

    # ============================================================
    # F-006: Full Crosscheck Workflow
    # ============================================================

    def run(self, state: str = "all", labels: List[str] = None,
            query_skill_name: str = None, query_filename: str = None,
            query_function: str = None,
            output_path: str = None,
            dry_run: bool = False) -> Dict:
        """
        Execute full crosscheck workflow.

        Args:
            state: Issue state filter
            labels: Label filter
            query_skill_name: Optional skill name filter for description matching
            query_filename: Optional filename filter
            query_function: Optional function name filter
            output_path: Where to write JSON report
            dry_run: If True, skip API calls and use cached data (for testing)

        Returns:
            Complete report dict
        """
        print("
" + "="*60)
        print("ISSUES CROSSCHECK v1.0.0")
        print("Repository: {}/{}".format(self.owner, self.repo))
        print("Skills dir: {}".format(self.skills_base_dir))
        print("="*60 + "
")

        if dry_run:
            print("[CROSSCHECK] DRY RUN: Skipping API calls")
            issues = []
        else:
            issues = self.fetch_issues(state=state, labels=labels)

        local_files = self.scan_local_skills()

        fixes_result = self.match_fixes(issues, local_files)

        matches = self.match_descriptions(
            issues, local_files,
            query_skill_name=query_skill_name,
            query_filename=query_filename,
            query_function=query_function
        )

        report = self.generate_report(fixes_result, matches, output_path)

        self._print_summary(report)

        return report

    def _print_summary(self, report: Dict):
        """Print human-readable summary to stdout."""
        summary = report["fixes_analysis"]["summary"]

        print("
" + "="*60)
        print("CROSSCHECK SUMMARY")
        print("="*60)
        print("Total issues checked:    {}".format(summary["total_issues_checked"]))
        print("Total files scanned:     {}".format(summary["total_files_scanned"]))
        print("Total fix references:    {}".format(summary["total_fix_references"]))
        print("Stale fixes (need cleanup): {}".format(summary["stale_count"]))
        print("Pending fixes (monitor):    {}".format(summary["pending_count"]))
        print("Orphan issues (unlinked):   {}".format(summary["orphan_count"]))
        print("Description matches:        {}".format(len(report["description_matches"])))
        print("="*60)

        if report["fixes_analysis"]["stale_fixes"]:
            print("
[STALE FIXES] - Remove from frontmatter and re-upload:")
            for sf in report["fixes_analysis"]["stale_fixes"]:
                files_str = ", ".join(f["file"] for f in sf.get("files", []))
                print("  #{} {} -> [{}]".format(sf["issue_number"], sf.get("issue_title", "N/A"), files_str))

        if report["fixes_analysis"]["pending_fixes"]:
            print("
[PENDING FIXES] - Monitor for closure:")
            for pf in report["fixes_analysis"]["pending_fixes"]:
                files_str = ", ".join(f["file"] for f in pf.get("files", []))
                print("  #{} {} -> [{}]".format(pf["issue_number"], pf.get("issue_title", "N/A"), files_str))

        if report["fixes_analysis"]["orphan_issues"]:
            print("
[ORPHAN ISSUES] - Consider adding fixes field:")
            for oi in report["fixes_analysis"]["orphan_issues"][:5]:
                print("  #{} [{}] {}".format(oi["issue_number"], oi["issue_state"], oi["issue_title"]))
            if len(report["fixes_analysis"]["orphan_issues"]) > 5:
                print("  ... and {} more".format(len(report["fixes_analysis"]["orphan_issues"]) - 5))

        print("
[RECOMMENDATIONS]")
        for rec in report["recommendations"]:
            print("  {}".format(rec))

        print("
" + "="*60)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Issues Crosscheck - Validate GitHub Issues against local skill fixes"
    )
    parser.add_argument("--state", default="all", choices=["open", "closed", "all"],
                        help="Issue state filter")
    parser.add_argument("--labels", help="Comma-separated label filters")
    parser.add_argument("--skill-name", help="Filter matches by skill name")
    parser.add_argument("--filename", help="Filter matches by filename")
    parser.add_argument("--function", help="Filter matches by function name")
    parser.add_argument("--output", default="~/workbuddy/logs/crosscheck_report.json",
                        help="Output JSON report path")
    parser.add_argument("--skills-dir", help="Override skills base directory")
    parser.add_argument("--owner", help="GitHub owner override")
    parser.add_argument("--repo", help="GitHub repo override")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip API calls (for testing)")
    parser.add_argument("--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        print("issues_crosscheck.py v1.0.0")
        sys.exit(0)

    labels = args.labels.split(",") if args.labels else None

    checker = IssuesCrosscheck(
        owner=args.owner,
        repo=args.repo,
        skills_base_dir=args.skills_dir,
    )

    report = checker.run(
        state=args.state,
        labels=labels,
        query_skill_name=args.skill_name,
        query_filename=args.filename,
        query_function=args.function,
        output_path=args.output,
        dry_run=args.dry_run,
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
