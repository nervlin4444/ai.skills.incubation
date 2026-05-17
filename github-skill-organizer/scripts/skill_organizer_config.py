"""
---
title: Skill Organizer Configuration Loader
name: github-skill-organizer
description: Loads and validates .env and sync.config.json. GITHUB_TOKEN and GITHUB_OWNER are borrowed from dependency skill github-restful-api-connector.
version: 1.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
auth_config:
  provider: github
  auth_method: personal_access_token
  token_env_var: GITHUB_TOKEN
  env_file_path: ../.env
file_mapping:
  local_path: "{baseDir}/scripts/skill_organizer_config.py"
  github_path: "github-skill-organizer/scripts/skill_organizer_config.py"
---
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv


class ConfigError(Exception):
    pass


class SkillOrganizerConfig:
    """
    Configuration for github-skill-organizer.
    Authentication (GITHUB_TOKEN, GITHUB_OWNER) is borrowed from
    the dependency skill github-restful-api-connector.
    """

    REQUIRED_ENV_VARS = [
        "DOWNLOAD_FOLDER",
        "USER_SKILLS_FOLDER",
        "DEPENDENCY_SKILL",
        "DEPENDENCY_SKILL_PATH",
    ]

    def __init__(self, env_path=None, config_path=None):
        self.script_dir = Path(__file__).parent.absolute()
        self.skill_root = self.script_dir.parent

        if env_path is None:
            env_path = self.skill_root / ".env"
        if config_path is None:
            config_path = self.skill_root / "config" / "sync.config.json"

        self.env_path = Path(env_path)
        self.config_path = Path(config_path)

        self._load_env()
        self._load_json_config()
        self._validate()

    def _load_env(self):
        if not self.env_path.exists():
            raise ConfigError(f".env file not found at {self.env_path}")
        load_dotenv(self.env_path, override=True)

        # Local paths (independent)
        self.download_folder = self._expand_path(os.getenv("DOWNLOAD_FOLDER", ""))
        self.user_skills_folder = self._expand_path(os.getenv("USER_SKILLS_FOLDER", ""))

        # Dependency skill reference
        self.dependency_skill = os.getenv("DEPENDENCY_SKILL", "").strip()
        self.dependency_skill_path = self._expand_path(os.getenv("DEPENDENCY_SKILL_PATH", ""))

        # Daemon settings
        self.log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        self.scan_interval = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))
        self.pid_file_path = os.getenv("PID_FILE_PATH", "/tmp/github-skill-organizer.pid")
        self.enable_web_fetcher = os.getenv("ENABLE_WEB_FETCHER", "false").lower() == "true"
        self.web_fetcher_interval = int(os.getenv("WEB_FETCHER_INTERVAL_MINUTES", "30"))
        self.auto_approve_patch = os.getenv("AUTO_APPROVE_PATCH", "true").lower() == "true"
        self.patch_max_files = int(os.getenv("PATCH_MAX_FILES", "3"))

    def _load_json_config(self):
        if not self.config_path.exists():
            raise ConfigError(f"sync.config.json not found at {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.json_config = json.load(f)

    def _validate(self):
        missing = []
        for var in self.REQUIRED_ENV_VARS:
            value = getattr(self, var.lower(), None)
            if not value or (isinstance(value, str) and not value.strip()):
                missing.append(var)

        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

        for path_name, path_val in [
            ("DOWNLOAD_FOLDER", self.download_folder),
            ("USER_SKILLS_FOLDER", self.user_skills_folder),
        ]:
            p = Path(path_val)
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)

        self.state_dir = Path(self.user_skills_folder).parent / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(self.user_skills_folder).parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pending_dir = Path(self.user_skills_folder).parent / "pending_approval"
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.rejected_dir = self.log_dir / "rejected"
        self.rejected_dir.mkdir(parents=True, exist_ok=True)

    def _expand_path(self, path_str):
        if not path_str:
            return ""
        return os.path.expanduser(os.path.expandvars(path_str.strip()))

    def get_state_file(self, filename):
        return self.state_dir / filename

    def get_dependency_import_path(self):
        """Return the scripts/ directory of the dependency skill, if exists."""
        dep_path = Path(self.dependency_skill_path)
        if dep_path.exists():
            scripts_dir = dep_path / "scripts"
            if scripts_dir.exists():
                return str(scripts_dir)
        return None

    def get_dependency_env_path(self):
        """Return the .env path of the dependency skill, if exists."""
        dep_path = Path(self.dependency_skill_path)
        env_file = dep_path / ".env"
        if env_file.exists():
            return str(env_file)
        return None

    def get_github_owner(self):
        """
        Read GITHUB_OWNER from dependency skill .env.
        Used only for logging/error messages, never for API calls.
        All API calls are delegated to github-restful-api-connector.
        """
        dep_env = self.get_dependency_env_path()
        if dep_env:
            load_dotenv(dep_env, override=False)
            owner = os.getenv("GITHUB_OWNER", "").strip()
            if owner:
                return owner
        return None

    def get_github_token(self):
        """
        Read GITHUB_TOKEN from dependency skill .env.
        Used only for validation/logging. Never stored locally.
        """
        dep_env = self.get_dependency_env_path()
        if dep_env:
            load_dotenv(dep_env, override=False)
            token = os.getenv("GITHUB_TOKEN", "").strip()
            if token:
                return token
        return None

    def to_dict(self):
        return {
            "download_folder": str(self.download_folder),
            "user_skills_folder": str(self.user_skills_folder),
            "dependency_skill": self.dependency_skill,
            "dependency_skill_path": str(self.dependency_skill_path),
            "log_level": self.log_level,
            "scan_interval": self.scan_interval,
            "pid_file_path": self.pid_file_path,
            "enable_web_fetcher": self.enable_web_fetcher,
            "auto_approve_patch": self.auto_approve_patch,
            "patch_max_files": self.patch_max_files,
        }


def load_config():
    try:
        return SkillOrganizerConfig()
    except ConfigError as e:
        print(f"[CONFIG ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cfg = load_config()
    import json as _json
    print(_json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False))
