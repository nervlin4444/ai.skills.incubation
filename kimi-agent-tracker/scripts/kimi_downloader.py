"""
---
title: Kimi Conversation File Downloader
name: kimi-agent-tracker
description: F-003 Auto-download files from Kimi chat conversations using Playwright. Handles .zip/.py/.csv direct downloads and .md preview-panel three-step download flow. Supports batch mode from conversations.json.
version: "1.1.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T11:57:00+00:00"
auth_config:
  provider: kimi
  auth_method: persistent_profile
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/scripts/kimi_downloader.py"
  github_path: "kimi-agent-tracker/scripts/kimi_downloader.py"
---
"""

import os
import sys
import json
import time
import hashlib
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# FIX: Playwright Sync API inside asyncio loop crash
# Apply nest_asyncio before any Playwright import
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    print("[WARN] nest_asyncio not installed. Run: python3 -m pip install nest_asyncio --user")
    print("[WARN] Downloader may crash with 'asyncio loop' error.")

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def get_base_dir():
    script_path = Path(__file__).resolve()
    return script_path.parent.parent


def load_config():
    base_dir = get_base_dir()
    config_path = base_dir / ".config" / "kimi_tracker_config.json"
    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    return Path(path)


def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_profile_dir():
    home = Path.home()
    profile = home / ".kimi_auth" / "browser_profile_chromium"
    ensure_dir(profile)
    return str(profile)


def get_log_dir():
    base_dir = get_base_dir()
    log_dir = base_dir / ".logs" / "download"
    ensure_dir(log_dir)
    return str(log_dir)


def expand_path(path_str):
    if path_str.startswith("~/"):
        return os.path.expanduser(path_str)
    return path_str


def load_downloads_json():
    base_dir = get_base_dir()
    downloads_path = base_dir / ".config" / "downloads.json"
    if downloads_path.exists():
        with open(downloads_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"downloaded": {}, "duplicates": []}


