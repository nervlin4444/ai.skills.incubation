"""
---
title: "Kimi Login Manager"
name: "kimi-agent-tracker"
description: "Kimi Login Manager，Kimi 平台專用自動化追蹤器組件。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T17:15:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/scripts/kimi_login_manager.py"
  github_path: "kimi-agent-tracker/scripts/kimi_login_manager.py"
---
"""

# -*- coding: utf-8 -*-

import sys
import time
from pathlib import Path

# 動態注入 connector 路徑
connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
if str(connector_path) not in sys.path:
    sys.path.insert(0, str(connector_path))

from browser_connector import BrowserConnector
from profile_manager import url_to_profile_name


def login(profile_name: str = "kimi_com", visible: bool = True,
          stay_open: int = 30, force_login: bool = False) -> bool:
    """Kimi SMS 登入。若已有有效登入態，自動跳過 SMS。"""
    if not force_login:
        if validate_login(profile_name):
            print("[LOGIN] Existing session valid, skipping SMS.")
            return True

    driver = BrowserConnector(profile_name=profile_name, visible=visible)
    context = driver.launch()
    page = driver.navigate("https://www.kimi.com")

    print("[LOGIN] Please enter phone number in terminal when prompted by browser...")
    # 實際 SMS 流程由 Kimi 網頁處理，此處僅等待
    time.sleep(stay_open)

    driver.close()
    print("[LOGIN] Session saved to profile.")
    return True


def validate_login(profile_name: str = "kimi_com") -> bool:
    """快速檢查登入態是否有效。headless 模式執行。"""
    try:
        driver = BrowserConnector(profile_name=profile_name, headless=True)
        driver.launch()
        page = driver.navigate("https://www.kimi.com")
        # 檢查側邊欄是否存在（登入後才有）
        driver.wait_for_selector("[class*='sidebar']", timeout=5000)
        driver.close()
        return True
    except Exception:
        return False


def get_login_expiry_hint(profile_name: str = "kimi_com") -> str:
    """根據 profile 最後修改時間推算有效期。"""
    from profile_manager import validate_profile
    info = validate_profile(profile_name)
    if not info["valid"]:
        return "No valid session found."
    # 簡單估算：7-14 天有效期
    return f"Session last used: {info['last_used']}. Typical expiry: 7-14 days."


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--stay-open", type=int, default=30)
    parser.add_argument("--force-login", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        print("Valid:", validate_login())
    else:
        login(visible=args.visible, stay_open=args.stay_open, force_login=args.force_login)
