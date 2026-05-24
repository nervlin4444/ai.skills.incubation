"""
---
title: "Kimi Login Manager - F001"
name: "kimi-agent-tracker"
description: "Kimi 平台 SMS 登入與 persistent profile 維護。所有可調參數從 config 讀取，禁止硬編碼。"
version: "1.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T02:05:00+08:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/scripts/kimi_login_manager.py"
  github_path: "kimi-agent-tracker/scripts/kimi_login_manager.py"
---
"""

import sys
import json
import time
import argparse
from pathlib import Path

# ------------------------------------------------------------------
# 動態注入 chrome-playwright-connector
# ------------------------------------------------------------------
connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
if str(connector_path) not in sys.path:
    sys.path.insert(0, str(connector_path))

from browser_connector import BrowserConnector
from profile_manager import url_to_profile_name

# ------------------------------------------------------------------
# 配置加載（禁止硬編碼，全部從 config 讀取）
# ------------------------------------------------------------------
def _load_config():
    """讀取 .config/kimi_tracker_config.json，不存在則返回默認值。"""
    config_path = Path(__file__).parent.parent / ".config" / "kimi_tracker_config.json"
    defaults = {
        "login": {
            "stay_open_default": 300,
            "validate_timeout_ms": 5000,
            "login_check_interval_sec": 3,
            "max_login_wait_sec": 600,
            "visible_default": True,
            "profile_name": "kimi_com"
        },
        "selectors": {
            "login_indicators": [
                ".chat-info-item",
                ".user-avatar",
                ".user-name"
            ],
            "conversation_items": ".chat-info-item",
            "user_avatar": ".user-avatar",
            "user_name": ".user-name"
        },
        "daemon": {
            "interval_sec": 900,
            "visible": False,
            "conversation_count": 10
        }
    }
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            # 深度合併
            for section in defaults:
                if section in user_cfg and isinstance(user_cfg[section], dict):
                    defaults[section].update(user_cfg[section])
        except Exception as e:
            print(f"[WARN] Config load failed: {e}. Using defaults.")
    return defaults


CONFIG = _load_config()

# ------------------------------------------------------------------
# 核心函數
# ------------------------------------------------------------------
def _check_login_success(page) -> bool:
    """組合判斷：對話項 OR 頭像 OR 用戶名，任一命中即判定已登入。"""
    selectors = CONFIG["selectors"]["login_indicators"]
    for sel in selectors:
        try:
            if page.query_selector(sel):
                return True
        except Exception:
            continue
    return False


def validate_login(profile_name: str = None) -> bool:
    """快速檢查登入態是否有效。headless 模式執行，無需人工介入。"""
    profile = profile_name or CONFIG["login"]["profile_name"]
    timeout = CONFIG["login"]["validate_timeout_ms"]
    driver = BrowserConnector(profile_name=profile, visible=False)
    try:
        context = driver.launch()
        page = driver.navigate("https://www.kimi.com/")
        # 等待頁面穩定
        page.wait_for_load_state("networkidle", timeout=timeout)
        result = _check_login_success(page)
        print(f"[VALIDATE] Login valid: {result}")
        return result
    except Exception as e:
        print(f"[VALIDATE] Error: {e}")
        return False
    finally:
        try:
            driver.close()
        except Exception:
            pass


def login(profile_name: str = None, visible: bool = None,
          stay_open: int = None, force_login: bool = False,
          diagnose: bool = False) -> bool:
    """啟動瀏覽器，導航到 Kimi，循環檢測登入態完成。"""
    profile = profile_name or CONFIG["login"]["profile_name"]
    vis = visible if visible is not None else CONFIG["login"]["visible_default"]
    stay = stay_open if stay_open is not None else CONFIG["login"]["stay_open_default"]
    interval = CONFIG["login"]["login_check_interval_sec"]
    max_wait = CONFIG["login"]["max_login_wait_sec"]

    # 非強制模式先驗證
    if not force_login:
        if validate_login(profile):
            print("[LOGIN] Existing session valid, skipping SMS.")
            return True

    driver = BrowserConnector(profile_name=profile, visible=vis)
    try:
        context = driver.launch()
        page = driver.navigate("https://www.kimi.com/")
        print(f"[LOGIN] Browser opened. Please complete SMS login within {max_wait}s.")
        print(f"[LOGIN] Checking every {interval}s...")

        elapsed = 0
        while elapsed < max_wait:
            time.sleep(interval)
            elapsed += interval
            if _check_login_success(page):
                print(f"[LOGIN] Login detected after {elapsed}s. Session saved.")
                return True
            print(f"[LOGIN] Waiting... {elapsed}s / {max_wait}s")

        print(f"[LOGIN] Timeout after {max_wait}s. Login not detected.")
        return False
    except Exception as e:
        print(f"[LOGIN] Error: {e}")
        return False
    finally:
        try:
            driver.close()
        except Exception:
            pass


