"""
---
title: "Kimi Conversation File Downloader"
name: "kimi-agent-tracker"
description: "Auto-download files from Kimi chat conversations. Physical mouse simulation to bypass event interception. Outputs JSON summary for Download Manager consumption."
version: "v5.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-27T00:51:00.828+00:00"
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


import os
import sys
import json
import time
import hashlib
import shutil
import argparse
import json
import os
import sys
from pathlib import Path

# Inject skill scripts into path for core module imports
_SKILL_DIR = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _SKILL_DIR / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from core_path_utils import get_download_dir
from core_logger import CoreLogger, get_default_logger

from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    print("[WARN] nest_asyncio not installed. Run: python3 -m pip install nest_asyncio --user")

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import re

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"

def log_event(msg):
    print(f"[{_now_iso()}] {msg}")

def get_base_dir():
    return Path(__file__).resolve().parent.parent

def load_config():
    p = get_base_dir() / ".config" / "kimi_tracker_config.json"
    if not p.exists():
        log_event(f"[ERROR] Config not found: {p}")
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dir(path):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def expand_path(path_str):
    if path_str.startswith("~/"):
        return os.path.expanduser(path_str)
    return path_str

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def get_profile_dir():
    p = Path.home() / ".kimi_auth" / "browser_profile_chromium"
    ensure_dir(p)
    return str(p)

def load_downloads_json():
    p = get_base_dir() / ".config" / "downloads.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"downloaded": {}, "duplicates": []}

def save_downloads_json(data):
    p = get_base_dir() / ".config" / "downloads.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class KimiDownloader:
    def __init__(self, config):
        self.config = config
        self.profile_dir = get_profile_dir()
        self.downloads_record = load_downloads_json()
        self.dedup = config.get("download", {}).get("deduplicate", True)
        self.unique_name = config.get("download", {}).get("unique_filename", True)
        self.timeout = config.get("login", {}).get("timeout_sec", 30)
        self.download_dir = expand_path(config.get("daemon", {}).get("download_dir", "~/Downloads"))
        self.duplicate_dir = expand_path(config.get("daemon", {}).get("duplicate_dir", "~/skills_moved/.duplicate_downloads"))
        self.browser_default_dir = Path.home() / "Downloads"
        self.diag_dir = get_base_dir() / ".logs" / "diagnose" / "download"
        ensure_dir(self.download_dir)
        ensure_dir(self.duplicate_dir)
        ensure_dir(self.diag_dir)

    def _get_browser_context(self, p, visible=False):
        return p.chromium.launch_persistent_context(
            self.profile_dir, headless=not visible,
            args=["--disable-blink-features=AutomationControlled"],
            accept_downloads=True,
        )

    def _capture(self, page, step_name):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        png_path = self.diag_dir / f"{step_name}_{ts}.png"
        try:
            page.screenshot(path=str(png_path), full_page=True)
            log_event(f"[DIAG] Screenshot: {png_path.name}")
        except Exception as e:
            log_event(f"[DIAG] Screenshot failed: {e}")

    def _dismiss_overlay(self, page):
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception:
            pass
        try:
            mask = page.query_selector(".mask, [class*='mask'], .sidebar-mask")
            if mask and mask.is_visible():
                mask.click()
                page.wait_for_timeout(300)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # File card scanning (based on probe v1.0.8 proven pattern)
    # ------------------------------------------------------------------
    def _scan_file_cards(self, page):
        # Scan for file card containers and extract filenames via regex
        cards = []
        selectors = [
            'div[class*="file-card-container"]',
            'div[class*="file-card"]',
            'div[data-v-][class*="file"]',
            'div[class*="file-item"]',
            'div[class*="attachment"]',
        ]
        for sel in selectors:
            try:
                elements = page.query_selector_all(sel)
                if elements:
                    log_event(f"[SCAN] Selector '{sel}' matched {len(elements)} elements")
                    for idx, el in enumerate(elements):
                        try:
                            text = el.text_content() or ""
                            text = text.strip()
                            match = re.search(r'([A-Za-z0-9_.-]+[.](py|md|json|zip|env|txt|csv|yaml|yml|js|html|css|xml))', text, re.I)
                            if match:
                                filename = match.group(1)
                                ext = match.group(2).lower()
                                cards.append({
                                    "filename": filename,
                                    "ext": ext,
                                    "selector": f'{sel}:nth-of-type({idx + 1})',
                                    "index": idx,
                                    "card_text": text[:100],
                                })
                        except Exception as e:
                            log_event(f"[WARN] Error processing card {idx}: {e}")
                    break
            except Exception:
                continue
        log_event(f"[SCAN] Extracted {len(cards)} valid file cards")
        return cards

    # ------------------------------------------------------------------
    # Preview panel detection (bounding box - proven in probe v1.0.8)
    # ------------------------------------------------------------------
    def _wait_for_preview_panel(self, page, max_wait_sec=10):
        # Poll for large right-side element (preview panel)
        start = time.time()
        while time.time() - start < max_wait_sec:
            try:
                data = page.evaluate("""
                    () => {
                        let best = null, bestArea = 0;
                        document.querySelectorAll('*').forEach(el => {
                            const rect = el.getBoundingClientRect();
                            const area = rect.width * rect.height;
                            if (rect.left > window.innerWidth * 0.45 && area > bestArea 
                                && rect.width > 400 && rect.height > 300) {
                                best = el;
                                bestArea = area;
                            }
                        });
                        return best ? {
                            tag: best.tagName,
                            class: (best.className || '').substring(0, 100),
                            hasContent: (best.innerText || '').length > 50
                        } : null;
                    }
                """)
                if data and data.get("hasContent"):
                    log_event(f"[PREVIEW] Panel detected: {data.get('class', '')[:60]}")
                    return True
            except Exception:
                pass
            time.sleep(1)
        log_event("[PREVIEW] Panel not detected within timeout")
        return False

    # ------------------------------------------------------------------
    # Download icon click (top-right corner - screenshot confirmed)
    # ------------------------------------------------------------------
    def _click_download_icon(self, page):
        # Find download icon in top-right area of preview panel
        try:
            icons = page.evaluate("""
                () => {
                    const results = [];
                    document.querySelectorAll('button, svg, [class*="icon"], i').forEach(el => {
                        const rect = el.getBoundingClientRect();
                        const cls = (el.className || '').toLowerCase();
                        const title = (el.getAttribute('title') || '').toLowerCase();
                        if (rect.width < 60 && rect.height < 60 
                            && rect.left > window.innerWidth * 0.8 && rect.top < 150
                            && (cls.includes('download') || title.includes('download') 
                                || cls.includes('save') || title.includes('save'))) {
                            results.push({
                                x: rect.left + rect.width / 2,
                                y: rect.top + rect.height / 2,
                                class: cls.substring(0, 50)
                            });
                        }
                    });
                    return results;
                }
            """)
            if icons:
                icon = icons[0]
                page.mouse.move(icon["x"], icon["y"])
                page.wait_for_timeout(300)
                page.mouse.down()
                page.wait_for_timeout(150)
                page.mouse.up()
                log_event(f"[DOWNLOAD] Clicked download icon at ({icon['x']:.0f}, {icon['y']:.0f})")
                return True
            else:
                log_event("[DOWNLOAD] No download icon found in top-right area")
                return False
        except Exception as e:
            log_event(f"[DOWNLOAD] Error clicking download icon: {e}")
            return False

    # ------------------------------------------------------------------
    # MD format dialog handling
    # ------------------------------------------------------------------
    def _handle_md_format_dialog(self, page, max_wait_sec=5):
        # Check if format selection dialog appears
        start = time.time()
        while time.time() - start < max_wait_sec:
            try:
                opts = page.evaluate("""
                    () => {
                        const results = [];
                        document.querySelectorAll('*').forEach(el => {
                            const text = (el.innerText || '').toLowerCase();
                            if (text.includes('markdown') || text.includes('save as')) {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    results.push({
                                        x: rect.left + rect.width / 2,
                                        y: rect.top + rect.height / 2,
                                        text: text.substring(0, 30)
                                    });
                                }
                            }
                        });
                        return results;
                    }
                """)
                if opts:
                    opt = opts[0]
                    page.mouse.move(opt["x"], opt["y"])
                    page.wait_for_timeout(300)
                    page.mouse.down()
                    page.wait_for_timeout(150)
                    page.mouse.up()
                    log_event(f"[MD] Selected format: {opt['text']}")
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        log_event("[MD] No format dialog detected (direct download)")
        return False

    # ------------------------------------------------------------------
    # Unified download via preview panel (proven pattern)
    # ------------------------------------------------------------------
    def _download_file(self, page, card_info, conversation_title, timeout_sec=30):
        filename = card_info["filename"]
        ext = card_info["ext"]
        card_selector = card_info["selector"]

        log_event(f"[DOWNLOAD] Processing: {filename} (.{ext})")

        # Step 1: Click file card to open preview
        try:
            card = page.wait_for_selector(card_selector, timeout=5000)
            if not card:
                return {"status": "skipped", "file": filename, "reason": "Card not found"}

            # Get card position and click
            bbox = card.bounding_box()
            if bbox:
                page.mouse.move(bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2)
                page.wait_for_timeout(300)
                page.mouse.down()
                page.wait_for_timeout(150)
                page.mouse.up()
                log_event(f"[DOWNLOAD] Clicked card for {filename}")
            else:
                # Fallback: force click
                card.click(force=True)
                log_event(f"[DOWNLOAD] Force-clicked card for {filename}")
        except Exception as e:
            log_event(f"[SKIP] Failed to click card for {filename}: {e}")
            return {"status": "skipped", "file": filename, "reason": str(e)}

        # Step 2: Wait for preview panel
        if not self._wait_for_preview_panel(page, max_wait_sec=10):
            return {"status": "skipped", "file": filename, "reason": "Preview panel not opened"}

        # Step 3: Click download icon
        if not self._click_download_icon(page):
            self._capture(page, f"no_download_icon_{filename[:30]}")
            return {"status": "skipped", "file": filename, "reason": "Download icon not found"}

        # Step 4: For .md, handle format dialog
        if ext == "md":
            self._handle_md_format_dialog(page, max_wait_sec=5)

        # Step 5: Poll for download completion
        dest_path = Path(self.download_dir) / filename
        if self.unique_name:
            safe_title = "".join(c for c in conversation_title if c.isalnum() or c in "-_ ").replace(" ", "_")[:30]
            dest_path = Path(self.download_dir) / f"{safe_title}_{filename}"

        browser_file = self._poll_for_download(filename_hint=filename, max_wait_sec=timeout_sec)
        if browser_file and browser_file.exists():
            shutil.copy2(str(browser_file), str(dest_path))
            file_hash = compute_sha256(dest_path)
            return self._record_download(dest_path, filename, conversation_title, file_hash)

        log_event(f"[SKIP] Download not captured for {filename}")
        return {"status": "skipped", "file": filename, "reason": "Download timeout"}

    # ------------------------------------------------------------------
    # Poll for browser download
    # ------------------------------------------------------------------
    def _poll_for_download(self, filename_hint, max_wait_sec=30, check_interval_sec=1):
        start = time.time()
        while time.time() - start < max_wait_sec:
            browser_file = self._wait_for_browser_download(filename_hint, max_wait_sec=check_interval_sec)
            if browser_file and browser_file.exists():
                return browser_file
            time.sleep(check_interval_sec)
        return None

    def _wait_for_browser_download(self, filename_hint, max_wait_sec=15):
        if not self.browser_default_dir.exists():
            return None
        start_time = time.time()
        while time.time() - start_time < max_wait_sec:
            candidates = []
            for p in self.browser_default_dir.iterdir():
                if p.is_file():
                    mtime = p.stat().st_mtime
                    if mtime > start_time - 60:
                        candidates.append((p, mtime))
            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)
                if filename_hint:
                    for c, m in candidates:
                        if filename_hint.lower() in c.name.lower():
                            return c
                return candidates[0][0]
            time.sleep(0.5)
        return None

    def _record_download(self, dest_path, filename, conversation_title, file_hash):
        if self.dedup and file_hash in self.downloads_record.get("downloaded", {}):
            dup_path = Path(self.duplicate_dir) / filename
            shutil.move(str(dest_path), str(dup_path))
            self.downloads_record["duplicates"].append({
                "file": filename, "hash": file_hash, "conversation": conversation_title,
                "time": datetime.now(timezone.utc).isoformat(),
            })
            log_event(f"[DEDUP] Duplicate moved to {dup_path}")
            return {"status": "duplicate", "file": filename, "hash": file_hash}
        else:
            self.downloads_record["downloaded"][file_hash] = {
                "file": filename, "conversation": conversation_title,
                "time": datetime.now(timezone.utc).isoformat(),
            }
            log_event(f"[SAVED] {dest_path}")
            return {"status": "success", "file": filename, "hash": file_hash, "path": str(dest_path)}

    # ------------------------------------------------------------------
    # Main entry: download from conversation URL
    # ------------------------------------------------------------------
    def download_conversation(self, url, title="unknown", visible=False, timeout_sec=20, max_files=None):
        log_event(f"[DOWNLOAD] Navigating to: {url}")
        results = {"success": [], "duplicates": [], "errors": [], "skipped": []}
        with sync_playwright() as p:
            browser = self._get_browser_context(p, visible=visible)
            page = browser.new_page()
            try:
                page.goto(url, timeout=self.timeout * 1000)
                page.wait_for_load_state("domcontentloaded", timeout=self.timeout * 1000)
                page.wait_for_timeout(5000)  # Wait for Vue/React hydration

                # Extract title from page if unknown
                if title == "unknown":
                    try:
                        title_el = page.query_selector(".chat-name, .conversation-title, h1, title")
                        if title_el:
                            title = (title_el.inner_text() or title).strip()[:50]
                    except Exception:
                        pass

                # Scan file cards
                cards = self._scan_file_cards(page)
                log_event(f"[DOWNLOAD] Found {len(cards)} file cards in '{title}'")

                # Apply max_files limit
                file_counter = 0
                max_limit = max_files if max_files else len(cards)

                for card in cards:
                    if file_counter >= max_limit:
                        log_event(f"[DOWNLOAD] Max files limit ({max_limit}) reached, stopping.")
                        break
                    file_counter += 1

                    res = self._download_file(page, card, title, timeout_sec=timeout_sec)
                    if res.get("status") == "success":
                        results["success"].append(res)
                    elif res.get("status") == "duplicate":
                        results["duplicates"].append(res)
                    elif res.get("status") == "skipped":
                        results["skipped"].append(res)
                    else:
                        results["errors"].append({"file": res.get("file", "unknown"), "error": res.get("reason", "unknown")})

                    # Dismiss any overlay before next card
                    self._dismiss_overlay(page)
                    page.wait_for_timeout(800)

            except PlaywrightTimeout:
                log_event(f"[TIMEOUT] Navigation timeout for {url}")
                results["errors"].append({"conversation": title, "error": "Navigation timeout"})
            except Exception as e:
                log_event(f"[ERROR] Unexpected error: {e}")
                results["errors"].append({"conversation": title, "error": str(e)})
            finally:
                browser.close()
        save_downloads_json(self.downloads_record)
        log_event(f"[RESULT] {title}: {len(results['success'])} success, {len(results['duplicates'])} duplicates, {len(results['errors'])} errors, {len(results['skipped'])} skipped")
        return results

    def download_from_list(self, conversations_path, visible=False, timeout_sec=20, max_files=None):
        with open(conversations_path, "r", encoding="utf-8") as f:
            conversations = json.load(f)
        all_results = {"success": [], "duplicates": [], "errors": [], "skipped": []}
        for conv in conversations:
            url = conv.get("url", "")
            title = conv.get("title", "unknown")
            if not url:
                continue
            res = self.download_conversation(url, title=title, visible=visible, timeout_sec=timeout_sec, max_files=max_files)
            all_results["success"].extend(res["success"])
            all_results["duplicates"].extend(res["duplicates"])
            all_results["errors"].extend(res["errors"])
            all_results["skipped"].extend(res["skipped"])
            time.sleep(2)
        log_event(f"[BATCH] Complete: {len(all_results['success'])} success, {len(all_results['duplicates'])} duplicates, {len(all_results['errors'])} errors, {len(all_results['skipped'])} skipped")
        return all_results
def main():
    parser = argparse.ArgumentParser(description="Kimi Conversation File Downloader v5.0.0")
    parser.add_argument("--url", help="Single conversation URL to download from")
    parser.add_argument("--from-list", help="Path to conversations.json for batch download")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode")
    parser.add_argument("--timeout", type=int, default=20, help="Download timeout in seconds per file")
    parser.add_argument("--max-files", type=int, default=None, help="Maximum files to download from this conversation")
    args = parser.parse_args()
    config = load_config()
    downloader = KimiDownloader(config)
    if args.url:
        results = downloader.download_conversation(args.url, visible=args.visible, timeout_sec=args.timeout, max_files=args.max_files)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.from_list:
        results = downloader.download_from_list(args.from_list, visible=args.visible, timeout_sec=args.timeout, max_files=args.max_files)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()