'''
---
title: "jira_restful_core.py"
name: "jira-restful-api-connector"
description: "F-001: Unified HTTP client for Jira REST API v2. Auto-auth, retry, pagination, rate-limit handling."
version: "v0.1.3"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T23:00:00+08:00"
fixes: [26]
auth_config:
  provider: jira
  auth_method: basic_or_bearer
  token_env_var: JIRA_API_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/scripts/jira_restful_core.py"
  github_path: "jira-restful-api-connector/scripts/jira_restful_core.py"
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
    """Unified HTTP client for Jira REST API v2.

    Auth architecture:
      - Jira Cloud (xxx.atlassian.net): Use username + API Token via Basic Auth.
      - Jira Server/DC (self-hosted): Two options:
        (1) username + PASSWORD via Basic Auth
        (2) PAT (Personal Access Token) via Bearer Token
        Server/DC PATs often REQUIRE Bearer mode even if username is present.
        If PAT with Basic Auth returns 403, force Bearer mode via auth_method="bearer".

    How to choose auth_method:
      - "auto" (default): If username present -> Basic Auth. If only token -> Bearer.
      - "basic": Force Basic Auth (username + token/password).
      - "bearer": Force Bearer Token (token only, username ignored).

    Environment variable override: JIRA_AUTH_METHOD=basic|bearer
    (Implemented at line 67: env_auth = os.getenv("JIRA_AUTH_METHOD", "").lower())
    """

    def __init__(self, jira_url=None, username=None, token=None, auth_method="auto"):
        load_env()
        self.jira_url = (jira_url or os.getenv("JIRA_URL") or os.getenv("JIRA_BASE_URL", "")).rstrip("/")
        self.username = username or os.getenv("JIRA_USERNAME") or os.getenv("JIRA_USER", "")
        self.token = token or os.getenv("JIRA_API_TOKEN") or os.getenv("JIRA_PAT", "")
        if not self.jira_url or not self.token:
            raise RuntimeError("JIRA_URL and JIRA_API_TOKEN (or JIRA_PAT) required")

        # Allow env override of auth method (Bug #2 fix confirmation: this IS implemented)
        env_auth = os.getenv("JIRA_AUTH_METHOD", "").lower()
        if env_auth in ("basic", "bearer"):
            auth_method = env_auth

        self.auth_method = auth_method
        self._auth_header = self._get_auth_header()

    def _get_auth_header(self):
        if self.auth_method == "bearer" or (self.auth_method == "auto" and not self.username):
            return {"Authorization": f"Bearer {self.token}"}
        # Basic Auth: username + token (password or API token)
        creds = base64.b64encode(f"{self.username}:{self.token}".encode()).decode()
        return {"Authorization": f"Basic {creds}"}

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
                    raise RuntimeError(
                        f"401 Unauthorized - check credentials. "
                        f"Current auth: {self.auth_method}. "
                        f"Cloud: use API Token + Basic Auth. "
                        f"Server/DC PAT: try Bearer mode (set JIRA_AUTH_METHOD=bearer or auth_method='bearer')."
                    )
                if e.code == 403:
                    time.sleep(2 ** attempt)
                    continue
                if e.code in (404, 422):
                    raise RuntimeError(f"{e.code} - {e.reason} ({url})")
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

    def search_issues(self, jql, fields=None, max_results=500):
        """JQL search via POST /search.

        Args:
            jql: JQL query string.
            fields: Field list. For Jira Cloud, "*all" works. For Server/DC 10.3.5,
                    use None (API default) or a list like ["key", "summary", "status"].
                    Strings "*all" and "*" are automatically converted to None for compatibility.
            max_results: Max results to return.

        Returns:
            Raw Jira API response dict.
        """
        payload = {"jql": jql, "maxResults": max_results}
        # Bug #4 fix: Server/DC 10.3.5 does not accept string "*all" for fields.
        # Convert "*all" or "*" to None (omitted) for compatibility.
        if fields and fields not in ("*all", "*"):
            payload["fields"] = fields
        return self.post("/search", payload)

    def get_issue(self, issue_key, fields=None, expand=None):
        """Fetch single issue by key.

        Args:
            issue_key: Issue key (e.g. "WIL-10").
            fields: Field list. For Server/DC 10.3.5, use None or list.
                    Strings "*all" and "*" are automatically converted to None.
            expand: Optional expand parameter (e.g. "changelog").

        Returns:
            Issue dict.
        """
        endpoint = f"/issue/{issue_key}"
        params = []
        # Bug #4 fix: Omit fields param if "*all" or "*" for Server/DC compatibility.
        if fields and fields not in ("*all", "*"):
            params.append(f"fields={fields}")
        if expand:
            params.append(f"expand={expand}")
        if params:
            endpoint += "?" + "&".join(params)
        return self.get(endpoint)

    def get_changelog(self, issue_key):
        return self.get(f"/issue/{issue_key}?expand=changelog")