def diagnose_login_page(profile_name: str = None) -> dict:
    """診斷模式：導出登入頁面 HTML + 元素統計。"""
    profile = profile_name or CONFIG["login"]["profile_name"]
    driver = BrowserConnector(profile_name=profile, visible=False)
    results = {
        "login_detected": False,
        "method": "none",
        "conversation_items": 0,
        "avatar_elements": 0,
        "user_name_elements": 0,
        "url": "",
        "title": "",
        "selector_hits": {}
    }
    try:
        context = driver.launch()
        page = driver.navigate("https://www.kimi.com/")
        page.wait_for_load_state("networkidle", timeout=10000)

        results["url"] = page.url
        results["title"] = page.title()

        # 統計各 selector 命中數
        for sel in CONFIG["selectors"]["login_indicators"]:
            try:
                count = len(page.query_selector_all(sel))
                results["selector_hits"][sel] = count
            except Exception:
                results["selector_hits"][sel] = -1

        results["conversation_items"] = results["selector_hits"].get(".chat-info-item", 0)
        results["avatar_elements"] = results["selector_hits"].get(".user-avatar", 0)
        results["user_name_elements"] = results["selector_hits"].get(".user-name", 0)

        if _check_login_success(page):
            results["login_detected"] = True
            results["method"] = "composite"

        # 保存診斷 HTML
        log_dir = Path(__file__).parent.parent / ".logs" / "diagnose"
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        html_path = log_dir / f"login_diagnose_{ts}.html"
        screenshot_path = log_dir / f"login_diagnose_{ts}.png"
        html_content = page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        page.screenshot(path=str(screenshot_path))
        results["html_path"] = str(html_path)
        results["screenshot_path"] = str(screenshot_path)

        print(f"[DIAGNOSE] Login detected: {results['login_detected']}")
        print(f"[DIAGNOSE] Method: {results['method']}")
        print(f"[DIAGNOSE] Conversation items: {results['conversation_items']}")
        print(f"[DIAGNOSE] Avatar elements: {results['avatar_elements']}")
        print(f"[DIAGNOSE] User name elements: {results['user_name_elements']}")
        print(f"[DIAGNOSE] HTML saved: {html_path}")
        print(f"[DIAGNOSE] Screenshot saved: {screenshot_path}")
        return results
    except Exception as e:
        print(f"[DIAGNOSE] Error: {e}")
        return results
    finally:
        try:
            driver.close()
        except Exception:
            pass


# ------------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Kimi Login Manager F-001")
    parser.add_argument("--profile", default=None, help="Profile name")
    parser.add_argument("--visible", action="store_true", default=None, help="Show browser window")
    parser.add_argument("--stay-open", type=int, default=None, help="Max wait seconds for login")
    parser.add_argument("--force-login", action="store_true", help="Force re-login")
    parser.add_argument("--validate", action="store_true", help="Validate existing session")
    parser.add_argument("--diagnose", action="store_true", help="Diagnose login page")
    args = parser.parse_args()

    if args.validate:
        result = validate_login(args.profile)
        sys.exit(0 if result else 1)
    elif args.diagnose:
        diagnose_login_page(args.profile)
    else:
        result = login(
            profile_name=args.profile,
            visible=args.visible,
            stay_open=args.stay_open,
            force_login=args.force_login
        )
        sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
