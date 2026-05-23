#!/usr/bin/env python3
"""
---
title: "RESTful Core Connector"
name: "github-restful-api-connector"
description: "Unified HTTP client: auth, pagination, rate limiting, error retry. v0.1.2 unified frontmatter format (fixes field, removed {baseDir}, single file_mapping)."
version: "0.1.2"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-23T11:28:00+08:00"
fixes: []

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: ".env"

file_mapping:
  local_path: "scripts/github_restful_core.py"
  github_path: "github-restful-api-connector/scripts/github_restful_core.py"
---
"""

# github_restful_core.py - F-001 Unified HTTP Client
# Version: v0.1.2
# Generated: 2026-05-23 11:28:00
# Core changes: unified frontmatter format (fixes field, removed {baseDir}, single file_mapping).
# Features unchanged: auth, pagination, rate limiting, error retry, PAT diagnostics.

import os
import sys
import time
import json
import logging
from pathlib import Path
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================
# Configuration & Constants
# ============================================
VERSION = "0.1.2"
API_VERSION = "2022-11-28"
BASE_REST_URL = "https://api.github.com"
BASE_GRAPHQL_URL = "https://api.github.com/graphql"

# ============================================
# Logging Setup
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("github_restful_core")

# ============================================
# Environment Loading (lazy call, prohibit module-level execution)
# ============================================
_ENV_LOADED = False
_TOKEN = None
_OWNER = None
_REPO = None
_PROJECT_NUMBER = None

def load_env():
    """Load environment variables from .env file. Lazy call, prohibit module-level execution."""
    global _ENV_LOADED, _TOKEN, _OWNER, _REPO, _PROJECT_NUMBER
    if _ENV_LOADED:
        return
    env_paths = [
        Path.home() / ".workbuddy" / "skills" / "github-restful-api-connector" / ".env",
        Path.home() / ".openclaw" / "skills" / "github-restful-api-connector" / ".env",
        Path(".env"),
    ]
    try:
        env_paths.insert(2, Path(__file__).parent / ".env")
    except NameError:
        pass
    for p in env_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        # Fix: direct assignment, ensure .env overrides system env vars
                        os.environ[key] = val
            logger.info(f"Loaded env from: {p}")
            break
    else:
        logger.error("No .env file found in any official path. Stop.")
        sys.exit(1)
    _TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
    _OWNER = os.environ.get("GITHUB_OWNER", "").strip()
    _REPO = os.environ.get("GITHUB_REPO", "").strip()
    _PROJECT_NUMBER = os.environ.get("GITHUB_PROJECT_NUMBER", "").strip()
    if not _TOKEN:
        logger.error("GITHUB_TOKEN not set. Stop.")
        sys.exit(1)
    _ENV_LOADED = True

def get_token() -> str:
    load_env()
    return _TOKEN

def get_owner() -> str:
    load_env()
    return _OWNER

def get_repo() -> str:
    load_env()
    return _REPO

def get_project_number() -> str:
    load_env()
    return _PROJECT_NUMBER

# ============================================
# HTTP Session (lazy load, prohibit module-level creation)
# ============================================
_SESSION = None

def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {get_token()}",
            "X-GitHub-Api-Version": API_VERSION,
        })
        retry = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PATCH"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        _SESSION.mount("https://", adapter)
    return _SESSION

# ============================================
# Core Functions
# ============================================
def graphql_query(query: str, variables: dict = None) -> dict:
    """
    Unified GraphQL call.
    Handles pagination and rate limiting.
    """
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = get_session().post(BASE_GRAPHQL_URL, json=payload)
    if resp.status_code == 401:
        logger.error("401 Unauthorized - PAT invalid or expired. Stop.")
        sys.exit(1)
    if resp.status_code == 403:
        reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
        wait = max(reset_time - int(time.time()), 0) + 1
        logger.warning(f"403 Rate limited. Retry after {wait}s.")
        time.sleep(wait)
        return graphql_query(query, variables)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        logger.error(f"GraphQL errors: {data['errors']}")
        raise RuntimeError(f"GraphQL error: {data['errors']}")
    return data.get("data", {})

def rest_request(method: str, endpoint: str, payload: dict = None) -> dict:
    """
    Unified REST call.
    Method limited to GET / POST / PUT / PATCH / DELETE.
    This is the core interface of github-restful-api-connector. All github.com API calls must go through this function.
    Complies with interface isolation decision: prohibit any skill script from directly using urllib.request or requests to access GitHub API.
    """
    method = method.upper()
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise ValueError(f"Method {method} not allowed.")
    url = urljoin(BASE_REST_URL, endpoint)
    kwargs = {}
    if payload is not None:
        kwargs["json"] = payload
    resp = get_session().request(method, url, **kwargs)
    if resp.status_code == 401:
        logger.error("401 Unauthorized - PAT invalid or expired. Stop.")
        sys.exit(1)
    if resp.status_code == 403:
        reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
        wait = max(reset_time - int(time.time()), 0) + 1
        logger.warning(f"403 Rate limited. Retry after {wait}s.")
        time.sleep(wait)
        return rest_request(method, endpoint, payload)
    if resp.status_code == 404:
        logger.error(f"404 Not Found: {endpoint}. Stop.")
        raise RuntimeError(f"404 Not Found: {endpoint}")
    if resp.status_code == 422:
        logger.error(f"422 Validation Failed: {resp.text}. Stop.")
        raise RuntimeError(f"Validation failed: {resp.text}")
    resp.raise_for_status()
    if resp.status_code == 204:
        return {}
    return resp.json()

