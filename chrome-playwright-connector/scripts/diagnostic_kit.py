"""
---
title: "Diagnostic Kit"
name: "chrome-playwright-connector"
description: "瀏覽器診斷工具集合，提供頁面診斷、Selector 診斷、按鈕列舉與 JSON 報告保存功能。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T16:39:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/scripts/diagnostic_kit.py"
  github_path: "chrome-playwright-connector/scripts/diagnostic_kit.py"
---
"""

# -*- coding: utf-8 -*-

import os
import json
import time
from pathlib import Path


def _diagnose_dir() -> Path:
    d = Path(__file__).parent.parent / "diagnose"
    d.mkdir(parents=True, exist_ok=True)
    return d


def diagnose_page(page, label: str = None) -> dict:
    """對當前頁面執行完整診斷：截圖 + HTML dump + 元素列舉。"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    prefix = f"{label}_" if label else ""
    diag_dir = _diagnose_dir()

    screenshot_path = str(diag_dir / f"{prefix}{ts}_screenshot.png")
    html_path = str(diag_dir / f"{prefix}{ts}_page.html")
    elements_path = str(diag_dir / f"{prefix}{ts}_elements.txt")

    page.screenshot(path=screenshot_path, full_page=True)

    html = page.content()
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    elements = page.query_selector_all("*")
    with open(elements_path, "w", encoding="utf-8") as f:
        for el in elements:
            tag = el.evaluate("el => el.tagName.toLowerCase()")
            text = el.inner_text() if hasattr(el, "inner_text") else ""
            f.write(f"{tag}: {text[:80]}
")

    return {
        "screenshot": screenshot_path,
        "html": html_path,
        "elements": elements_path,
        "timestamp": ts,
    }


def diagnose_selector(page, selector: str) -> dict:
    """針對特定 selector 診斷：檢查是否存在、是否可見、是否可點擊。"""
    result = {
        "exists": False,
        "visible": False,
        "interactable": False,
        "html": "",
    }
    try:
        el = page.query_selector(selector)
        if el:
            result["exists"] = True
            result["visible"] = el.is_visible()
            result["interactable"] = el.is_enabled() if hasattr(el, "is_enabled") else True
            result["html"] = el.inner_html() if hasattr(el, "inner_html") else ""
    except Exception:
        pass
    return result


def list_buttons(page) -> list:
    """列舉頁面所有按鈕元素（button, div[role=button], a 等）。"""
    selectors = ["button", 'div[role="button"]', "a", 'input[type="submit"]', 'input[type="button"]']
    buttons = []
    for sel in selectors:
        for el in page.query_selector_all(sel):
            try:
                text = el.inner_text() if hasattr(el, "inner_text") else ""
                class_attr = el.get_attribute("class") or ""
                id_attr = el.get_attribute("id") or ""
                buttons.append((text.strip(), class_attr, id_attr, sel))
            except Exception:
                continue
    return buttons


def save_diagnose_report(results: dict, path: str = None) -> str:
    """將診斷結果保存為 JSON 報告。path 為 None 時自動生成。"""
    if path is None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = str(_diagnose_dir() / f"report_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return path


if __name__ == "__main__":
    print("Diagnostic Kit loaded. Use with a Playwright page object.")
