"""
---
title: Kimi Conversation File Downloader
name: kimi-agent-tracker
description: F-003 Auto-download files from Kimi chat conversations. v1.1.8 adds anchor-download injection, keyboard Enter/Space fallback, realistic mouse trajectory, and fetch-API direct content extraction as ultimate fallbacks.
version: "1.1.8"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T14:10:00+00:00"
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

    def _download_direct(self, page, link, conversation_title):
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

            # STRATEGY A: Anchor injection with download attribute (forces browser download)
            log_event(f"[STRAT-A] Anchor injection for {filename}")
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

            # STRATEGY B: Physical mouse click (single click, not down/up)
            log_event(f"[STRAT-B] Mouse click for {filename}")
            scrolled = self._scroll_element_into_view(page, href)
            if scrolled:
                page.wait_for_timeout(1000)
                pos = self._get_element_position(page, href)
                if pos and pos.get("in_viewport") and pos["y"] > 0:
                    x, y = pos["x"], pos["y"]
                    # Realistic mouse trajectory: move to nearby first, then to target
                    nearby_x = x + random.randint(-50, 50)
                    nearby_y = y + random.randint(-30, 30)
                    page.mouse.move(nearby_x, nearby_y)
                    page.wait_for_timeout(random.randint(200, 500))
                    page.mouse.move(x, y)
                    page.wait_for_timeout(random.randint(300, 700))
                    page.mouse.click(x, y)  # Single click with built-in down/up
                    log_event(f"[MOUSE] Clicked at ({x:.0f}, {y:.0f}) for {filename}")
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

            # STRATEGY C: Keyboard navigation (focus + Enter/Space)
            log_event(f"[STRAT-C] Keyboard navigation for {filename}")
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            js_focus = f"""() => {{
            var links = document.querySelectorAll('a[href]');
            for (var i = 0; i < links.length; i++) {{
                if (links[i].getAttribute('href') === "{href.replace(chr(34), chr(92)+chr(34))}") {{
                    links[i].focus();
                    links[i].tabIndex = 0;
                    return true;
                }}
            }}
            return false;
            }}"""
            focused = page.evaluate(js_focus)
            if focused:
                page.wait_for_timeout(500)
                page.keyboard.press("Enter")
                log_event(f"[KEYBOARD] Enter pressed for {filename}")
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

                # Try Space key as alternative
                page.keyboard.press("Space")
                log_event(f"[KEYBOARD] Space pressed for {filename}")
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

            # STRATEGY D: JS element.click() on original element
            log_event(f"[STRAT-D] JS element.click() for {filename}")
            js_click = f"""() => {{
            var links = document.querySelectorAll('a[href]');
            for (var i = 0; i < links.length; i++) {{
                if (links[i].getAttribute('href') === "{href.replace(chr(34), chr(92)+chr(34))}") {{
                    links[i].click();
                    return "clicked";
                }}
            }}
            return "not_found";
            }}"""
            result = page.evaluate(js_click)
            log_event(f"[JS-CLICK] Result: {result} for {filename}")
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

            # STRATEGY E: Fetch API direct content extraction
            log_event(f"[STRAT-E] Fetch API for {filename}")
            try:
                js_fetch = f"""async () => {{
                try {{
                    const resp = await fetch("{href.replace(chr(34), chr(92)+chr(34))}");
                    if (!resp.ok) return {{ok: false, status: resp.status}};
                    const blob = await resp.blob();
                    return {{ok: true, size: blob.size, type: blob.type}};
                }} catch (e) {{
                    return {{ok: false, error: e.message}};
                }}
                }}"""
                fetch_result = page.evaluate(js_fetch)
                log_event(f"[FETCH] Result: {fetch_result} for {filename}")
                if fetch_result and fetch_result.get("ok"):
                    # Fetch succeeded, try to download via blob URL
                    js_blob_download = f"""async () => {{
                    const resp = await fetch("{href.replace(chr(34), chr(92)+chr(34))}");
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = "{filename.replace(chr(34), chr(92)+chr(34))}";
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    return "blob_downloaded";
                    }}"""
                    page.evaluate(js_blob_download)
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
            except Exception as e:
                log_event(f"[FETCH] Error: {e} for {filename}")

            # All strategies exhausted
            log_event(f"[SKIP] All 5 strategies failed for {filename}")
            self._capture(page, f"skip_all_{filename[:30]}")
            return {"status": "skipped", "file": filename, "reason": "All download strategies failed"}
        except Exception as e:
            log_event(f"[ERROR] Direct download failed for {filename}: {e}")
            self._capture(page, f"error_{filename[:30]}")
            return {"status": "error", "file": filename, "error": str(e)}
        finally:
            page.remove_listener("download", on_download)

    def _download_md_preview(self, page, link, conversation_title):
        href = link["href"]
        filename_base = os.path.basename(urlparse(href).path).replace(".md", "") or "document"
        safe_title = "".join(c for c in conversation_title if c.isalnum() or c in "-_ ").replace(" ", "_")[:30]
        filename = f"{safe_title}_{filename_base}.md"
        dest_path = Path(self.download_dir) / filename

        try:
            self._dismiss_overlay(page)

            # Step 1: Scroll MD link into view and click via mouse to open preview
            scrolled = self._scroll_element_into_view(page, href)
            if not scrolled:
                log_event(f"[SKIP] MD link not found for {filename}")
                return {"status": "skipped", "file": filename, "reason": "MD link not found"}
            page.wait_for_timeout(500)
            pos = self._get_element_position(page, href)
            if pos and pos.get("in_viewport") and pos["y"] > 0:
                page.mouse.move(pos["x"], pos["y"])
                page.wait_for_timeout(300)
                page.mouse.click(pos["x"], pos["y"])
            else:
                js_click = "href => { var links = document.querySelectorAll('a[href]'); for (var i = 0; i < links.length; i++) { if (links[i].getAttribute('href') === href) { links[i].click(); return true; } } return false; }"
                page.evaluate(js_click, href)
            log_event(f"[MD-STEP1] Opened preview for {filename}")
            page.wait_for_timeout(3000)
            self._capture(page, f"md_step1_{filename_base}")

            # Step 2: Find download icon in preview panel
            icon_selectors = [
                '[class*="download"]', 'button[class*="download"]',
                'svg[class*="download"]', '[title*="download" i]',
                '[aria-label*="download" i]', 'i[class*="download"]',
                '.preview-download', '[data-testid*="download"]',
            ]
            clicked = False
            for sel in icon_selectors:
                try:
                    icon = page.wait_for_selector(sel, timeout=3000)
                    if icon and icon.is_visible():
                        bbox = icon.bounding_box()
                        if bbox:
                            page.mouse.move(bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2)
                            page.wait_for_timeout(300)
                            page.mouse.click(bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2)
                            clicked = True
                            break
                except Exception:
                    continue

            if not clicked:
                log_event(f"[SKIP] No download icon found in preview for {filename}")
                self._capture(page, f"md_no_icon_{filename_base}")
                return {"status": "skipped", "file": filename, "reason": "No download icon in preview panel"}

            log_event(f"[MD-STEP2] Clicked download icon for {filename}")
            page.wait_for_timeout(2000)
            self._capture(page, f"md_step2_{filename_base}")

            # Step 3: Select Markdown format
            md_selectors = [
                "text=Markdown", "text=Save as Markdown",
                '[class*="markdown"]', "button:has-text(\"Markdown\")",
                "div:has-text(\"Markdown\")", '[role="dialog"] button:has-text("Markdown")',
                '[class*="dialog"] [class*="markdown"]', '.modal button:has-text("Markdown")',
            ]
            for sel in md_selectors:
                try:
                    opt = page.wait_for_selector(sel, timeout=3000)
                    if opt and opt.is_visible():
                        bbox = opt.bounding_box()
                        if bbox:
                            page.mouse.move(bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2)
                            page.wait_for_timeout(300)
                            page.mouse.click(bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2)
                            break
                except Exception:
                    continue
            else:
                try:
                    page.keyboard.press("ArrowDown")
                    page.wait_for_timeout(300)
                    page.keyboard.press("Enter")
                    log_event(f"[MD-FALLBACK] Used keyboard navigation for {filename}")
                except Exception:
                    pass

            page.wait_for_timeout(3000)
            self._capture(page, f"md_step3_{filename_base}")

            browser_file = self._wait_for_browser_download(filename_hint=".md", max_wait_sec=10)
            if browser_file and browser_file.exists():
                shutil.copy2(str(browser_file), str(dest_path))
                file_hash = compute_sha256(dest_path)
                return self._record_download(dest_path, filename, conversation_title, file_hash)

            log_event(f"[SKIP] No .md file found in browser download dir for {filename}")
            return {"status": "skipped", "file": filename, "reason": "No .md file in browser download dir"}
        except Exception as e:
            log_event(f"[ERROR] MD preview download failed for {filename}: {e}")
            self._capture(page, f"md_error_{filename_base}")
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
                    is_sandbox = href.startswith("sandbox://")
                    is_md = ".md" in href.lower() or href.endswith(".md")
                    is_direct = is_sandbox or not is_md or "github.com" in href or "raw.githubusercontent" in href
                    if is_md and not is_direct:
                        res = self._download_md_preview(page, link, title)
                    else:
                        res = self._download_direct(page, link, title)
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
    parser = argparse.ArgumentParser(description="Kimi Conversation File Downloader v1.1.8")
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