#!/usr/bin/env python3
"""
---
title: "Kimi Downloader"
name: "kimi-agent-tracker"
description: "Kimi Downloader，Kimi 平台專用自動化追蹤器組件。v1.0.2 hotfix: 同步版本與 auth_config。"
version: "1.0.2"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T00:10:00+08:00"
fixes: [24]
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "scripts/kimi_downloader.py"
  github_path: "kimi-agent-tracker/scripts/kimi_downloader.py"
---
"""

# -*- coding: utf-8 -*-

import os
import sys
import json
import time
from pathlib import Path

connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
if str(connector_path) not in sys.path:
    sys.path.insert(0, str(connector_path))

from browser_connector import BrowserConnector


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
    time.sleep(3)

    results = {"success": [], "duplicates": [], "errors": []}
    try:
        # v1.0.2: 擴展 selector 覆蓋更多文件連結模式
        selectors = [
            "a[href*='sandbox']",
            "a[href*='download']",
            "a[download]",
            "[class*='file-link']",
            "[class*='attachment']",
        ]
        links = []
        for sel in selectors:
            links.extend(page.query_selector_all(sel))

        # 去重
        seen = set()
        unique_links = []
        for link in links:
            try:
                href = link.get_attribute("href") or ""
                if href and href not in seen:
                    seen.add(href)
                    unique_links.append(link)
            except Exception:
                unique_links.append(link)

        for link in unique_links:
            try:
                href = link.get_attribute("href") or ""
                text = link.inner_text().strip() if hasattr(link, "inner_text") else "unnamed"
                if not href:
                    continue

                if screenshot_only:
                    results["success"].append({"url": href, "name": text, "status": "screenshot_only"})
                    continue

                # 判斷文件類型並處理
                if any(href.endswith(ext) for ext in [".zip", ".py", ".csv"]):
                    result = _handle_direct_download(driver, link)
                elif any(href.endswith(ext) for ext in [".md", ".txt"]):
                    result = _handle_preview_panel_download(driver, link)
                else:
                    result = _handle_direct_download(driver, link)

                if result.get("status") == "success":
                    results["success"].append(result)
                elif result.get("status") == "duplicate":
                    results["duplicates"].append(result)
                else:
                    results["errors"].append(result)
            except Exception as e:
                results["errors"].append({"error": str(e)})

        if diagnose:
            diag_dir = Path(__file__).parent.parent / ".logs" / "diagnose"
            diag_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            driver.dump_html(str(diag_dir / f"download_{ts}.html"))
            driver.screenshot(str(diag_dir / f"download_{ts}.png"))

    except Exception as e:
        if diagnose:
            diag_dir = Path(__file__).parent.parent / ".logs" / "diagnose"
            diag_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            driver.dump_html(str(diag_dir / f"error_{ts}.html"))
            driver.screenshot(str(diag_dir / f"error_{ts}.png"))

    driver.close()
    return results


def download_from_list(list_path: str, profile_name: str = "kimi_com",
                       visible: bool = False) -> dict:
    """讀取 JSON 對話列表，逐個處理。重用同一 browser context。"""
    with open(list_path, "r", encoding="utf-8") as f:
        conversations = json.load(f)

    all_results = {"success": [], "duplicates": [], "errors": []}
    driver = BrowserConnector(profile_name=profile_name, visible=visible)
    driver.launch()

    for conv in conversations:
        try:
            result = download_from_url(conv["url"], profile_name=profile_name, visible=visible)
            all_results["success"].extend(result["success"])
            all_results["duplicates"].extend(result["duplicates"])
            all_results["errors"].extend(result["errors"])
        except Exception as e:
            all_results["errors"].append({"conversation": conv.get("title"), "error": str(e)})

    driver.close()
    return all_results


def _handle_direct_download(driver, link_element) -> dict:
    """處理直接下載類型（.zip/.py/.csv）。使用 expect_download() 捕獲。"""
    try:
        with driver._page.expect_download(timeout=10000) as download_info:
            link_element.click()
        download = download_info.value
        path = download.path()
        return {
            "status": "success",
            "path": str(path),
            "name": download.suggested_filename,
            "conversation": "unknown"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _handle_preview_panel_download(driver, link_element) -> dict:
    """處理預覽面板類型（.md/.txt）。直接點擊優先 + 重試 + 預覽面板備用。"""
    try:
        # 嘗試 1：直接點擊（部分 .md 直接觸發下載）
        for attempt in range(2):
            try:
                with driver._page.expect_download(timeout=5000) as download_info:
                    link_element.click()
                download = download_info.value
                path = download.path()
                return {
                    "status": "success",
                    "path": str(path),
                    "name": download.suggested_filename,
                    "conversation": "unknown"
                }
            except Exception:
                if attempt == 0:
                    time.sleep(2)

        # 嘗試 2：預覽面板流程
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
        path = download.path()
        return {
            "status": "success",
            "path": str(path),
            "name": download.suggested_filename,
            "conversation": "unknown"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str)
    parser.add_argument("--from-list", type=str)
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--screenshot-only", action="store_true")
    args = parser.parse_args()

    if args.url:
        result = download_from_url(
            args.url, visible=args.visible,
            diagnose=args.diagnose, screenshot_only=args.screenshot_only
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.from_list:
        result = download_from_list(args.from_list, visible=args.visible)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
