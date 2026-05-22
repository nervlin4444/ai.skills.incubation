"""
---
title: "Kimi Conversation Lister"
name: "kimi-agent-tracker"
description: "Kimi Conversation Lister，Kimi 平台專用自動化追蹤器組件。"
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
  local_path: "{baseDir}/scripts/kimi_conversation_lister.py"
  github_path: "kimi-agent-tracker/scripts/kimi_conversation_lister.py"
---
"""

# -*- coding: utf-8 -*-

import sys
import json
import time
from pathlib import Path

connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
if str(connector_path) not in sys.path:
    sys.path.insert(0, str(connector_path))

from browser_connector import BrowserConnector


def extract_conversations(profile_name: str = "kimi_com",
                          count: int = 10, visible: bool = False,
                          diagnose: bool = False) -> list:
    """從 Kimi 側邊欄提取對話列表。"""
    driver = BrowserConnector(profile_name=profile_name, visible=visible)
    driver.launch()
    page = driver.navigate("https://www.kimi.com")

    try:
        # 等待側邊欄加載
        driver.wait_for_selector("[class*='sidebar']", timeout=10000)

        # 提取對話元素（基於觀察到的 Kimi UI 結構）
        conversations = []
        items = page.query_selector_all("[class*='conversation-item'], [class*='chat-item']")

        for idx, item in enumerate(items[:count]):
            try:
                title_el = item.query_selector("[class*='title'], span, div")
                title = title_el.inner_text() if title_el else f"Conversation {idx}"

                link_el = item.query_selector("a")
                url = link_el.get_attribute("href") if link_el else ""
                if url and not url.startswith("http"):
                    url = "https://www.kimi.com" + url

                pinned = "pinned" in (item.get_attribute("class") or "").lower()

                conversations.append({
                    "index": idx,
                    "title": title.strip(),
                    "url": url,
                    "pinned": pinned,
                })
            except Exception:
                continue

        if diagnose and not conversations:
            driver.dump_html()
            driver.screenshot()

        driver.close()
        return conversations

    except Exception as e:
        if diagnose:
            driver.dump_html()
            driver.screenshot()
        driver.close()
        raise e


def save_conversation_list(conversations: list, path: str = None) -> str:
    """保存對話列表為 JSON。"""
    if path is None:
        base = Path(__file__).parent.parent
        config_dir = base / ".config"
        config_dir.mkdir(parents=True, exist_ok=True)
        path = str(config_dir / "conversations.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    conversations = extract_conversations(count=args.count, visible=args.visible, diagnose=args.diagnose)
    path = save_conversation_list(conversations, args.output)
    print(f"Saved {len(conversations)} conversations to {path}")
    for c in conversations:
        print(f"  [{c['index']}] {'[PIN]' if c['pinned'] else '    '} {c['title']}")
