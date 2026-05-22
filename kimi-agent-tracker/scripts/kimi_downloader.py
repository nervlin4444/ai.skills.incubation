"""
---
title: "Kimi Downloader"
name: "kimi-agent-tracker"
description: "Kimi Downloader，Kimi 平台專用自動化追蹤器組件。"
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
  local_path: "{baseDir}/scripts/kimi_downloader.py"
  github_path: "kimi-agent-tracker/scripts/kimi_downloader.py"
---
"""

# -*- coding: utf-8 -*-

import sys
import os
import time
import json
from pathlib import Path

connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
if str(connector_path) not in sys.path:
    sys.path.insert(0, str(connector_path))

from browser_connector import BrowserConnector
from state_manager import load_state, save_state, get_unique_filename, register_download


def _default_download_dir() -> str:
    base = Path(__file__).parent.parent
    d = base / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def download_from_url(url: str, profile_name: str = "kimi_com",
                      visible: bool = False, diagnose: bool = False,
                      screenshot_only: bool = False) -> dict:
    """訪問單個對話 URL，掃描所有可下載文件並執行下載。"""
    driver = BrowserConnector(profile_name=profile_name, visible=visible)
    driver.launch()
    page = driver.navigate(url)

    result = {"success": [], "duplicates": [], "errors": []}
    state = load_state()

    try:
        # 掃描文件連結
        links = page.query_selector_all("a[href*='sandbox'], a[download], [class*='file']")

        for link in links:
            try:
                href = link.get_attribute("href") or ""
                text = link.inner_text() or "unnamed"

                if screenshot_only:
                    driver.screenshot(f"link_{text[:20]}.png")
                    continue

                # 判斷文件類型並處理
                if href.endswith((".zip", ".py", ".csv")):
                    res = _handle_direct_download(driver, link)
                else:
                    res = _handle_preview_panel_download(driver, link)

                if res.get("path"):
                    state = register_download(state, res["path"], conversation=url)
                    if res.get("duplicate"):
                        result["duplicates"].append(res)
                    else:
                        result["success"].append(res)

            except Exception as e:
                result["errors"].append({"url": url, "error": str(e)})
                if diagnose:
                    driver.screenshot()
                    driver.dump_html()

        driver.close()
        save_state(state)
        return result

    except Exception as e:
        if diagnose:
            driver.screenshot()
            driver.dump_html()
        driver.close()
        raise e


def _handle_direct_download(driver, link_element) -> dict:
    """處理直接下載類型（.zip/.py/.csv）。"""
    download_dir = _default_download_dir()
    filename = get_unique_filename(download_dir, "download.bin")
    save_path = os.path.join(download_dir, filename)

    try:
        with driver._page.expect_download(timeout=10000) as download_info:
            link_element.click()
        download = download_info.value
        download.save_as(save_path)
        return {"path": save_path, "filename": filename, "duplicate": False}
    except Exception as e:
        return {"path": None, "error": str(e)}


def _handle_preview_panel_download(driver, link_element) -> dict:
    """處理預覽面板類型（.md/.txt）。策略：直接點擊優先 → 重試 → 預覽面板備用。"""
    download_dir = _default_download_dir()
    filename = get_unique_filename(download_dir, "download.md")
    save_path = os.path.join(download_dir, filename)

    # 嘗試 1：直接點擊
    for attempt in range(2):
        try:
            with driver._page.expect_download(timeout=5000) as download_info:
                link_element.click()
            download = download_info.value
            download.save_as(save_path)
            return {"path": save_path, "filename": filename, "duplicate": False}
        except Exception:
            time.sleep(2)

    # 嘗試 2：預覽面板流程
    try:
        link_element.click()
        time.sleep(1)
        # 點擊預覽面板下載圖標
        driver.click("svg[name='Download']", force=True)
        time.sleep(0.5)
        # 選擇 Markdown 格式
        driver.click("text=Save as Markdown", force=True)

        with driver._page.expect_download(timeout=10000) as download_info:
            pass
        download = download_info.value
        download.save_as(save_path)
        return {"path": save_path, "filename": filename, "duplicate": False}
    except Exception as e:
        return {"path": None, "error": str(e)}


def download_from_list(list_path: str, profile_name: str = "kimi_com",
                       visible: bool = False) -> dict:
    """讀取 JSON 對話列表，逐個處理。"""
    with open(list_path, "r", encoding="utf-8") as f:
        conversations = json.load(f)

    total = {"success": [], "duplicates": [], "errors": []}

    for conv in conversations:
        print(f"Processing: {conv['title']}")
        try:
            res = download_from_url(conv["url"], profile_name=profile_name, visible=visible)
            total["success"].extend(res["success"])
            total["duplicates"].extend(res["duplicates"])
            total["errors"].extend(res["errors"])
        except Exception as e:
            total["errors"].append({"url": conv["url"], "error": str(e)})

    return total


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, default=None)
    parser.add_argument("--from-list", type=str, default=None)
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--screenshot-only", action="store_true")
    args = parser.parse_args()

    if args.url:
        result = download_from_url(args.url, visible=args.visible, diagnose=args.diagnose, screenshot_only=args.screenshot_only)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.from_list:
        result = download_from_list(args.from_list, visible=args.visible)
        print(f"Success: {len(result['success'])}, Duplicates: {len(result['duplicates'])}, Errors: {len(result['errors'])}")
    else:
        parser.print_help()
