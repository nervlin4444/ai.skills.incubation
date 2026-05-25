'''
---
title: "jira.restful.core.py"
name: "jira-restful-api-connector"
description: "F-001: Unified HTTP client for Jira REST API v2. Auto-auth, retry, pagination, rate-limit handling."
version: "v0.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T00:52:00+08:00"
fixes: []
auth_config:
  provider: jira
  auth_method: basic_or_bearer
  token_env_var: JIRA_API_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/scripts/jira.restful.core.py"
  github_path: "jira-restful-api-connector/scripts/jira.restful.core.py"
---
'''
import os
import sys
import json
import base64
import urllib.request
import urllib.error
import time
from pathlib import Path


def load_env(env_path=".env"):
    """Load key=value pairs from .env file into os.environ."""
    p = Path(env_path)
    if not p.exists():
        p = Path(__file__).parent.parent / env_path
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class JiraClient:
    def __init__(self, jira_url=None, username=None, token=None):
        load_env()
        self.jira_url = (jira_url or os.getenv("JIRA_URL") or os.getenv("JIRA_BASE_URL", "")).rstrip("/")
        self.username = username or os.getenv("JIRA_USERNAME") or os.getenv("JIRA_USER", "")
        self.token = token or os.getenv("JIRA_API_TOKEN") or os.getenv("JIRA_PAT", "")
        if not self.jira_url or not self.token:
            raise RuntimeError("JIRA_URL and JIRA_API_TOKEN (or JIRA_PAT) required")
        self._auth_header = self._get_auth_header()

    def _get_auth_header(self):
        if self.username:
            creds = base64.b64encode(f"{self.username}:{self.token}".encode()).decode()
            return {"Authorization": f"Basic {creds}"}
        return {"Authorization": f"Bearer {self.token}"}

    def _request(self, endpoint, method="GET", data=None, retries=3):
        url = f"{self.jira_url}/rest/api/2{endpoint}"
        headers = {**self._auth_header, "Content-Type": "application/json"}
        body = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        last_err = None
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code == 401:
                    raise RuntimeError(f"401 Unauthorized — check token/username")
                if e.code == 403:
                    time.sleep(2 ** attempt)
                    continue
                if e.code in (404, 422):
                    raise RuntimeError(f"{e.code} — {e.reason} ({url})")
                if 500 <= e.code < 600:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
            except Exception as e:
                last_err = e
                time.sleep(1)
        raise last_err

    def get(self, endpoint):
        return self._request(endpoint, "GET")

    def post(self, endpoint, data):
        return self._request(endpoint, "POST", data)