def save_downloads_json(data):
    base_dir = get_base_dir()
    downloads_path = base_dir / ".config" / "downloads.json"
    with open(downloads_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_event(msg):
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"
    print(f"[{ts}] {msg}")


class KimiDownloader:
    def __init__(self, config):
        self.config = config
        self.profile_dir = get_profile_dir()
        self.log_dir = get_log_dir()
        self.downloads_record = load_downloads_json()
        self.dedup = config.get("download", {}).get("deduplicate", True)
        self.unique_name = config.get("download", {}).get("unique_filename", True)
        self.timeout = config.get("login", {}).get("timeout_sec", 30)
        self.download_dir = expand_path(config.get("daemon", {}).get("download_dir", "~/Downloads"))
        self.duplicate_dir = expand_path(config.get("daemon", {}).get("duplicate_dir", "~/skills_moved/.duplicate_downloads"))
        ensure_dir(self.download_dir)
        ensure_dir(self.duplicate_dir)

    def _get_browser_context(self, p, visible=False):
        browser = p.chromium.launch_persistent_context(
            self.profile_dir,
            headless=not visible,
            args=["--disable-blink-features=AutomationControlled"],
            accept_downloads=True,
        )
        return browser

    def _find_file_links(self, page):
        links = []
        # Pattern 1: Direct download links (sandbox://)
        selectors = [
            'a[href*="sandbox://"]',
            'a[href*=".zip"]',
            'a[href*=".py"]',
            'a[href*=".csv"]',
            'a[href*=".json"]',
            'a[href*=".md"]',
            'a[href*=".txt"]',
        ]
        for sel in selectors:
            try:
                elements = page.query_selector_all(sel)
                for el in elements:
                    href = el.get_attribute("href")
                    text = el.inner_text().strip() if el.inner_text() else ""
                    if href:
                        links.append({"href": href, "text": text, "type": "direct"})
            except Exception:
                pass
        # Pattern 2: Preview panel download icons (for .md files)
        try:
            preview_icons = page.query_selector_all('[class*="download"]')
            for icon in preview_icons:
                parent = icon.query_selector("xpath=..")
                if parent:
                    href = parent.get_attribute("href") or ""
                    links.append({"href": href, "text": "preview_download", "type": "preview"})
        except Exception:
            pass
        # Deduplicate by href
        seen = set()
        unique = []
        for link in links:
            if link["href"] and link["href"] not in seen:
                seen.add(link["href"])
                unique.append(link)
        return unique

    def _trigger_direct_download(self, page, link, conversation_title):
        href = link["href"]
        filename = os.path.basename(urlparse(href).path) or "unknown"
        if not filename or filename == "unknown":
            filename = f"download_{int(time.time())}"
        # Add conversation prefix for uniqueness
        if self.unique_name:
            safe_title = "".join(c for c in conversation_title if c.isalnum() or c in "-_ ").replace(" ", "_")[:30]
            filename = f"{safe_title}_{filename}"
        dest_path = Path(self.download_dir) / filename
        try:
            with page.expect_download(timeout=self.timeout * 1000) as download_info:
                page.click(f'a[href="{href}"]')
            download = download_info.value
            download_path = Path(download.path())
            # Move from temp to target
            if download_path.exists():
                shutil.move(str(download_path), str(dest_path))
                file_hash = compute_sha256(dest_path)
                if self.dedup and file_hash in self.downloads_record.get("downloaded", {}):
                    dup_path = Path(self.duplicate_dir) / filename
                    shutil.move(str(dest_path), str(dup_path))
                    self.downloads_record["duplicates"].append({
                        "file": filename,
                        "hash": file_hash,
                        "conversation": conversation_title,
                        "time": datetime.utcnow().isoformat(),
                    })
                    log_event(f"[DEDUP] Duplicate moved to {dup_path}")
                    return {"status": "duplicate", "file": filename, "hash": file_hash}
                else:
                    self.downloads_record["downloaded"][file_hash] = {
                        "file": filename,
                        "conversation": conversation_title,
                        "time": datetime.utcnow().isoformat(),
                    }
                    log_event(f"[DOWNLOAD] Saved: {dest_path}")
                    return {"status": "success", "file": filename, "hash": file_hash, "path": str(dest_path)}
        except PlaywrightTimeout:
            log_event(f"[TIMEOUT] Direct download timeout for {href}")
            return {"status": "error", "file": filename, "error": "Direct download timeout"}
        except Exception as e:
            log_event(f"[ERROR] Direct download failed: {e}")
            return {"status": "error", "file": filename, "error": str(e)}

    def _handle_md_preview(self, page, link, conversation_title):
        # Three-step flow for .md files: click link -> preview panel -> click download icon -> select format -> download
        href = link["href"]
        filename_base = os.path.basename(urlparse(href).path).replace(".md", "") or "document"
        safe_title = "".join(c for c in conversation_title if c.isalnum() or c in "-_ ").replace(" ", "_")[:30]
        filename = f"{safe_title}_{filename_base}.md"
        dest_path = Path(self.download_dir) / filename
        try:
            # Step 1: Click the .md link to open preview panel
            page.click(f'a[href="{href}"]')
            page.wait_for_timeout(2000)
            # Step 2: Click download icon in preview panel
            download_icon_selectors = [
                '[class*="download"]',
                'button[class*="download"]',
                'svg[class*="download"]',
                '[title*="download" i]',
                '[aria-label*="download" i]',
            ]
            clicked = False
            for sel in download_icon_selectors:
                try:
                    icon = page.wait_for_selector(sel, timeout=5000)
                    if icon:
                        icon.click()
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                log_event(f"[SKIP] No download icon found for markdown preview: {href}")
                return {"status": "skipped", "file": filename, "reason": "No download icon in preview"}
            # Step 3: Select Markdown format if dialog appears
            page.wait_for_timeout(1500)
            md_option_selectors = [
                'text=Markdown',
                'text=Save as Markdown',
                '[class*="markdown"]',
            ]
            for sel in md_option_selectors:
                try:
                    opt = page.wait_for_selector(sel, timeout=3000)
                    if opt:
                        opt.click()
                        break
                except Exception:
                    continue
            # Wait for download
            page.wait_for_timeout(3000)
            # Check browser default download dir for new files
            browser_default = Path.home() / "Downloads"
            candidates = sorted(browser_default.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                latest = candidates[0]
                shutil.move(str(latest), str(dest_path))
                file_hash = compute_sha256(dest_path)
                if self.dedup and file_hash in self.downloads_record.get("downloaded", {}):
                    dup_path = Path(self.duplicate_dir) / filename
                    shutil.move(str(dest_path), str(dup_path))
                    self.downloads_record["duplicates"].append({
                        "file": filename,
                        "hash": file_hash,
                        "conversation": conversation_title,
                        "time": datetime.utcnow().isoformat(),
                    })
                    log_event(f"[DEDUP] Duplicate MD moved to {dup_path}")
                    return {"status": "duplicate", "file": filename, "hash": file_hash}
                else:
                    self.downloads_record["downloaded"][file_hash] = {
                        "file": filename,
                        "conversation": conversation_title,
                        "time": datetime.utcnow().isoformat(),
                    }
                    log_event(f"[DOWNLOAD] MD saved: {dest_path}")
                    return {"status": "success", "file": filename, "hash": file_hash, "path": str(dest_path)}
            else:
                log_event(f"[SKIP] No .md file found in browser download dir after preview download: {href}")
                return {"status": "skipped", "file": filename, "reason": "No file in download dir"}
        except Exception as e:
            log_event(f"[ERROR] MD preview download failed: {e}")
            return {"status": "error", "file": filename, "error": str(e)}

    def download_conversation(self, url, title="unknown", visible=False):
        log_event(f"[DOWNLOAD] Navigating to: {url}")
        results = {"success": [], "duplicates": [], "errors": [], "skipped": []}
        with sync_playwright() as p:
            browser = self._get_browser_context(p, visible=visible)
            page = browser.new_page()
            try:
                page.goto(url, timeout=self.timeout * 1000)
                page.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
                page.wait_for_timeout(3000)  # Allow dynamic content to settle
                links = self._find_file_links(page)
                log_event(f"[DOWNLOAD] Found {len(links)} file links")
                for link in links:
                    href = link["href"]
                    if ".md" in href.lower() or link.get("type") == "preview":
                        res = self._handle_md_preview(page, link, title)
                    else:
                        res = self._trigger_direct_download(page, link, title)
                    if res["status"] == "success":
                        results["success"].append(res)
                    elif res["status"] == "duplicate":
                        results["duplicates"].append(res)
                    elif res["status"] == "skipped":
                        results["skipped"].append(res)
                    else:
                        results["errors"].append({"file": res.get("file", "unknown"), "error": res.get("error", "unknown")})
                    page.wait_for_timeout(1000)
            except PlaywrightTimeout:
                log_event(f"[TIMEOUT] Navigation or load timeout for {url}")
                results["errors"].append({"conversation": title, "error": "Navigation timeout"})
            except Exception as e:
                log_event(f"[ERROR] Unexpected error: {e}")
                results["errors"].append({"conversation": title, "error": str(e)})
            finally:
                browser.close()
        save_downloads_json(self.downloads_record)
        return results

    def download_from_list(self, conversations_path, visible=False):
        with open(conversations_path, "r", encoding="utf-8") as f:
            conversations = json.load(f)
        all_results = {"success": [], "duplicates": [], "errors": [], "skipped": []}
        for conv in conversations:
            url = conv.get("url", "")
            title = conv.get("title", "unknown")
            if not url:
                continue
            log_event(f"[BATCH] Processing: {title}")
            res = self.download_conversation(url, title=title, visible=visible)
            all_results["success"].extend(res["success"])
            all_results["duplicates"].extend(res["duplicates"])
            all_results["errors"].extend(res["errors"])
            all_results["skipped"].extend(res["skipped"])
            time.sleep(2)
        log_event(f"[BATCH] Complete: {len(all_results['success'])} success, {len(all_results['duplicates'])} duplicates, {len(all_results['errors'])} errors, {len(all_results['skipped'])} skipped")
        return all_results


def main():
    parser = argparse.ArgumentParser(description="Kimi Conversation File Downloader v1.1.1")
    parser.add_argument("--url", help="Single conversation URL to download from")
    parser.add_argument("--from-list", help="Path to conversations.json for batch download")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode")
    args = parser.parse_args()

    config = load_config()
    downloader = KimiDownloader(config)

    if args.url:
        results = downloader.download_conversation(args.url, visible=args.visible)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.from_list:
        results = downloader.download_from_list(args.from_list, visible=args.visible)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