def get_rate_limit_status() -> dict:
    """
    Returns remaining quota and reset time, for upstream decision on whether to continue calling.
    """
    data = rest_request("GET", "/rate_limit")
    core = data.get("resources", {}).get("core", {})
    return {
        "limit": core.get("limit", 0),
        "remaining": core.get("remaining", 0),
        "reset_timestamp": core.get("reset", 0),
        "used": core.get("used", 0),
    }

# ============================================
# PAT Test Diagnostics (for verify script)
# ============================================
def test_pat_diagnostic() -> dict:
    """
    Comprehensive PAT validity diagnosis.
    Returns structured report, for upstream root cause analysis.
    """
    report = {
        "token_loaded": False,
        "token_prefix": "",
        "token_length": 0,
        "token_format_ok": False,
        "api_reachable": False,
        "auth_success": False,
        "user_login": "",
        "scopes": [],
        "rate_limit": {},
        "repo_accessible": False,
        "repo_name": "",
        "repo_exists": False,
        "errors": [],
    }

    # Step 1: Load .env
    try:
        load_env()
        token = get_token()
        report["token_loaded"] = True
        report["token_prefix"] = token[:12] + "..." if len(token) > 12 else token
        report["token_length"] = len(token)
        report["token_format_ok"] = token.startswith("ghp_") and len(token) == 40
    except SystemExit:
        report["errors"].append("GITHUB_TOKEN not found in .env or environment")
        return report
    except Exception as e:
        report["errors"].append(f"Token load failed: {e}")
        return report

    # Step 2: Test API connectivity (unauthenticated endpoint)
    try:
        # Test unauthenticated /rate_limit first (public endpoint)
        resp = requests.get("https://api.github.com/rate_limit", timeout=10)
        report["api_reachable"] = resp.status_code == 200
    except Exception as e:
        report["errors"].append(f"API unreachable: {e}")
        return report

    # Step 3: Test authentication (/user)
    try:
        user = rest_request("GET", "/user")
        report["auth_success"] = True
        report["user_login"] = user.get("login", "")
    except RuntimeError as e:
        err_str = str(e)
        if "401" in err_str:
            report["errors"].append("401 Unauthorized - Token invalid or expired")
        elif "403" in err_str:
            report["errors"].append("403 Forbidden - Token lacks required scope (need 'repo')")
        else:
            report["errors"].append(f"Auth test failed: {e}")
        return report
    except Exception as e:
        report["errors"].append(f"Auth test exception: {e}")
        return report

    # Step 4: Rate limit
    try:
        report["rate_limit"] = get_rate_limit_status()
    except Exception as e:
        report["errors"].append(f"Rate limit check failed: {e}")

    # Step 5: Repository check
    owner = get_owner()
    repo = get_repo()
    report["repo_name"] = f"{owner}/{repo}" if owner and repo else ""
    if owner and repo:
        try:
            repo_data = rest_request("GET", f"/repos/{owner}/{repo}")
            report["repo_exists"] = True
            report["repo_accessible"] = True
        except RuntimeError as e:
            err_str = str(e)
            if "404" in err_str:
                report["repo_exists"] = False
                report["errors"].append(f"Repo '{owner}/{repo}' not found - will auto-create on sync")
            elif "401" in err_str or "403" in err_str:
                report["errors"].append(f"No access to repo '{owner}/{repo}' - check PAT 'repo' scope")
            else:
                report["errors"].append(f"Repo check failed: {e}")

    return report

# ============================================
# CLI Entry
# ============================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub RESTful Core - F-001")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--test-connection", action="store_true", help="Test API connection")
    args = parser.parse_args()

    if args.version:
        print(f"github_restful_core.py v{VERSION}")
        return

    if args.test_connection:
        try:
            load_env()
            user = rest_request("GET", "/user")
            print(f"[OK] Authenticated as: {user.get('login', 'unknown')}")
            rl = get_rate_limit_status()
            print(f"[OK] Rate limit remaining: {rl['remaining']}/{rl['limit']}")
            owner = get_owner()
            repo = get_repo()
            if owner and repo:
                try:
                    repo_data = rest_request("GET", f"/repos/{owner}/{repo}")
                    print(f"[OK] Repo access confirmed: {repo_data.get('full_name', 'unknown')}")
                except RuntimeError as e:
                    if "404" in str(e):
                        print(f"[WARN] Repo '{owner}/{repo}' not found or no access. Check PAT 'repo' scope and repo name.")
                    else:
                        print(f"[WARN] Repo check failed: {e}")
            else:
                print("[INFO] GITHUB_REPO not set. Skipping repo access test.")
            project_number = get_project_number()
            if owner and project_number:
                q = (
                    "query($owner: String!, $number: Int!) {"
                    "  userOrOrganization(login: $owner) {"
                    "    projectV2(number: $number) { id title }"
                    "  }"
                    "}"
                )
                result = graphql_query(q, {"owner": owner, "number": int(project_number)})
                proj = result.get("userOrOrganization", {}).get("projectV2")
                if proj:
                    print(f"[OK] Project #{project_number} found: {proj.get('title', 'untitled')}")
                else:
                    print(f"[WARN] Project #{project_number} not found for owner '{owner}'")
            print("[OK] Connection test passed.")
        except Exception as e:
            print(f"[FAIL] {e}")
            sys.exit(1)
        return

    parser.print_help()

if __name__ == "__main__":
    main()
