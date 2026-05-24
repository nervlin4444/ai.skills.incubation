"""
---
title: "Kimi Conversation Lister - F002"
name: "kimi-agent-tracker"
description: "從 Kimi 側邊欄提取對話列表。所有 selector 從 config 讀取，禁止硬編碼。"
version: "1.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T02:20:00+08:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{baseDir}/scripts/kimi_conversation_lister.py"
  github_path: "kimi-agent-tracker/scripts/kimi_conversation_lister.py"
---
"""

import sys
import json
import time
import argparse
from pathlib import Path

# 動態注入 connector
connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
if str(connector_path) not in sys.path:
    sys.path.insert(0, str(connector_path))

from browser_connector import BrowserConnector
from profile_manager import url_to_profile_name


def _load_config():
    """讀取統一配置中心。"""
    config_path = Path(__file__).parent.parent / ".config" / "kimi_tracker_config.json"
    defaults = {
        "platform": {"base_url": "https://www.kimi.com"},
        "login": {"profile_name": "kimi_com", "validate_timeout_ms": 5000},
        "selectors": {
            "conversation_items": ".chat-info-item",
            "conversation_title": ".chat-name",
        },
        "daemon": {"conversation_count": 10},
        "state": {"conversations_file": "{baseDir}/.config/conversations.json"},
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
    """將 {baseDir} 佔位符解析為實際路徑。"""
    base = Path(__file__).parent.parent
    return Path(path_tpl.replace("{baseDir}", str(base)))


def extract_conversations(profile_name: str = None, count: int = None,
                           visible: bool = False, diagnose: bool = False) -> list:
    """從 Kimi 側邊欄提取對話列表。"""
    profile = profile_name or CONFIG["login"]["profile_name"]
    max_count = count or CONFIG["daemon"]["conversation_count"]
    base_url = CONFIG["platform"]["base_url"]
    item_sel = CONFIG["selectors"]["conversation_items"]
    title_sel = CONFIG["selectors"]["conversation_title"]

    driver = BrowserConnector(profile_name=profile, visible=visible)
    conversations = []
    diagnose_data = {
        "url": "", "title": "", "item_selector": item_sel,
        "title_selector": title_sel, "items_found": 0,
        "selector_hits": {}, "raw_items": []
    }

    try:
        context = driver.launch()
        page = driver.navigate(base_url)
        page.wait_for_load_state("networkidle", timeout=10000)

        diagnose_data["url"] = page.url
        diagnose_data["title"] = page.title()

        # 等待對話項出現（最多 5 秒）
        try:
            page.wait_for_selector(item_sel, timeout=5000)
        except Exception:
            print(f"[EXTRACT] Selector '{item_sel}' not found within 5s")

        items = page.query_selector_all(item_sel)
        diagnose_data["items_found"] = len(items)
        print(f"[EXTRACT] Found {len(items)} raw items with selector '{item_sel}'")

        for idx, item in enumerate(items[:max_count]):
            try:
                title_el = item.query_selector(title_sel)
                title = title_el.inner_text().strip() if title_el else ""
                href = item.get_attribute("href") or ""
                # 補全為絕對 URL
                if href.startswith("/"):
                    url = f"{base_url}{href}"
                elif href.startswith("http"):
                    url = href
                else:
                    url = f"{base_url}/{href}"

                conv = {
                    "index": idx,
                    "title": title,
                    "url": url,
                    "pinned": False
                }
                conversations.append(conv)
                diagnose_data["raw_items"].append({
                    "title": title, "href": href, "resolved_url": url
                })
            except Exception as e:
                diagnose_data["raw_items"].append({"error": str(e)})

        print(f"[EXTRACT] Extracted {len(conversations)} conversations")

        # 診斷模式：保存詳細報告
        if diagnose:
            diag_dir = _resolve_path(CONFIG["diagnose"]["diagnose_dir"])
            diag_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")

            # 保存 HTML
            html_path = diag_dir / f"sidebar_{ts}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.content())

            # 保存截圖
            screenshot_path = diag_dir / f"sidebar_{ts}.png"
            page.screenshot(path=str(screenshot_path))

            # 保存 JSON 診斷報告
            report_path = diag_dir / f"lister_diagnose_{ts}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(diagnose_data, f, ensure_ascii=False, indent=2)

            print(f"[DIAGNOSE] HTML: {html_path}")
            print(f"[DIAGNOSE] Screenshot: {screenshot_path}")
            print(f"[DIAGNOSE] Report: {report_path}")

    except Exception as e:
        print(f"[EXTRACT] Error: {e}")
    finally:
        try:
            driver.close()
        except Exception:
            pass

    return conversations


def save_conversation_list(conversations: list, path: str = None) -> str:
    """保存對話列表到 JSON。"""
    out_path = path or str(_resolve_path(CONFIG["state"]["conversations_file"]))
    out_dir = Path(out_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(conversations)} conversations to {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Kimi Conversation Lister F-002")
    parser.add_argument("--profile", default=None, help="Profile name")
    parser.add_argument("--count", type=int, default=None, help="Max conversations to extract")
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    parser.add_argument("--diagnose", action="store_true", help="Diagnose mode")
    args = parser.parse_args()

    conversations = extract_conversations(
        profile_name=args.profile,
        count=args.count,
        visible=args.visible,
        diagnose=args.diagnose
    )
    save_conversation_list(conversations)


if __name__ == "__main__":
    main()
