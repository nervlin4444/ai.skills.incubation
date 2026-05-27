"""
---
title: "Kimi Login Manager - F001"
name: "kimi-agent-tracker"
description: "Kimi 平台 SMS 登入與 persistent profile 維護。config 分離，診斷增強。"
version: "4.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-26T06:53:23.027+00:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
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

connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
if str(connector_path) not in sys.path:
    sys.path.insert(0, str(connector_path))

from browser_connector import BrowserConnector
from profile_manager import url_to_profile_name


def _load_config():
    config_path = Path(__file__).parent.parent / ".config" / "kimi_tracker_config.json"
    defaults = {
        "platform": {"base_url": "https://www.kimi.com"},
        "login": {
            "stay_open_default": 300,
            "validate_timeout_ms": 5000,
            "login_check_interval_sec": 3,
            "max_login_wait_sec": 600,
            "visible_default": True,
            "profile_name": "kimi_com"
        },
        "selectors": {
            "login_indicators": [".chat-info-item", ".user-avatar", ".user-name"]
        },
        "diagnose": {"diagnose_dir": "{baseDir}/.logs/diagnose"}
    }
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            for section in defaults:
                if section in user_cfg and isinstance(user_cfg[section], dict):
                    defaults[section].update(user_cfg[section])
        except Exception as e:
            print(f"[WARN] Config load failed: {e}. Using defaults.")
    return defaults


CONFIG = _load_config()


def _resolve_path(path_tpl: str) -> Path:
    base = Path(__file__).parent.parent
    return Path(path_tpl.replace("{baseDir}", str(base)))


# ------------------------------------------------------------------
# 核心檢測函數（帶詳細診斷輸出）
# ------------------------------------------------------------------
def _check_login_success(page, verbose: bool = False) -> bool:
    """組合判斷：對話項 OR 頭像 OR 用戶名，任一命中即判定已登入。
    verbose=True 時輸出每個 selector 的詳細結果。"""
    selectors = CONFIG["selectors"]["login_indicators"]
    results = {}
    for sel in selectors:
        try:
            # 先嘗試 query_selector（單個）
            el = page.query_selector(sel)
            if el:
                # 進一步驗證元素是否可見且有內容
                try:
                    text = el.inner_text().strip() if hasattr(el, "inner_text") else ""
                    visible = el.is_visible() if hasattr(el, "is_visible") else True
                    results[sel] = {"found": True, "text": text[:50], "visible": visible}
                    if verbose:
                        print(f"  [CHECK] {sel}: FOUND (text='{text[:30]}...', visible={visible})")
                    return True
                except Exception as inner_e:
                    results[sel] = {"found": True, "error": str(inner_e)}
                    if verbose:
                        print(f"  [CHECK] {sel}: FOUND but inner check failed: {inner_e}")
                    return True  # 至少找到了
            else:
                # 嘗試 query_selector_all 統計數量
                all_els = page.query_selector_all(sel)
                count = len(all_els)
                results[sel] = {"found": False, "count": count}
                if verbose:
                    print(f"  [CHECK] {sel}: NOT FOUND (query_selector_all count={count})")
        except Exception as e:
            results[sel] = {"found": False, "error": str(e)}
            if verbose:
                print(f"  [CHECK] {sel}: EXCEPTION - {e}")

    if verbose:
        print(f"  [CHECK] Summary: {json.dumps(results, ensure_ascii=False)}")
    return False


# ------------------------------------------------------------------
# validate_login — 支持 visible 參數傳入
# ------------------------------------------------------------------
def validate_login(profile_name: str = None, visible: bool = False) -> bool:
    """快速檢查登入態。visible=True 用於排查 headless 問題。"""
    profile = profile_name or CONFIG["login"]["profile_name"]
    timeout = CONFIG["login"]["validate_timeout_ms"]
    driver = BrowserConnector(profile_name=profile, visible=visible)
    try:
        context = driver.launch()
        page = driver.navigate(CONFIG["platform"]["base_url"])
        page.wait_for_load_state("networkidle", timeout=timeout)
        result = _check_login_success(page, verbose=True)
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


# ------------------------------------------------------------------
# login — 循環檢測，帶詳細日誌
# ------------------------------------------------------------------
def login(profile_name: str = None, visible: bool = None,
          stay_open: int = None, force_login: bool = False,
          diagnose: bool = False) -> bool:
    profile = profile_name or CONFIG["login"]["profile_name"]
    vis = visible if visible is not None else CONFIG["login"]["visible_default"]
    stay = stay_open if stay_open is not None else CONFIG["login"]["stay_open_default"]
    interval = CONFIG["login"]["login_check_interval_sec"]
    max_wait = CONFIG["login"]["max_login_wait_sec"]

    # 非強制模式先驗證
    if not force_login:
        print("[LOGIN] Checking existing session...")
        if validate_login(profile, visible=vis):
            print("[LOGIN] Existing session valid, skipping SMS.")
            return True
        print("[LOGIN] No valid session found, opening browser for SMS login.")

    driver = BrowserConnector(profile_name=profile, visible=vis)
    try:
        context = driver.launch()
        page = driver.navigate(CONFIG["platform"]["base_url"])
        print(f"[LOGIN] Browser opened. Please complete SMS login within {max_wait}s.")
        print(f"[LOGIN] Checking every {interval}s with selectors: {CONFIG['selectors']['login_indicators']}")

        elapsed = 0
        while elapsed < max_wait:
            time.sleep(interval)
            elapsed += interval

            # 詳細檢測輸出
            print(f"[LOGIN] Checking login state at {elapsed}s...")
            if _check_login_success(page, verbose=True):
                print(f"[LOGIN] Login detected after {elapsed}s. Session saved.")
                return True
            print(f"[LOGIN] Still waiting... ({elapsed}/{max_wait}s)")

        print(f"[LOGIN] Timeout after {max_wait}s. Login not detected.")
        return False
    except Exception as e:
        print(f"[LOGIN] Fatal error: {e}")
        return False
    finally:
        try:
            driver.close()
        except Exception:
            pass


# ------------------------------------------------------------------
# diagnose_login_page — 增強診斷
# ------------------------------------------------------------------
def diagnose_login_page(profile_name: str = None) -> dict:
    profile = profile_name or CONFIG["login"]["profile_name"]
    driver = BrowserConnector(profile_name=profile, visible=False)
    results = {
        "login_detected": False,
        "url": "",
        "title": "",
        "selector_results": {},
        "html_path": "",
        "screenshot_path": ""
    }
    try:
        context = driver.launch()
        page = driver.navigate(CONFIG["platform"]["base_url"])
        page.wait_for_load_state("networkidle", timeout=10000)

        results["url"] = page.url
        results["title"] = page.title()

        print(f"[DIAGNOSE] URL: {results['url']}")
        print(f"[DIAGNOSE] Title: {results['title']}")

        # 詳細 selector 檢測
        selectors = CONFIG["selectors"]["login_indicators"]
        for sel in selectors:
            try:
                count = len(page.query_selector_all(sel))
                single = page.query_selector(sel)
                text = ""
                if single:
                    try:
                        text = single.inner_text().strip()[:50]
                    except:
                        pass
                results["selector_results"][sel] = {
                    "count": count,
                    "single_found": single is not None,
                    "sample_text": text
                }
                print(f"[DIAGNOSE] {sel}: count={count}, single={single is not None}, text='{text}'")
            except Exception as e:
                results["selector_results"][sel] = {"error": str(e)}
                print(f"[DIAGNOSE] {sel}: ERROR - {e}")

        results["login_detected"] = _check_login_success(page, verbose=False)
        print(f"[DIAGNOSE] Login detected: {results['login_detected']}")

        # 保存診斷文件
        log_dir = _resolve_path(CONFIG["diagnose"]["diagnose_dir"])
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")

        html_path = log_dir / f"login_diagnose_{ts}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page.content())

        screenshot_path = log_dir / f"login_diagnose_{ts}.png"
        page.screenshot(path=str(screenshot_path))

        results["html_path"] = str(html_path)
        results["screenshot_path"] = str(screenshot_path)
        print(f"[DIAGNOSE] HTML saved: {html_path}")
        print(f"[DIAGNOSE] Screenshot saved: {screenshot_path}")

        return results
    except Exception as e:
        print(f"[DIAGNOSE] Fatal error: {e}")
        return results
    finally:
        try:
            driver.close()
        except Exception:
            pass


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Kimi Login Manager F-001 v1.1.1")
    parser.add_argument("--profile", default=None, help="Profile name")
    parser.add_argument("--visible", action="store_true", default=None, help="Show browser window")
    parser.add_argument("--stay-open", type=int, default=None, help="Max wait seconds")
    parser.add_argument("--force-login", action="store_true", help="Force re-login")
    parser.add_argument("--validate", action="store_true", help="Validate existing session")
    parser.add_argument("--diagnose", action="store_true", help="Diagnose login page")
    args = parser.parse_args()

    if args.validate:
        # 重要：--validate 也支持 --visible 參數
        vis = args.visible if args.visible is not None else False
        result = validate_login(args.profile, visible=vis)
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
