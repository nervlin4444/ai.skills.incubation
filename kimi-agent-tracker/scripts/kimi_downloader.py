"""
---
title: Kimi Conversation File Downloader
name: kimi-agent-tracker
description: F-003 Auto-download files from Kimi chat conversations. v1.2.0 replaces download triggering with preview panel content extraction as primary strategy. Clicks file link, waits for preview panel to load, extracts text content from DOM, and writes directly to local file. Fallback to browser download for binary files.
version: "1.2.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T14:30:00+00:00"
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
import random
import argparse
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    print("[WARN] nest_asyncio not installed. Run: python3 -m pip install nest_asyncio --user")

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

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
        try:
            main = page.query_selector("main, .main-content, .chat-container, #app")
            if main:
                main.click()
                page.wait_for_timeout(200)
        except Exception:
            pass

    def _scroll_element_into_view(self, page, href):
        js_scroll = "href => { var links = document.querySelectorAll('a[href]'); for (var i = 0; i < links.length; i++) { if (links[i].getAttribute('href') === href) { links[i].scrollIntoView({block: \"center\", inline: \"center\", behavior: \"instant\"}); return true; } } return false; }"
        return page.evaluate(js_scroll, href)

    def _get_element_position(self, page, href):
        js_pos = "href => { var links = document.querySelectorAll('a[href]'); for (var i = 0; i < links.length; i++) { if (links[i].getAttribute('href') === href) { var rect = links[i].getBoundingClientRect(); return {x: rect.left + rect.width/2, y: rect.top + rect.height/2, w: rect.width, h: rect.height, in_viewport: rect.top >= 0 && rect.bottom <= window.innerHeight}; } } return null; }"
        return page.evaluate(js_pos, href)

    def _find_file_links(self, page):
        links = []
        selectors = [
            'a[href*="sandbox://"]', 'a[href*=".zip"]', 'a[href*=".py"]',
            'a[href*=".csv"]', 'a[href*=".json"]', 'a[href*=".md"]',
            'a[href*=".txt"]', 'a[href*=".html"]', 'a[href*=".yml"]',
            'a[href*=".yaml"]',
        ]
        for sel in selectors:
            try:
                for el in page.query_selector_all(sel):
                    href = el.get_attribute("href") or ""
                    text = (el.inner_text() or "").strip()
                    if href and href not in [l["href"] for l in links]:
                        links.append({"href": href, "text": text, "type": "direct"})
            except Exception:
                pass
        return links

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

    def _download_by_extraction(self, page, link, conversation_title):
        """Primary strategy: click link, wait for preview panel, extract content from DOM."""
        href = link["href"]
        filename = os.path.basename(urlparse(href).path) or "unknown"
        if not filename or filename == "unknown":
            filename = f"download_{int(time.time())}"
        if self.unique_name:
            safe_title = "".join(c for c in conversation_title if c.isalnum() or c in "-_ ").replace(" ", "_")[:30]
            filename = f"{safe_title}_{filename}"
        dest_path = Path(self.download_dir) / filename

        try:
            self._dismiss_overlay(page)

            # Step 1: Click the file link to open preview panel
            log_event(f"[EXTRACT-1] Clicking link for {filename}")
            scrolled = self._scroll_element_into_view(page, href)
            if scrolled:
                page.wait_for_timeout(800)
                pos = self._get_element_position(page, href)
                if pos and pos.get("in_viewport") and pos["y"] > 0:
                    page.mouse.move(pos["x"], pos["y"])
                    page.wait_for_timeout(300)
                    page.mouse.click(pos["x"], pos["y"])
                else:
                    js_click = "href => { var links = document.querySelectorAll('a[href]'); for (var i = 0; i < links.length; i++) { if (links[i].getAttribute('href') === href) { links[i].click(); return true; } } return false; }"
                    page.evaluate(js_click, href)
            else:
                js_click = "href => { var links = document.querySelectorAll('a[href]'); for (var i = 0; i < links.length; i++) { if (links[i].getAttribute('href') === href) { links[i].click(); return true; } } return false; }"
                page.evaluate(js_click, href)

            # Step 2: Wait for preview panel to appear
            log_event(f"[EXTRACT-2] Waiting for preview panel...")
            preview_selectors = [
                '[class*="preview"]', '[class*="panel"]', '[class*="drawer"]',
                '[class*="sidebar"]', '[class*="file-view"]', '[class*="code"]',
                '.monaco-editor', '[role="dialog"]', '.ant-drawer',
                '[class*="content"]',
            ]
            preview_found = False
            for sel in preview_selectors:
                try:
                    el = page.wait_for_selector(sel, timeout=5000)
                    if el and el.is_visible():
                        preview_found = True
                        log_event(f"[EXTRACT-2] Preview panel found: {sel}")
                        break
                except Exception:
                    continue

            if not preview_found:
                log_event(f"[EXTRACT-FAIL] Preview panel not found for {filename}")
                self._capture(page, f"extract_no_preview_{filename[:30]}")
                return {"status": "skipped", "file": filename, "reason": "Preview panel not found"}

            # Step 3: Wait for content to load (check multiple times)
            log_event(f"[EXTRACT-3] Waiting for content to load...")
            content = None
            for attempt in range(5):
                page.wait_for_timeout(2000)
                content = self._extract_preview_content(page)
                if content and len(content.strip()) > 50:
                    log_event(f"[EXTRACT-3] Content loaded: {len(content)} chars")
                    break
                log_event(f"[EXTRACT-3] Content not ready, attempt {attempt+1}/5")

            if not content or len(content.strip()) < 10:
                log_event(f"[EXTRACT-FAIL] Content empty or too short for {filename}")
                self._capture(page, f"extract_empty_{filename[:30]}")
                return {"status": "skipped", "file": filename, "reason": "Preview content empty"}

            # Step 4: Write content to file
            log_event(f"[EXTRACT-4] Writing {len(content)} chars to {dest_path}")
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(content)
            file_hash = compute_sha256(dest_path)
            return self._record_download(dest_path, filename, conversation_title, file_hash)

        except Exception as e:
            log_event(f"[EXTRACT-ERROR] {filename}: {e}")
            self._capture(page, f"extract_error_{filename[:30]}")
            return {"status": "error", "file": filename, "error": str(e)}

    def _extract_preview_content(self, page):
        """Extract text content from preview panel DOM."""
        js_extract = """() => {
            var selectors = [
                '[class*="preview"] pre', '[class*="panel"] pre',
                '[class*="code"] pre', '.monaco-editor .view-lines',
                '[class*="file-view"] pre', '[class*="content"] pre',
                '.ant-drawer pre', '[role="dialog"] pre',
                'pre[class*="code"]', 'code[class*="language"]',
                '[class*="markdown-body"]', '[class*="article"]',
                '.preview-panel pre', '.file-preview pre',
                '[class*="text"] pre', 'pre',
            ];
            for (var i = 0; i < selectors.length; i++) {
                var el = document.querySelector(selectors[i]);
                if (el && el.innerText && el.innerText.trim().length > 10) {
                    return el.innerText;
                }
            }
            // Fallback: get all text from preview-like containers
            var containers = document.querySelectorAll('[class*="preview"], [class*="panel"], [class*="drawer"], [class*="file-view"]');
            for (var j = 0; j < containers.length; j++) {
                var text = containers[j].innerText;
                if (text && text.trim().length > 50) {
                    return text;
                }
            }
            return null;
        }"""
        try:
            return page.evaluate(js_extract)
        except Exception as e:
            log_event(f"[EXTRACT-ERROR] JS extraction failed: {e}")
            return None

    def _download_by_browser(self, page, link, conversation_title):
        """Fallback strategy: trigger browser download for binary files (zip, etc)."""
        href = link["href"]
        filename = os.path.basename(urlparse(href).path) or "unknown"
        if not filename or filename == "unknown":
            filename = f"download_{int(time.time())}"
        if self.unique_name:
            safe_title = "".join(c for c in conversation_title if c.isalnum() or c in "-_ ").replace(" ", "_")[:30]
            filename = f"{safe_title}_{filename}"
        dest_path = Path(self.download_dir) / filename

        downloads_collected = []
        def on_download(download):
            downloads_collected.append(download)
        page.on("download", on_download)

        try:
            self._dismiss_overlay(page)

            # Strategy A: Anchor injection with download attribute
            log_event(f"[BROWSER-A] Anchor injection for {filename}")
            js_inject = f"""() => {{
            var a = document.createElement("a");
            a.href = "{href.replace(chr(34), chr(92)+chr(34))}";
            a.download = "{filename.replace(chr(34), chr(92)+chr(34))}";
            a.style.display = "none";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            return "injected";
            }}"""
            page.evaluate(js_inject)
            page.wait_for_timeout(8000)

            if downloads_collected:
                download = downloads_collected[-1]
                tmp_path = Path(download.path())
                if tmp_path.exists():
                    shutil.move(str(tmp_path), str(dest_path))
                    file_hash = compute_sha256(dest_path)
                    return self._record_download(dest_path, filename, conversation_title, file_hash)

            browser_file = self._wait_for_browser_download(filename_hint=filename, max_wait_sec=12)
            if browser_file and browser_file.exists():
                shutil.copy2(str(browser_file), str(dest_path))
                file_hash = compute_sha256(dest_path)
                return self._record_download(dest_path, filename, conversation_title, file_hash)

            # Strategy B: Mouse click on original element
            log_event(f"[BROWSER-B] Mouse click for {filename}")
            scrolled = self._scroll_element_into_view(page, href)
            if scrolled:
                page.wait_for_timeout(1000)
                pos = self._get_element_position(page, href)
                if pos and pos.get("in_viewport") and pos["y"] > 0:
                    page.mouse.move(pos["x"], pos["y"])
                    page.wait_for_timeout(300)
                    page.mouse.click(pos["x"], pos["y"])
                    log_event(f"[MOUSE] Clicked at ({pos['x']:.0f}, {pos['y']:.0f}) for {filename}")
                    page.wait_for_timeout(8000)

                    if downloads_collected:
                        download = downloads_collected[-1]
                        tmp_path = Path(download.path())
                        if tmp_path.exists():
                            shutil.move(str(tmp_path), str(dest_path))
                            file_hash = compute_sha256(dest_path)
                            return self._record_download(dest_path, filename, conversation_title, file_hash)

                    browser_file = self._wait_for_browser_download(filename_hint=filename, max_wait_sec=12)
                    if browser_file and browser_file.exists():
                        shutil.copy2(str(browser_file), str(dest_path))
                        file_hash = compute_sha256(dest_path)
                        return self._record_download(dest_path, filename, conversation_title, file_hash)

            log_event(f"[SKIP] Browser download failed for {filename}")
            return {"status": "skipped", "file": filename, "reason": "Browser download failed"}
        except Exception as e:
            log_event(f"[ERROR] Browser download failed for {filename}: {e}")
            return {"status": "error", "file": filename, "error": str(e)}
        finally:
            page.remove_listener("download", on_download)

    def download_conversation(self, url, title="unknown", visible=False):
        log_event(f"[DOWNLOAD] Navigating to: {url}")
        results = {"success": [], "duplicates": [], "errors": [], "skipped": []}
        with sync_playwright() as p:
            browser = self._get_browser_context(p, visible=visible)
            page = browser.new_page()
            try:
                page.goto(url, timeout=self.timeout * 1000)
                page.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
                page.wait_for_timeout(3000)

                if title == "unknown":
                    try:
                        title_el = page.query_selector(".chat-name, .conversation-title, h1, title")
                        if title_el:
                            title = (title_el.inner_text() or title).strip()[:50]
                    except Exception:
                        pass

                links = self._find_file_links(page)
                log_event(f"[DOWNLOAD] Found {len(links)} file links in '{title}'")
                for link in links:
                    href = link["href"]
                    filename = os.path.basename(urlparse(href).path) or ""
                    ext = Path(filename).suffix.lower()
                    # Text files: use content extraction (primary)
                    # Binary files: use browser download (fallback)
                    is_text = ext in [".py", ".md", ".txt", ".json", ".csv", ".yml", ".yaml", ".html", ".js", ".css", ".xml"]
                    is_binary = ext in [".zip", ".rar", ".7z", ".tar", ".gz", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".mp3", ".mp4"]
                    if is_text or not is_binary:
                        res = self._download_by_extraction(page, link, title)
                        # If extraction fails, try browser download as fallback
                        if res.get("status") in ["skipped", "error"]:
                            log_event(f"[FALLBACK] Extraction failed, trying browser download for {filename}")
                            res = self._download_by_browser(page, link, title)
                    else:
                        res = self._download_by_browser(page, link, title)
                    if res is None:
                        results["errors"].append({"file": "unknown", "error": "Download returned None"})
                    elif res.get("status") == "success":
                        results["success"].append(res)
                    elif res.get("status") == "duplicate":
                        results["duplicates"].append(res)
                    elif res.get("status") == "skipped":
                        results["skipped"].append(res)
                    else:
                        results["errors"].append({"file": res.get("file", "unknown"), "error": res.get("error", "unknown")})
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

    def download_from_list(self, conversations_path, visible=False):
        with open(conversations_path, "r", encoding="utf-8") as f:
            conversations = json.load(f)
        all_results = {"success": [], "duplicates": [], "errors": [], "skipped": []}
        for conv in conversations:
            url = conv.get("url", "")
            title = conv.get("title", "unknown")
            if not url:
                continue
            res = self.download_conversation(url, title=title, visible=visible)
            all_results["success"].extend(res["success"])
            all_results["duplicates"].extend(res["duplicates"])
            all_results["errors"].extend(res["errors"])
            all_results["skipped"].extend(res["skipped"])
            time.sleep(2)
        log_event(f"[BATCH] Complete: {len(all_results['success'])} success, {len(all_results['duplicates'])} duplicates, {len(all_results['errors'])} errors, {len(all_results['skipped'])} skipped")
        return all_results

def main():
    parser = argparse.ArgumentParser(description="Kimi Conversation File Downloader v1.2.0")
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