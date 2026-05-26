#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""---
title: Skill Profile Extractor
name: agent-skill-acquiring
description: Scan skill directories, extract frontmatter, run security checks, and update skill_profile.json.
version: v2.0.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T12:10:00+08:00
fixes: []
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/scripts/skill_profile_extract.py"
  github_path: "agent-skill-acquiring/scripts/skill_profile_extract.py"
---"""

"""
skill_profile_extract.py
Extract skill metadata from directories and update profile.
"""

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from core_profile_io import load_profile, save_profile, update_skill


def _get_platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    elif sys.platform == "darwin":
        return "macos"
    return "linux"


def _expand_path(path_str: str) -> Path:
    if sys.platform.startswith("win"):
        def _repl(m):
            return os.environ.get(m.group(1), m.group(0))
        path_str = re.sub(r'%([^%]+)%', _repl, path_str)
    return Path(os.path.expandvars(os.path.expanduser(path_str)))


def _load_config() -> Dict[str, Any]:
    script_dir = Path(__file__).resolve().parent
    config_path = script_dir.parent / "config" / "acquiring.config.json"
    if not config_path.exists():
        config_path = script_dir / "acquiring.config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _get_scan_paths() -> Tuple[List[Path], List[Path]]:
    cfg = _load_config()
    scan = cfg.get("scan_paths", {})
    platform = _get_platform()
    ws = cfg.get("workstation_defaults", {}).get(platform, {})
    skills_folder = ws.get("skills_folder", "~/.workbuddy/skills")
    skills_folder = _expand_path(skills_folder)
    user_paths = []
    for p in scan.get("user", ["{skills_folder}/user"]):
        user_paths.append(_expand_path(p.replace("{skills_folder}", str(skills_folder))))
    external_paths = []
    for p in scan.get("external", ["{skills_folder}/vendor", "{skills_folder}/shared"]):
        external_paths.append(_expand_path(p.replace("{skills_folder}", str(skills_folder))))
    return user_paths, external_paths


def _try_import_frontmatter_extractor():
    candidates = [
        Path("~/.workbuddy/skills/agent-skill-improving/scripts/skill_files_designer.py").expanduser(),
        Path("~/.local/share/openclaw/skills/agent-skill-improving/scripts/skill_files_designer.py").expanduser(),
        Path(__file__).resolve().parent.parent.parent / "agent-skill-improving" / "scripts" / "skill_files_designer.py",
    ]
    for p in candidates:
        if p.exists():
            try:
                spec = importlib.util.spec_from_file_location("skill_files_designer", p)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.SkillFrontmatterExtractor
            except Exception:
                continue
    return None


def _find_skill_files(skill_dir: Path) -> List[Path]:
    files = []
    if not skill_dir.exists() or not skill_dir.is_dir():
        return files
    for item in skill_dir.iterdir():
        if item.is_file() and item.suffix in (".md", ".py"):
            files.append(item)
        elif item.is_dir() and item.name not in ("__pycache__", ".git", "node_modules", "data", "logs", "assets"):
            files.extend(_find_skill_files(item))
    return files


def _extract_frontmatter_builtin(file_path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    if file_path.suffix == ".md":
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                return _parse_yaml_frontmatter(content[3:end].strip())
        return None
    if file_path.suffix == ".py":
        match = re.search(r'""".*?---\n(.*?)\n---.*?"""', content, re.DOTALL)
        if not match:
            match = re.search(r"'''.*?---\n(.*?)\n---.*?'''", content, re.DOTALL)
        if match:
            return _parse_yaml_frontmatter(match.group(1).strip())
        return None
    return None


def _parse_yaml_frontmatter(yaml_text: str) -> Dict[str, Any]:
    result = {}
    current_key = None
    for line in yaml_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_key:
                if current_key not in result:
                    result[current_key] = []
                val = stripped[2:].strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                result[current_key].append(val)
            continue
        if ":" in stripped:
            key, val = stripped.split(":", 1)
            current_key = key.strip()
            val = val.strip()
            if val:
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                result[current_key] = val
                current_key = None
            else:
                result[current_key] = []
    return result


def _extract_frontmatter(file_path: Path) -> Optional[Dict[str, Any]]:
    extractor_class = _try_import_frontmatter_extractor()
    if extractor_class:
        try:
            extractor = extractor_class()
            return extractor.extract(file_path)
        except Exception:
            pass
    return _extract_frontmatter_builtin(file_path)


def _security_check(skill_dir: Path, dangerous_patterns: List[str]) -> Tuple[bool, List[str]]:
    warnings = []
    files = _find_skill_files(skill_dir)
    for fp in files:
        if fp.suffix != ".py":
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        for pattern in dangerous_patterns:
            if pattern in content:
                warnings.append(f"Found dangerous pattern '{pattern}' in {fp.name}")
    return (len(warnings) == 0), warnings


def _extract_keywords(name: str, description: str) -> List[str]:
    keywords = set()
    for sep in [".", "_", "-"]:
        if sep in name:
            for part in name.split(sep):
                if len(part) > 1:
                    keywords.add(part.lower())
    if description:
        for word in re.findall(r"[a-zA-Z]{2,}", description):
            keywords.add(word.lower())
        for phrase in re.findall(r"[\u4e00-\u9fff]{2,}", description):
            keywords.add(phrase)
    return sorted(keywords)


def _make_summary(text: str, max_chars: int = 10) -> str:
    if not text:
        return ""
    return text[:max_chars]


def _scan_skill_directory(skill_dir: Path, source: str, dangerous_patterns: List[str]) -> Optional[Dict[str, Any]]:
    if not skill_dir.exists() or not skill_dir.is_dir():
        return None
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    frontmatter = None
    if skill_md.exists():
        frontmatter = _extract_frontmatter(skill_md)
    if not frontmatter:
        for py_file in skill_dir.glob("*.py"):
            frontmatter = _extract_frontmatter(py_file)
            if frontmatter:
                break
    has_identity = frontmatter is not None and "name" in frontmatter
    passed, warnings = _security_check(skill_dir, dangerous_patterns)
    description = ""
    if frontmatter:
        description = frontmatter.get("description", "")
    now = datetime.now(timezone.utc).isoformat()
    meta = {
        "name": skill_name,
        "source": source,
        "has_identity": has_identity,
        "location": str(skill_dir),
        "keywords": _extract_keywords(skill_name, description),
        "skill_summary": _make_summary(description, 10),
        "function_summary": _make_summary(description, 10),
        "alias": "",
        "security_passed": passed,
        "security_warnings": warnings,
        "registered_at": now,
        "updated_at": now
    }
    if frontmatter:
        meta["version"] = frontmatter.get("version", "")
        meta["github_repository"] = frontmatter.get("github_repository", "")
        meta["description"] = description
    return meta


def extract(names: Optional[List[str]] = None) -> Dict[str, Any]:
    user_paths, external_paths = _get_scan_paths()
    cfg = _load_config()
    dangerous_patterns = cfg.get("extract", {}).get("dangerous_patterns", [
        "os.system(", "subprocess.call(", "eval(", "exec(",
        "__import__('os').system", "rm -rf", "shutil.rmtree"
    ])
    profile = load_profile()
    for base_path in user_paths:
        if not base_path.exists():
            continue
        for skill_dir in base_path.iterdir():
            if not skill_dir.is_dir():
                continue
            if names and skill_dir.name not in names:
                continue
            meta = _scan_skill_directory(skill_dir, "user", dangerous_patterns)
            if meta:
                existing = profile.get(skill_dir.name, {})
                if "registered_at" in existing:
                    meta["registered_at"] = existing["registered_at"]
                profile = update_skill(profile, skill_dir.name, meta)
    for base_path in external_paths:
        if not base_path.exists():
            continue
        for skill_dir in base_path.iterdir():
            if not skill_dir.is_dir():
                continue
            if names and skill_dir.name not in names:
                continue
            meta = _scan_skill_directory(skill_dir, "external", dangerous_patterns)
            if meta:
                existing = profile.get(skill_dir.name, {})
                if "registered_at" in existing:
                    meta["registered_at"] = existing["registered_at"]
                profile = update_skill(profile, skill_dir.name, meta)
    save_profile(profile)
    return profile


def main():
    parser = argparse.ArgumentParser(description="Extract skill metadata from directories")
    parser.add_argument("--names", nargs="*", help="Specific skill names to extract (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()
    profile = extract(args.names)
    if args.dry_run:
        print("[DRY-RUN] Preview only. Profile not saved.")
    count = len(profile)
    user_count = sum(1 for v in profile.values() if v.get("source") == "user")
    ext_count = sum(1 for v in profile.values() if v.get("source") == "external")
    print(f"[OK] Profile updated: {count} skills total ({user_count} user, {ext_count} external)")


if __name__ == "__main__":
    main()
