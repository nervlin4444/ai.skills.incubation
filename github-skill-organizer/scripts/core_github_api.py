"""
---
title: Core GitHub API Client
name: github-skill-organizer
description: Unified GitHub API call layer with SSL fallback. All github.com API calls must go through this module per interface isolation architecture.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-24T15:58:00+08:00
fixes: []
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: scripts/core_github_api.py
  github_path: github-skill-organizer/scripts/core_github_api.py
---
"""

import json
import ssl
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class GitHubAPIClient:
    """
    Unified GitHub API client.
    Interface isolation: all github.com API calls must use this class.
    """

    def __init__(self, token: str, api_base: str = "https://api.github.com"):
        self.token = token
        self.api_base = api_base

    def call(self, endpoint: str, method: str = "GET", payload: dict = None, use_unverified: bool = False) -> dict:
        """
        Make authenticated GitHub API call with SSL fallback.
        Returns parsed JSON dict. On error returns {"error": True, "status": code, "message": "..."}.
        """
        endpoint = endpoint.lstrip("/")
        url = f"{self.api_base}/{endpoint}"

        data = json.dumps(payload).encode("utf-8") if payload else None
        req = Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("Accept", "application/vnd.github+json")
        if data:
            req.add_header("Content-Type", "application/json")

        ctx = None
        if use_unverified:
            ctx = ssl._create_unverified_context()
            print(f"[WARN] SSL verification disabled for: {url}")

        try:
            if ctx:
                with urlopen(req, timeout=30, context=ctx) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            else:
                with urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            return {"error": True, "status": e.code, "message": str(e)}
        except URLError as e:
            err_str = str(e.reason) if hasattr(e, "reason") else str(e)
            if "CERTIFICATE_VERIFY_FAILED" in err_str and not use_unverified:
                return self.call(endpoint, method, payload, use_unverified=True)
            return {"error": True, "status": 0, "message": err_str}
        except Exception as e:
            return {"error": True, "status": 0, "message": str(e)}
