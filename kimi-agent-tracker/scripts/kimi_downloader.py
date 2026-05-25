"""
---
title: "Kimi Downloader - F003"
name: "kimi-agent-tracker"
description: "Auto-download sandbox files. Fixed asyncio loop conflict with nest_asyncio."
version: "1.1.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T11:25:00+08:00"
auth_config:
  provider: "local"
  auth_method: "none"
  token_env_var: "N/A"
  env_file_path: "N/A"
file_mapping:
  local_path: "{baseDir}/scripts/kimi_downloader.py"
  github_path: "kimi-agent-tracker/scripts/kimi_downloader.py"
---
"""

# FIX: Apply nest_asyncio before any playwright import
try:
    import nest_asyncio
    nest_asyncio.apply()
    _NEST_OK = True
except ImportError:
    _NEST_OK = False
    print("[WARN] nest_asyncio not installed. Run: python3 -m pip install nest-asyncio --user")

import sys, json, time, hashlib, argparse
from pathlib import Path

connector_path = Path(__file__).parent.parent.parent / "chrome-playwright-connector" / "scripts"
if str(connector_path) not in sys.path:
    sys.path.insert(0, str(connector_path))

from browser_connector import BrowserConnector

def _load_config():
    config_path = Path(__file__).parent.parent / ".config" / "kimi_tracker_config.json"
    defaults = {
        "platform": {"base_url": "https://www.kimi.com"},
        "login": {"profile_name": "kimi_com"},
        "download": {"download_timeout_ms": 10000},
        "daemon": {"download_dir": "{baseDir}/downloads", "duplicate_dir": "{baseDir}/.duplicate"},
        "state": {"state_file": "{baseDir}/.config/downloads.json"},
        "diagnose": {"diagnose_dir": "{baseDir}/.logs/diagnose"}
    }
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f2:
                user_cfg = json.load(f2)
            for section in defaults:
                if section in user_cfg and isinstance(user_cfg[section], dict):
                    defaults[section].update(user_cfg[section])
        except Exception as e:
            print(f"[WARN] Config load failed: {e}")
    return defaults

CONFIG = _load_config()

def _resolve_path(path_tpl: str) -> Path:
    base = Path(__file__).parent.parent
    return Path(path_tpl.replace("{baseDir}", str(base)))

def _find_file_links(page) -> list:
    links = []
    for link in page.query_selector_all("a[href*='sandbox://']"):
        try:
            href = link.get_attribute("href") or ""
            text = link.inner_text().strip() or "unnamed"
            if "sandbox://" in href:
                links.append({"href": href, "text": text, "element": link})
        except Exception:
            continue
    return links

def download_from_url(url: str, profile_name=None, visible=False, diagnose=False):
    profile = profile_name or CONFIG["login"]["profile_name"]
    driver = BrowserConnector(profile_name=profile, visible=visible)
    result = {"success": [], "duplicates": [], "errors": []}
    download_dir = _resolve_path(CONFIG["daemon"]["download_dir"])
    download_dir.mkdir(parents=True, exist_ok=True)

    try:
        context = driver.launch()
        page = driver.navigate(url)
        page.wait_for_load_state("networkidle", timeout=15000)
        print(f"[DOWNLOAD] Navigated to: {url}")

        file_links = _find_file_links(page)
        print(f"[DOWNLOAD] Found {len(file_links)} file links")

        if not file_links:
            print("[DOWNLOAD] No files found")
            return result

        for link_info in file_links:
            try:
                href = link_info["href"]
                text = link_info["text"]
                file_name = href.split("/")[-1] or "download"
                if "." not in file_name:
                    file_name = f"download_{int(time.time())}.bin"

                link_info["element"].click()
                time.sleep(2)
                print(f"[DOWNLOAD] Triggered: {text} -> {href}")
                result["success"].append({"file": file_name, "href": href})
            except Exception as e:
                result["errors"].append({"file": link_info.get("text", ""), "error": str(e)})
                print(f"[DOWNLOAD] Error: {e}")

        if diagnose:
            diag_dir = _resolve_path(CONFIG["diagnose"]["diagnose_dir"])
            diag_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            with open(diag_dir / f"download_page_{ts}.html", "w", encoding="utf-8") as f2:
                f2.write(page.content())
            page.screenshot(path=str(diag_dir / f"download_page_{ts}.png"))

    except Exception as e:
        print(f"[DOWNLOAD] Fatal error: {e}")
        result["errors"].append({"fatal": str(e)})
    finally:
        try:
            driver.close()
        except Exception:
            pass

    print(f"[DOWNLOAD] Result: {len(result['success'])} success, {len(result['errors'])} errors")
    return result

def download_from_list(list_path=None, profile_name=None, visible=False):
    list_file = list_path or str(_resolve_path(CONFIG["state"]["conversations_file"]))
    if not Path(list_file).exists():
        print(f"[DOWNLOAD] List not found: {list_file}")
        return {"success": [], "duplicates": [], "errors": []}

    with open(list_file, "r", encoding="utf-8") as f2:
        conversations = json.load(f2)

    total = {"success": [], "duplicates": [], "errors": []}
    for conv in conversations:
        print(f"[DOWNLOAD] Processing: {conv.get('title', 'Unknown')}")
        result = download_from_url(conv["url"], profile_name, visible)
        for key in total:
            total[key].extend(result.get(key, []))
    print(f"[DOWNLOAD] Batch: {len(total['success'])} success, {len(total['errors'])} errors")
    return total

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--from-list")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--diagnose", action="store_true")
    args = parser.parse_args()

    if args.url:
        download_from_url(args.url, args.profile, args.visible, args.diagnose)
    elif args.from_list:
        download_from_list(args.from_list, args.profile, args.visible)
    else:
        download_from_list(profile_name=args.profile, visible=args.visible)

if __name__ == "__main__":
    main()
