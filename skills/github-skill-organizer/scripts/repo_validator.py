#!/usr/bin/env python3
"""
---
title: GitHub Repository Validator for Local Skills
name: github-skill-organizer
version: 2.0.1
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/scripts/repo_validator.py"
  github_path: "github-skill-organizer/scripts/repo_validator.py"
---
"""

import os
import sys
import re
import json
import ssl
import argparse
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def load_env_from_dependency(dep_env_path):
    """從依賴技能的 .env 讀取 GITHUB_TOKEN。"""
    token = ""
    if os.path.exists(dep_env_path):
        with open(dep_env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GITHUB_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return token


def parse_frontmatter_md(filepath):
    """從 .md 檔案提取 frontmatter。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    fm_text = content[3:end].strip()
    fm = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            fm[key] = val
    return fm


def parse_docstring_py(filepath):
    """從 .py 檔案 docstring 提取 frontmatter。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    triple_double = chr(34) * 3
    triple_single = chr(39) * 3
    for quote in (triple_double, triple_single):
        idx = content.find(quote)
        if idx != -1:
            end = content.find(quote, idx + 3)
            if end != -1:
                doc = content[idx + 3:end]
                if "---" in doc:
                    start = doc.find("---")
                    end_fm = doc.find("---", start + 3)
                    if end_fm != -1:
                        fm_text = doc[start + 3:end_fm].strip()
                        fm = {}
                        for line in fm_text.split("\n"):
                            line = line.strip()
                            if ":" in line and not line.startswith("#"):
                                key, val = line.split(":", 1)
                                key = key.strip()
                                val = val.strip().strip('"').strip("'")
                                fm[key] = val
                        return fm
    return None


def _github_api_call(url, token, use_unverified=False):
    """呼叫 GitHub API，SSL 失敗時可 fallback 到未驗證上下文。"""
    req = Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "repo-validator")

    ctx = None
    if use_unverified:
        ctx = ssl._create_unverified_context()
        print(f"[WARN] SSL verification disabled for: {url}")

    try:
        if ctx:
            with urlopen(req, timeout=15, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        else:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return {"__error": "Repository not found (404)"}
        elif e.code == 401:
            return {"__error": "Unauthorized (401) - check token"}
        else:
            return {"__error": f"HTTP {e.code}"}
    except URLError as e:
        err_str = str(e.reason) if hasattr(e, "reason") else str(e)
        if "CERTIFICATE_VERIFY_FAILED" in err_str and not use_unverified:
            # 第一次 SSL 失敗，嘗試未驗證上下文
            return _github_api_call(url, token, use_unverified=True)
        return {"__error": err_str}
    except Exception as e:
        return {"__error": str(e)}


def check_github_repo_exists(owner_repo, token):
    """驗證倉庫是否存在，帶 SSL fallback。"""
    url = f"https://api.github.com/repos/{owner_repo}"
    data = _github_api_call(url, token)

    if "__error" in data:
        return {"exists": False, "error": data["__error"]}

    return {
        "exists": True,
        "html_url": data.get("html_url", ""),
        "updated_at": data.get("updated_at", ""),
        "private": data.get("private", False),
        "description": data.get("description", "")
    }


def scan_local_skills(skills_dir):
    """掃描本地技能目錄。"""
    skills_dir = Path(skills_dir).expanduser().resolve()
    results = []
    if not skills_dir.exists():
        print(f"[ERROR] Skills directory not found: {skills_dir}")
        return results
    for skill_path in skills_dir.iterdir():
        if not skill_path.is_dir():
            continue
        skill_name = skill_path.name
        github_repo = None
        version = None
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            fm = parse_frontmatter_md(skill_md)
            if fm:
                github_repo = fm.get("github_repository", "")
                version = fm.get("version", "")
        if not github_repo:
            for f in skill_path.rglob("*"):
                if f.is_file() and f.suffix in (".md", ".py"):
                    if f.suffix == ".md":
                        fm = parse_frontmatter_md(f)
                    else:
                        fm = parse_docstring_py(f)
                    if fm and fm.get("github_repository"):
                        github_repo = fm.get("github_repository")
                        version = fm.get("version", "")
                        break
        results.append({
            "skill_name": skill_name,
            "local_path": str(skill_path),
            "github_repository": github_repo or "",
            "version": version or ""
        })
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Validate local skills claimed GitHub repositories actually exist."
    )
    parser.add_argument("--skills-dir", default="~/skills",
                        help="Local skills root directory")
    parser.add_argument("--dep-env", default="~/skills/github-restful-api-connector/.env",
                        help="Path to dependency skill .env for GITHUB_TOKEN")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON for agent consumption")
    parser.add_argument("--no-ssl-verify", action="store_true",
                        help="Disable SSL verification (use if behind corporate proxy)")
    args = parser.parse_args()

    token = load_env_from_dependency(Path(args.dep_env).expanduser())
    if not token:
        print("[WARN] No GITHUB_TOKEN found. Public repos only (rate limit: 60/hr).")

    skills = scan_local_skills(args.skills_dir)

    for skill in skills:
        repo = skill["github_repository"]
        if not repo:
            skill["status"] = "NO_REPO_CLAIMED"
            skill["exists"] = None
            continue
        if "/" not in repo:
            skill["status"] = "INVALID_FORMAT"
            skill["exists"] = False
            skill["error"] = "Missing owner/repo slash"
            continue

        result = check_github_repo_exists(repo, token)
        skill["exists"] = result.get("exists", False)
        skill["status"] = "EXISTS" if result.get("exists") else "NOT_FOUND"
        if "error" in result:
            skill["error"] = result["error"]
        if "html_url" in result:
            skill["html_url"] = result["html_url"]
        if "updated_at" in result:
            skill["github_updated_at"] = result["updated_at"]

    if args.json:
        print(json.dumps({
            "total_skills": len(skills),
            "verified": sum(1 for s in skills if s.get("exists") is not None),
            "exists_count": sum(1 for s in skills if s.get("exists") is True),
            "not_found_count": sum(1 for s in skills if s.get("exists") is False),
            "skills": skills
        }, indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print("LOCAL SKILL -> GITHUB REPOSITORY VALIDATION REPORT")
        print("=" * 70)
        for skill in skills:
            name = skill["skill_name"]
            repo = skill["github_repository"] or "(none)"
            status = skill["status"]
            ver = skill["version"] or "?"
            if status == "EXISTS":
                icon = "[OK]"
                extra = f"  URL: {skill.get('html_url', '')}"
            elif status == "NOT_FOUND":
                icon = "[XX]"
                extra = f"  Error: {skill.get('error', '')}"
            elif status == "NO_REPO_CLAIMED":
                icon = "[WW]"
                extra = "  No github_repository in frontmatter"
            else:
                icon = "[??]"
                extra = f"  {skill.get('error', '')}"
            print(f"\n{icon} {name} (v{ver})")
            print(f"   Claimed: {repo}")
            print(f"   Status:  {status}{extra}")
        print("\n" + "=" * 70)
        exists = sum(1 for s in skills if s.get("status") == "EXISTS")
        not_found = sum(1 for s in skills if s.get("status") == "NOT_FOUND")
        no_claim = sum(1 for s in skills if s.get("status") == "NO_REPO_CLAIMED")
        print(f"Summary: {exists} exists | {not_found} not found | {no_claim} no claim | {len(skills)} total")


if __name__ == "__main__":
    main()
