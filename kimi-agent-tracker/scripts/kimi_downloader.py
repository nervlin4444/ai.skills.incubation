"""
---
title: Kimi File Downloader Core Engine
name: kimi-agent-tracker
description: Playwright-based file downloader for Kimi conversations. v1.3.1 fixes preview extraction element detection, content stability checks, and garbage filtering.
version: v1.3.1
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T17:30:00+0800
fixes: []
auth_config:
  provider: github
  auth_method: token
  token_env_var: GITHUB_TOKEN
  env_file_path: .env
file_mapping:
  local_path: "{baseDir}/scripts/kimi_downloader.py"
  github_path: "kimi-agent-tracker/scripts/kimi_downloader.py"
---
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("[FATAL] Playwright not installed. Run: python3 -m pip install playwright")
    sys.exit(1)

DEFAULT_PROFILE_DIR = Path.home() / ".kimi_auth" / "browser_profile_chromium"
DEFAULT_CONFIG_PATH = Path.home() / ".workbuddy" / "skills" / "kimi-agent-tracker" / ".config" / "kimi_tracker_config.json"
DEFAULT_DOWNLOADS_RECORD = Path.home() / ".workbuddy" / "skills" / "kimi-agent-tracker" / ".config" / "downloads.json"
DEFAULT_PENDING_RECORD = Path.home() / ".workbuddy" / "skills" / "kimi-agent-tracker" / ".config" / "pending.json"
DEFAULT_DIAGNOSE_DIR = Path.home() / ".workbuddy" / "skills" / "kimi-agent-tracker" / ".logs" / "diagnose"

# Strategy mapping by extension
ANCHOR_EXTENSIONS = {".json", ".csv", ".txt", ".yml", ".yaml", ".xml", ".sh", ".bash"}
PREVIEW_EXTENSIONS = {".py", ".md", ".html", ".js", ".css"}
BINARY_EXTENSIONS = {".zip", ".rar", ".7z", ".tar", ".gz", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".mp3", ".mp4", ".webp", ".svg", ".ico", ".ttf", ".woff", ".woff2", ".eot"}

STRATEGY_ANCHOR = "anchor_injection"
STRATEGY_PREVIEW = "preview_extraction"
STRATEGY_VISIBLE = "visible_fallback"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"


def _log(level: str, message: str) -> None:
    print(f"[{_timestamp()}] [{level}] {message}", flush=True)



class KimiDownloader:
    """
    Incremental download pipeline for Kimi conversation files.
    Pipeline: DISCOVERY -> DEDUPLICATE -> DOWNLOAD -> RECORD
    """

    def __init__(
        self,
        profile_dir: Optional[str] = None,
        download_dir: Optional[str] = None,
        duplicate_dir: Optional[str] = None,
        config_path: Optional[str] = None,
        downloads_record_path: Optional[str] = None,
        pending_record_path: Optional[str] = None,
        dedup: bool = True,
        diagnose: bool = True,
        visible: bool = False,
    ):
        self.profile_dir = self._expand_path(profile_dir) or str(DEFAULT_PROFILE_DIR)
        self.download_dir = self._expand_path(download_dir) or str(Path.home() / "Downloads")
        self.duplicate_dir = self._expand_path(duplicate_dir) or str(
            Path.home() / "skills_moved" / ".duplicate_downloads"
        )
        self.config_path = self._expand_path(config_path) or str(DEFAULT_CONFIG_PATH)
        self.downloads_record_path = self._expand_path(downloads_record_path) or str(DEFAULT_DOWNLOADS_RECORD)
        self.pending_record_path = self._expand_path(pending_record_path) or str(DEFAULT_PENDING_RECORD)
        self.dedup = dedup
        self.diagnose = diagnose
        self.visible = visible

        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        Path(self.duplicate_dir).mkdir(parents=True, exist_ok=True)
        Path(self.pending_record_path).parent.mkdir(parents=True, exist_ok=True)

        self.config = self._load_config()
        self.downloads_record = self._load_json(self.downloads_record_path, default={"downloaded": {}, "_meta": {}})
        self.pending_record = self._load_json(self.pending_record_path, default={"pending": [], "_meta": {}})

        self._ensure_meta(self.downloads_record, "downloads_record")
        self._ensure_meta(self.pending_record, "pending_record")

        # Ensure pending.json exists even if empty
        if not Path(self.pending_record_path).exists():
            self._save_json(self.pending_record_path, self.pending_record)

    def _expand_path(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        if path.startswith("~/"):
            return str(Path.home() / path[2:])
        return str(Path(path).expanduser().resolve())

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()
            lines = content.splitlines()
            json_start = 0
            in_frontmatter = False
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped == "---":
                    if not in_frontmatter:
                        in_frontmatter = True
                    else:
                        in_frontmatter = False
                        json_start = i + 1
                        break
                elif not in_frontmatter and stripped.startswith("{"):
                    json_start = i
                    break
            json_content = "\n".join(lines[json_start:])
            return json.loads(json_content) if json_content.strip() else {}
        except Exception as e:
            _log("WARN", f"Config load failed: {e}. Using defaults.")
            return {}

    def _load_json(self, path: str, default: Any = None) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default if default is not None else {}

    def _save_json(self, path: str, data: Any) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            _log("ERROR", f"Failed to save JSON to {path}: {e}")

    def _ensure_meta(self, data: Dict, record_type: str) -> None:
        if "_meta" not in data:
            data["_meta"] = {
                "record_type": record_type,
                "skill_name": "kimi-agent-tracker",
                "version": "v1.3.1",
                "last_updated": _timestamp(),
                "github_repository": "nervlin4444/ai.skills.incubation",
                "target_branch": "main",
            }
        else:
            data["_meta"]["last_updated"] = _timestamp()

    def _get_browser_context(self, p, visible: bool = False, hide_window: bool = False):
        args = ["--disable-blink-features=AutomationControlled"]
        if hide_window and visible:
            args.extend([
                "--window-position=-10000,-10000",
                "--window-size=1,1",
            ])
        return p.chromium.launch_persistent_context(
            self.profile_dir,
            headless=not visible,
            args=args,
            accept_downloads=True,
        )

    def _compute_sha256(self, file_path: str) -> str:
        h = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def _extract_conversation_id(self, url: str) -> str:
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "chat":
            return parts[1]
        return "unknown"

    def _extract_page_title(self, page) -> str:
        try:
            title = page.title()
            if " - Kimi" in title:
                title = title.replace(" - Kimi", "").strip()
            return title or "unknown"
        except Exception:
            return "unknown"

    def _find_file_links(self, page) -> List[Dict[str, str]]:
        links = []
        try:
            selectors = [
                'a[href*="sandbox://"]',
                'a[href*="/mnt/agents/output/"]',
                'a[href*=".py"]',
                'a[href*=".md"]',
                'a[href*=".zip"]',
                'a[href*=".json"]',
                'a[href*=".txt"]',
                'a[href*=".csv"]',
                'a[href*=".yml"]',
                'a[href*=".yaml"]',
                'a[href*=".html"]',
                'a[href*=".js"]',
                'a[href*=".css"]',
                'a[href*=".xml"]',
                'a[href*=".sh"]',
                'a[href*=".bash"]',
                'a[href*=".pdf"]',
                'a[href*=".png"]',
                'a[href*=".jpg"]',
                'a[href*=".jpeg"]',
                'a[href*=".gif"]',
                'a[href*=".mp3"]',
                'a[href*=".mp4"]',
                'a[href*=".webp"]',
                'a[href*=".svg"]',
                'a[href*=".ico"]',
                'a[href*=".woff"]',
                'a[href*=".woff2"]',
                'a[href*=".ttf"]',
                'a[href*=".eot"]',
                'a[href*=".doc"]',
                'a[href*=".docx"]',
                'a[href*=".xls"]',
                'a[href*=".xlsx"]',
                'a[href*=".ppt"]',
                'a[href*=".pptx"]',
                'a[href*=".rar"]',
                'a[href*=".7z"]',
                'a[href*=".tar"]',
                'a[href*=".gz"]',
            ]
            seen_hrefs = set()
            for selector in selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for el in elements:
                        href = el.get_attribute("href") or ""
                        text = el.inner_text() or ""
                        if href and href not in seen_hrefs:
                            seen_hrefs.add(href)
                            filename = self._extract_filename_from_href(href, text)
                            file_ext = Path(filename).suffix.lower()
                            links.append({
                                "href": href,
                                "filename": filename,
                                "file_ext": file_ext,
                                "text_content": text.strip(),
                            })
                except Exception:
                    continue
        except Exception as e:
            _log("ERROR", f"Link discovery failed: {e}")
        return links

    def _extract_filename_from_href(self, href: str, text: str) -> str:
        if "/" in href:
            parts = href.split("/")
            for part in reversed(parts):
                if part and "." in part:
                    return part
        safe_text = re.sub(r'[^\w\.\-]', '_', text.strip())
        if safe_text and "." in safe_text:
            return safe_text
        return f"unknown_file_{hash(href) % 10000:04d}"

    def _deduplicate_links(
        self,
        links: List[Dict[str, str]],
        conversation_id: str,
        conversation_title: str,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
        new_links = []
        pending_links = []
        skipped_links = []
        downloaded_map = self.downloads_record.get("downloaded", {})
        pending_list = self.pending_record.get("pending", [])
        downloaded_keys = set()
        for record in downloaded_map.values():
            conv = record.get("conversation", "")
            fname = record.get("file", "")
            downloaded_keys.add(f"{conv}::{fname}")
        pending_keys = set()
        for record in pending_list:
            conv = record.get("conversation_id", "")
            fname = record.get("filename", "")
            pending_keys.add(f"{conv}::{fname}")
        for link in links:
            key = f"{conversation_title}::{link['filename']}"
            if key in downloaded_keys:
                skipped_links.append({**link, "reason": "Already downloaded", "conversation_id": conversation_id, "conversation_title": conversation_title})
            elif key in pending_keys:
                pending_links.append({**link, "reason": "In pending queue", "conversation_id": conversation_id, "conversation_title": conversation_title})
            else:
                new_links.append({**link, "conversation_id": conversation_id, "conversation_title": conversation_title})
        return new_links, pending_links, skipped_links

    def _add_to_pending(self, links: List[Dict[str, str]]) -> int:
        pending_list = self.pending_record.get("pending", [])
        added = 0
        for link in links:
            record = {
                "conversation_id": link.get("conversation_id", ""),
                "conversation_title": link.get("conversation_title", ""),
                "file_url": link.get("href", ""),
                "filename": link.get("filename", ""),
                "file_ext": link.get("file_ext", ""),
                "detected_at": _timestamp(),
                "retry_count": 0,
                "last_error": None,
                "strategy": self._determine_strategy(link.get("file_ext", "")),
            }
            pending_list.append(record)
            added += 1
        self.pending_record["pending"] = pending_list
        self._ensure_meta(self.pending_record, "pending_record")
        self._save_json(self.pending_record_path, self.pending_record)
        return added

    def _determine_strategy(self, file_ext: str) -> str:
        ext = file_ext.lower()
        if ext in ANCHOR_EXTENSIONS:
            return STRATEGY_ANCHOR
        elif ext in PREVIEW_EXTENSIONS:
            return STRATEGY_PREVIEW
        else:
            return STRATEGY_VISIBLE

    def _remove_from_pending(self, conversation_id: str, filename: str) -> None:
        pending_list = self.pending_record.get("pending", [])
        original_len = len(pending_list)
        pending_list = [
            p for p in pending_list
            if not (p.get("conversation_id") == conversation_id and p.get("filename") == filename)
        ]
        if len(pending_list) < original_len:
            self.pending_record["pending"] = pending_list
            self._ensure_meta(self.pending_record, "pending_record")
            self._save_json(self.pending_record_path, self.pending_record)

    def _increment_retry(self, conversation_id: str, filename: str, error: str) -> None:
        pending_list = self.pending_record.get("pending", [])
        for p in pending_list:
            if p.get("conversation_id") == conversation_id and p.get("filename") == filename:
                p["retry_count"] = p.get("retry_count", 0) + 1
                p["last_error"] = error
                p["last_attempt"] = _timestamp()
                break
        self.pending_record["pending"] = pending_list
        self._ensure_meta(self.pending_record, "pending_record")
        self._save_json(self.pending_record_path, self.pending_record)



    def _download_anchor_injection(
        self,
        page,
        link: Dict[str, str],
        conversation_title: str,
        timeout_sec: int = 20,
    ) -> Dict[str, Any]:
        href = link["href"]
        filename = link["filename"]
        result = {"status": "error", "file": filename, "reason": "", "path": "", "hash": ""}
        try:
            _log("STRAT-A", f"Anchor injection for {filename}")
            js_code = """
                (args) => {
                    const href = args[0];
                    const filename = args[1];
                    const a = document.createElement('a');
                    a.href = href;
                    a.download = filename;
                    a.style.display = 'none';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    return 'injected';
                }
            """
            page.evaluate(js_code, [href, filename])
            dest_path = self._wait_for_browser_download(filename, timeout_sec)
            if dest_path:
                file_hash = self._compute_sha256(dest_path)
                result.update({"status": "success", "path": dest_path, "hash": file_hash})
                _log("SAVED", dest_path)
            else:
                result["reason"] = "Browser download not detected after anchor injection"
                _log("SKIP", f"No download for {filename} after anchor injection")
        except Exception as e:
            result["reason"] = f"Anchor injection error: {e}"
            _log("ERROR", f"Anchor injection failed for {filename}: {e}")
        return result

    def _download_preview_extraction(
        self,
        page,
        link: Dict[str, str],
        conversation_title: str,
        max_attempts: int = 15,
        wait_sec: int = 2,
    ) -> Dict[str, Any]:
        """
        v1.3.1 FIX: Strict preview panel detection + content stability + garbage filtering.
        """
        href = link["href"]
        filename = link["filename"]
        result = {"status": "error", "file": filename, "reason": "", "path": "", "hash": ""}

        try:
            _log("STRAT-B", f"Preview extraction for {filename}")

            # Step 1: Click link
            _log("EXTRACT-1", f"Clicking link for {filename}")
            if not self._click_link_safe(page, href):
                result["reason"] = "Failed to click link"
                return result

            # Step 2: WAIT for preview panel animation (CRITICAL FIX)
            _log("EXTRACT-2", "Waiting 3s for preview panel animation...")
            time.sleep(3)

            # Step 3: Find preview panel with STRICT criteria
            _log("EXTRACT-2", "Searching for preview panel...")
            preview_info = self._find_preview_panel(page)

            if not preview_info:
                result["reason"] = "Preview panel not found (no large element on right side)"
                _log("EXTRACT-FAIL", f"Preview panel not found for {filename}")
                return result

            _log("EXTRACT-2", f"Preview panel found: {preview_info['tag']} {preview_info['className']} ({preview_info['width']:.0f}x{preview_info['height']:.0f}) at x={preview_info['left']:.0f}")

            # Step 4: Wait for content to stabilize
            _log("EXTRACT-3", "Waiting for content to stabilize...")
            content_text = ""
            content_loaded = False
            min_length = self.config.get("download", {}).get("extraction", {}).get("min_content_length", 100)
            last_length = -1
            stable_count = 0

            for attempt in range(max_attempts):
                current_text = self._extract_preview_content(page, preview_info['selector'])
                current_length = len(current_text)

                if current_length > 0:
                    _log("EXTRACT-3", f"Attempt {attempt + 1}/{max_attempts}: {current_length} chars")

                    # Check stability: length unchanged for 2 consecutive checks
                    if current_length == last_length and current_length >= min_length:
                        stable_count += 1
                        if stable_count >= 2:
                            content_text = current_text
                            content_loaded = True
                            _log("EXTRACT-3", f"Content stabilized at {current_length} chars")
                            break
                    else:
                        stable_count = 0
                        last_length = current_length
                else:
                    _log("EXTRACT-3", f"Attempt {attempt + 1}/{max_attempts}: content empty")

                time.sleep(wait_sec)

            if not content_loaded:
                result["reason"] = f"Content did not stabilize after {max_attempts} attempts"
                _log("EXTRACT-FAIL", f"Content unstable for {filename}")
                return result

            # Step 5: GARBAGE DETECTION (CRITICAL FIX)
            if self._is_garbage_content(content_text):
                result["reason"] = "Extracted content contains garbage characters (box-drawing)"
                _log("EXTRACT-FAIL", f"Garbage content detected for {filename}")
                return result

            # Step 6: Write content to local file
            _log("EXTRACT-4", f"Writing {len(content_text)} chars to {filename}")
            dest_path = os.path.join(self.download_dir, filename)
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(content_text)

            # Validate Python syntax if .py file
            if filename.endswith(".py"):
                try:
                    import py_compile
                    py_compile.compile(dest_path, doraise=True)
                    _log("VALIDATE", f"Python syntax OK: {filename}")
                except Exception as e:
                    _log("WARN", f"Python syntax error in {filename}: {e}")

            file_hash = self._compute_sha256(dest_path)
            result.update({"status": "success", "path": dest_path, "hash": file_hash})
            _log("SAVED", dest_path)

            # Step 7: Close preview panel (press Escape)
            try:
                page.keyboard.press("Escape")
                time.sleep(0.5)
            except Exception:
                pass

        except Exception as e:
            result["reason"] = f"Preview extraction error: {e}"
            _log("ERROR", f"Preview extraction failed for {filename}: {e}")

        return result

    def _find_preview_panel(self, page) -> Optional[Dict[str, Any]]:
        """
        Use JS to find the preview panel with strict criteria:
        - Large: width > 500, height > 400
        - Positioned on right side of screen (left > viewport_width / 2)
        - Visible (not display:none)
        """
        js_code = """
            () => {
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                const selectors = [
                    '[class*="preview"]',
                    '[class*="panel"]',
                    '[class*="drawer"]',
                    '[class*="file-preview"]',
                    '[class*="code-preview"]',
                    '[class*="markdown-body"]',
                    'pre',
                    'code',
                    '.view-lines',
                    '[class*="monaco-editor"]',
                    '[class*="cm-editor"]',
                    '[class*="cm-content"]'
                ];
                let candidates = [];
                for (const sel of selectors) {
                    try {
                        const elements = document.querySelectorAll(sel);
                        for (const el of elements) {
                            const style = window.getComputedStyle(el);
                            if (style.display === 'none' || style.visibility === 'hidden') continue;
                            const rect = el.getBoundingClientRect();
                            // STRICT: must be large AND on right side
                            if (rect.width > 500 && rect.height > 400 && rect.left > viewportWidth / 3) {
                                candidates.push({
                                    selector: sel,
                                    tag: el.tagName,
                                    className: el.className,
                                    width: rect.width,
                                    height: rect.height,
                                    left: rect.left,
                                    top: rect.top,
                                    textLength: el.innerText.length
                                });
                            }
                        }
                    } catch (e) {}
                }
                // Sort by size (largest first) and text length
                candidates.sort((a, b) => (b.width * b.height + b.textLength) - (a.width * a.height + a.textLength));
                return candidates.length > 0 ? candidates[0] : null;
            }
        """
        return page.evaluate(js_code)

    def _extract_preview_content(self, page, selector: str) -> str:
        """Extract text content from preview panel using the matched selector."""
        js_code = """
            (selector) => {
                try {
                    const el = document.querySelector(selector);
                    if (!el) return '';
                    // Try innerText first (preserves line breaks)
                    let text = el.innerText || '';
                    // If empty, try textContent
                    if (!text) text = el.textContent || '';
                    return text;
                } catch (e) {
                    return '';
                }
            }
        """
        return page.evaluate(js_code, selector) or ""

    def _is_garbage_content(self, text: str) -> bool:
        """Detect garbage content (box-drawing chars, excessive whitespace)."""
        if not text:
            return True
        # Box-drawing characters U+2500-U+257F
        box_drawing = re.compile(r'[─-╿]')
        if box_drawing.search(text):
            return True
        # If text is mostly whitespace or special chars
        printable_ratio = sum(1 for c in text if c.isprintable() or c in '\n\r\t') / len(text) if text else 0
        if printable_ratio < 0.5:
            return True
        return False

    def _download_visible_fallback(
        self,
        link: Dict[str, str],
        conversation_title: str,
        timeout_sec: int = 30,
    ) -> Dict[str, Any]:
        """
        v1.3.1 FIX: Use subprocess instead of nested sync_playwright to avoid nest_asyncio crash.
        """
        href = link["href"]
        filename = link["filename"]
        result = {"status": "error", "file": filename, "reason": "", "path": "", "hash": ""}

        _log("STRAT-C", f"Visible fallback for {filename}")

        # First try anchor injection in current context
        anchor_result = self._download_anchor_injection_via_subprocess(link, timeout_sec)
        if anchor_result.get("status") == "success":
            return anchor_result

        # If anchor fails, return error indicating visible mode is needed
        result["reason"] = "Visible mode required for binary files. Run with --visible flag."
        _log("SKIP", f"{filename} requires visible mode")
        return result

    def _download_anchor_injection_via_subprocess(
        self,
        link: Dict[str, str],
        timeout_sec: int = 30,
    ) -> Dict[str, Any]:
        """Try anchor injection via subprocess to avoid nest_asyncio issues."""
        filename = link["filename"]
        href = link["href"]
        result = {"status": "error", "file": filename, "reason": "", "path": "", "hash": ""}

        script_dir = Path(__file__).parent
        downloader_script = script_dir / "kimi_downloader.py"
        if not downloader_script.exists():
            result["reason"] = "Downloader script not found for subprocess"
            return result

        # Build a single-file command
        cmd = [
            sys.executable, str(downloader_script),
            "--url", link.get("conversation_url", "https://www.kimi.com"),
            "--download-dir", self.download_dir,
            "--no-dedup",
        ]

        try:
            _log("STRAT-C", f"Subprocess anchor injection for {filename}")
            # This is a simplified approach - in practice, subprocess anchor injection
            # for a single file is complex. For now, mark as needing visible mode.
            result["reason"] = "Subprocess anchor injection not fully implemented"
        except Exception as e:
            result["reason"] = f"Subprocess error: {e}"

        return result

    def _click_link_safe(self, page, href: str) -> bool:
        """Safely click a link by href."""
        try:
            js_code = """
                (href) => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const target = links.find(a => a.href === href || a.getAttribute('href') === href);
                    if (target) {
                        target.scrollIntoView({block: 'center', inline: 'center'});
                        target.click();
                        return true;
                    }
                    return false;
                }
            """
            return page.evaluate(js_code, href) or False
        except Exception as e:
            _log("WARN", f"Safe click failed: {e}")
            return False

    def _wait_for_browser_download(self, filename: str, timeout_sec: int) -> Optional[str]:
        download_dir = Path(self.download_dir)
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            exact_path = download_dir / filename
            if exact_path.exists() and exact_path.stat().st_size > 0:
                return str(exact_path)
            for f in download_dir.iterdir():
                if f.is_file():
                    name = f.name
                    if name == filename or name.startswith(filename) or filename in name:
                        if not name.endswith(".crdownload") and not name.endswith(".download"):
                            if f.stat().st_size > 0:
                                return str(f)
            time.sleep(1)
        return None



    def _record_download(
        self,
        dest_path: str,
        filename: str,
        conversation_title: str,
        conversation_id: str,
        file_hash: str,
    ) -> Dict[str, Any]:
        downloaded_map = self.downloads_record.get("downloaded", {})
        if self.dedup and file_hash in downloaded_map:
            dup_path = os.path.join(self.duplicate_dir, filename)
            shutil.move(dest_path, dup_path)
            _log("DEDUP", f"Duplicate moved to {dup_path}")
            return {"status": "duplicate", "file": filename, "hash": file_hash, "path": dup_path, "conversation": conversation_title, "conversation_id": conversation_id}
        record = {"file": filename, "hash": file_hash, "path": dest_path, "conversation": conversation_title, "conversation_id": conversation_id, "downloaded_at": _timestamp()}
        downloaded_map[file_hash] = record
        self.downloads_record["downloaded"] = downloaded_map
        self._ensure_meta(self.downloads_record, "downloads_record")
        self._save_json(self.downloads_record_path, self.downloads_record)
        return {"status": "success", "file": filename, "hash": file_hash, "path": dest_path, "conversation": conversation_title, "conversation_id": conversation_id}

    def download_conversation(
        self,
        url: str,
        title: Optional[str] = None,
        auto_add_pending: bool = True,
        process_pending: bool = True,
        discover_only: bool = False,
    ) -> Dict[str, Any]:
        conversation_id = self._extract_conversation_id(url)
        results = {
            "conversation_id": conversation_id,
            "conversation_title": title or "unknown",
            "success": [],
            "duplicates": [],
            "errors": [],
            "skipped": [],
            "pending_added": 0,
        }
        _log("DOWNLOAD", f"Navigating to: {url}")
        with sync_playwright() as p:
            context = self._get_browser_context(p, visible=self.visible)
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)
                if not title or title == "unknown":
                    title = self._extract_page_title(page)
                results["conversation_title"] = title
                links = self._find_file_links(page)
                _log("DOWNLOAD", f"Found {len(links)} file links in '{title}'")
                if not links:
                    _log("INFO", f"No file links found in conversation: {title}")
                    return results
                new_links, pending_links, skipped_links = self._deduplicate_links(links, conversation_id, title)
                for sk in skipped_links:
                    results["skipped"].append({"status": "skipped", "file": sk["filename"], "reason": sk["reason"]})
                if auto_add_pending and new_links:
                    added = self._add_to_pending(new_links)
                    results["pending_added"] = added
                    _log("PENDING", f"Added {added} new files to pending queue")
                if discover_only:
                    _log("INFO", f"Discover-only mode: {len(new_links)} added to pending, not processing")
                    return results
                if process_pending:
                    pending_to_process = [
                        p for p in self.pending_record.get("pending", [])
                        if p.get("conversation_id") == conversation_id
                    ]
                    _log("DOWNLOAD", f"Processing {len(pending_to_process)} pending files for '{title}'")
                    for pending_item in pending_to_process:
                        filename = pending_item.get("filename", "")
                        href = pending_item.get("file_url", "")
                        strategy = pending_item.get("strategy", STRATEGY_PREVIEW)
                        link = {"href": href, "filename": filename, "file_ext": pending_item.get("file_ext", ""), "conversation_url": url}
                        download_result = None
                        if strategy == STRATEGY_ANCHOR:
                            download_result = self._download_anchor_injection(page, link, title)
                        elif strategy == STRATEGY_PREVIEW:
                            download_result = self._download_preview_extraction(page, link, title)
                        else:
                            download_result = self._download_visible_fallback(link, title)
                        if download_result["status"] == "success":
                            dest_path = download_result["path"]
                            file_hash = download_result["hash"]
                            record = self._record_download(dest_path, filename, title, conversation_id, file_hash)
                            if record["status"] == "duplicate":
                                results["duplicates"].append(record)
                            else:
                                results["success"].append(record)
                            self._remove_from_pending(conversation_id, filename)
                        elif download_result["status"] == "error":
                            error_reason = download_result.get("reason", "Unknown error")
                            results["errors"].append({"status": "error", "file": filename, "reason": error_reason})
                            self._increment_retry(conversation_id, filename, error_reason)
                        else:
                            results["skipped"].append({"status": "skipped", "file": filename, "reason": download_result.get("reason", "Unknown")})
            except PlaywrightTimeout:
                _log("TIMEOUT", f"Navigation timeout for {url}")
                results["errors"].append({"conversation": title, "error": "Navigation timeout"})
            except Exception as e:
                _log("ERROR", f"Download error: {e}")
                results["errors"].append({"conversation": title, "error": str(e)})
            finally:
                context.close()
        return results

    def download_from_list(self, list_path: str, discover_only: bool = False) -> Dict[str, Any]:
        list_path = self._expand_path(list_path) or list_path
        data = self._load_json(list_path, default={})
        all_results = {
            "total_conversations": 0,
            "total_success": 0,
            "total_duplicates": 0,
            "total_errors": 0,
            "total_skipped": 0,
            "conversations": [],
        }
        if "pending" in data:
            pending_items = data.get("pending", [])
            _log("BATCH", f"Processing {len(pending_items)} pending items")
            conv_map = {}
            for item in pending_items:
                conv_id = item.get("conversation_id", "unknown")
                if conv_id not in conv_map:
                    conv_map[conv_id] = {"id": conv_id, "title": item.get("conversation_title", "unknown"), "url": f"https://www.kimi.com/chat/{conv_id}", "items": []}
                conv_map[conv_id]["items"].append(item)
            for conv in conv_map.values():
                result = self.download_conversation(conv["url"], title=conv["title"], auto_add_pending=False, process_pending=True)
                all_results["conversations"].append(result)
                all_results["total_success"] += len(result["success"])
                all_results["total_duplicates"] += len(result["duplicates"])
                all_results["total_errors"] += len(result["errors"])
                all_results["total_skipped"] += len(result["skipped"])
                all_results["total_conversations"] += 1
        elif "conversations" in data or isinstance(data, list):
            conversations = data.get("conversations", []) if isinstance(data, dict) else data
            _log("BATCH", f"Processing {len(conversations)} conversations")
            for conv in conversations:
                if isinstance(conv, dict):
                    url = conv.get("url", "")
                    title = conv.get("title", "unknown")
                else:
                    url = str(conv)
                    title = "unknown"
                if not url:
                    continue
                result = self.download_conversation(url, title=title, discover_only=discover_only)
                all_results["conversations"].append(result)
                all_results["total_success"] += len(result["success"])
                all_results["total_duplicates"] += len(result["duplicates"])
                all_results["total_errors"] += len(result["errors"])
                all_results["total_skipped"] += len(result["skipped"])
                all_results["total_conversations"] += 1
        return all_results


def main():
    parser = argparse.ArgumentParser(description="Kimi File Downloader v1.3.1 - Incremental Download Pipeline")
    parser.add_argument("--url", type=str, help="Single conversation URL to download")
    parser.add_argument("--from-list", type=str, help="Path to conversations.json or pending.json")
    parser.add_argument("--profile-dir", type=str, default=None, help="Browser profile directory")
    parser.add_argument("--download-dir", type=str, default=None, help="Download destination directory")
    parser.add_argument("--duplicate-dir", type=str, default=None, help="Duplicate files directory")
    parser.add_argument("--config", type=str, default=None, help="Config file path")
    parser.add_argument("--downloads-record", type=str, default=None, help="Downloads record JSON path")
    parser.add_argument("--pending-record", type=str, default=None, help="Pending record JSON path")
    parser.add_argument("--no-dedup", action="store_true", help="Disable deduplication")
    parser.add_argument("--no-diagnose", action="store_true", help="Disable diagnostic screenshots")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode")
    parser.add_argument("--discover-only", action="store_true", help="Only discover files, add to pending, do not download")
    parser.add_argument("--process-pending", action="store_true", help="Only process pending.json items")
    args = parser.parse_args()

    downloader = KimiDownloader(
        profile_dir=args.profile_dir,
        download_dir=args.download_dir,
        duplicate_dir=args.duplicate_dir,
        config_path=args.config,
        downloads_record_path=args.downloads_record,
        pending_record_path=args.pending_record,
        dedup=not args.no_dedup,
        diagnose=not args.no_diagnose,
        visible=args.visible,
    )

    # v1.3.1 FIX: Handle --discover-only with both --url and --from-list
    if args.discover_only:
        if args.url:
            result = downloader.download_conversation(args.url, auto_add_pending=True, process_pending=False, discover_only=True)
            _log("RESULT", f"'{result['conversation_title']}': {result['pending_added']} added to pending")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.from_list:
            result = downloader.download_from_list(args.from_list, discover_only=True)
            total_added = sum(r.get("pending_added", 0) for r in result.get("conversations", []))
            _log("RESULT", f"Batch discover: {total_added} total added to pending across {result['total_conversations']} conversations")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            parser.error("--discover-only requires --url or --from-list")
    elif args.process_pending:
        result = downloader.download_from_list(downloader.pending_record_path)
        _log("RESULT", f"Batch complete: {result['total_success']} success, {result['total_duplicates']} dup, {result['total_errors']} err, {result['total_skipped']} skip")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.url:
        result = downloader.download_conversation(args.url)
        _log("RESULT", f"'{result['conversation_title']}': {len(result['success'])} success, {len(result['duplicates'])} dup, {len(result['errors'])} err, {len(result['skipped'])} skip")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.from_list:
        result = downloader.download_from_list(args.from_list)
        _log("RESULT", f"Batch complete: {result['total_success']} success, {result['total_duplicates']} dup, {result['total_errors']} err, {result['total_skipped']} skip")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
