"""
---
title: Repo Issue Finder
name: github-skill-organizer
description: Downloads GitHub issues from a repository with configurable state, labels, pagination, and safety limits. Pure data fetcher with no local file operations. Outputs normalized issue list for downstream processing. v1.0.0 refactored to use core modules.
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
  local_path: scripts/repo_issue_finder.py
  github_path: github-skill-organizer/scripts/repo_issue_finder.py
---
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from core_path_utils import normalize_path
    from core_logger import log
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    from core_path_utils import normalize_path
    from core_logger import log


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
        "[REPO_ISSUE_FINDER] github-restful-api-connector not found. "
        "Please ensure github-restful-api-connector/scripts/github_restful_core.py exists."
    )


class RepoIssueFinder:
    """
    Repo Issue Finder v1.0.0
    Single responsibility: Download GitHub issues with filters.
    No local file operations. No fixes analysis.
    Output: normalized list of issue dicts.
    Architecture: ALL GitHub API calls go through github-restful-api-connector rest_request().
    """

    def __init__(self, owner: str = None, repo: str = None):
        self.rest_request, self._get_owner, self._get_repo = _import_connector()
        self.owner = owner or self._get_owner()
        self.repo = repo or self._get_repo()

    def find_issues(
        self,
        state: str = "all",
        labels: List[str] = None,
        per_page: int = 100,
        max_pages: int = 10,
        since: str = None,
        assignee: str = None,
        creator: str = None,
        milestone: str = None,
        sort: str = "created",
        direction: str = "desc",
    ) -> List[Dict]:
        """
        F001: Download GitHub issues with full filtering support.
        Args: state (open/closed/all), labels (AND logic), per_page (max 100), max_pages (safety limit),
              since (ISO 8601), assignee, creator, milestone, sort, direction.
        Returns: List of normalized issue dicts.
        """
        issues = []
        page = 1

        while page <= max_pages:
            endpoint = "/repos/{}/{}".format(self.owner, self.repo) + "/issues"
            params = [
                "state={}".format(state),
                "per_page={}".format(per_page),
                "page={}".format(page),
                "sort={}".format(sort),
                "direction={}".format(direction),
            ]

            if labels:
                params.append("labels={}".format(",".join(labels)))
            if since:
                params.append("since={}".format(since))
            if assignee:
                params.append("assignee={}".format(assignee))
            if creator:
                params.append("creator={}".format(creator))
            if milestone:
                params.append("milestone={}".format(milestone))

            url_suffix = "?" + "&".join(params)

            try:
                result = self.rest_request("GET", endpoint + url_suffix)
            except Exception as e:
                log("ISSUE_FINDER", "API error on page {}: {}".format(page, e), "ERROR")
                break

            if not isinstance(result, list):
                log("ISSUE_FINDER", "Unexpected response type: {}".format(type(result)), "ERROR")
                break

            if not result:
                break

            for issue in result:
                # Skip pull requests (GitHub API returns PRs in issues endpoint)
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
                    "assignees": [a.get("login", "") for a in issue.get("assignees", [])],
                    "milestone_title": (issue.get("milestone") or {}).get("title", ""),
                    "comments_count": issue.get("comments", 0),
                }
                issues.append(normalized)

            issue_count = len([i for i in result if "pull_request" not in i])
            log("ISSUE_FINDER", "Fetched page {}: {} items, {} issues".format(page, len(result), issue_count))
            page += 1

        log("ISSUE_FINDER", "Total issues fetched: {}".format(len(issues)))
        return issues

    def save_to_file(self, issues: List[Dict], output_path: str) -> str:
        """Save fetched issues to JSON file for offline processing."""
        out_path = normalize_path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "meta": {
                        "tool": "repo_issue_finder",
                        "version": "1.0.0",
                        "repository": "{}/{}".format(self.owner, self.repo),
                        "fetched_at": __import__("datetime").datetime.now(
                            __import__("datetime").timezone.utc
                        ).isoformat(),
                        "count": len(issues),
                    },
                    "issues": issues,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        log("ISSUE_FINDER", "Saved {} issues to {}".format(len(issues), out_path))
        return str(out_path)

    def run(
        self,
        state: str = "all",
        labels: List[str] = None,
        per_page: int = 100,
        max_pages: int = 10,
        since: str = None,
        assignee: str = None,
        creator: str = None,
        milestone: str = None,
        sort: str = "created",
        direction: str = "desc",
        output_path: str = None,
    ) -> List[Dict]:
        """
        Execute full fetch workflow.
        Returns: List of issue dicts (also saves to file if output_path given)
        """
        log("ISSUE_FINDER", "=" * 60)
        log("ISSUE_FINDER", "REPO ISSUE FINDER v1.0.0")
        log("ISSUE_FINDER", "Repository: {}/{}".format(self.owner, self.repo))
        log("ISSUE_FINDER", "=" * 60)

        issues = self.find_issues(
            state=state,
            labels=labels,
            per_page=per_page,
            max_pages=max_pages,
            since=since,
            assignee=assignee,
            creator=creator,
            milestone=milestone,
            sort=sort,
            direction=direction,
        )

        if output_path:
            self.save_to_file(issues, output_path)

        log("ISSUE_FINDER", "[SUMMARY] Fetched {} issues".format(len(issues)))
        state_counts = {}
        for i in issues:
            s = i["state"]
            state_counts[s] = state_counts.get(s, 0) + 1
        for s, c in sorted(state_counts.items()):
            log("ISSUE_FINDER", "  {}: {}".format(s, c))

        return issues


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Repo Issue Finder - Download GitHub issues with filters")
    parser.add_argument("--state", default="all", choices=["open", "closed", "all"], help="Issue state filter")
    parser.add_argument("--labels", help="Comma-separated label filters")
    parser.add_argument("--per-page", type=int, default=100, help="Items per page (max 100)")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to fetch")
    parser.add_argument("--since", help="ISO 8601 timestamp for updated-after filter")
    parser.add_argument("--assignee", help="Filter by assignee login")
    parser.add_argument("--creator", help="Filter by creator login")
    parser.add_argument("--milestone", help="Filter by milestone number")
    parser.add_argument("--sort", default="created", choices=["created", "updated", "comments"], help="Sort field")
    parser.add_argument("--direction", default="desc", choices=["asc", "desc"], help="Sort direction")
    parser.add_argument("--output", help="Save to JSON file path")
    parser.add_argument("--owner", help="GitHub owner override")
    parser.add_argument("--repo", help="GitHub repo override")
    parser.add_argument("--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        print("repo_issue_finder.py v1.0.0")
        sys.exit(0)

    labels = args.labels.split(",") if args.labels else None

    finder = RepoIssueFinder(owner=args.owner, repo=args.repo)

    issues = finder.run(
        state=args.state,
        labels=labels,
        per_page=args.per_page,
        max_pages=args.max_pages,
        since=args.since,
        assignee=args.assignee,
        creator=args.creator,
        milestone=args.milestone,
        sort=args.sort,
        direction=args.direction,
        output_path=args.output,
    )

    print(json.dumps(issues, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
