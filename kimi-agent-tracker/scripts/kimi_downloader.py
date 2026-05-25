"""
---
title: Kimi File Downloader Core Engine
name: kimi-agent-tracker
description: Playwright-based file downloader for Kimi conversations. Supports incremental download pipeline with discovery, deduplication, and categorized extraction strategies.
version: v1.3.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T16:53:00+0800
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
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

# Third-party imports with graceful fallback
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

# Constants
DEFAULT_PROFILE_DIR = Path.home() / ".kimi_auth" / "browser_profile_chromium"
DEFAULT_CONFIG_PATH = Path.home() / ".workbuddy" / "skills" / "kimi-agent-tracker" / ".config" / "kimi_tracker_config.json"
DEFAULT_DOWNLOADS_RECORD = Path.home() / ".workbuddy" / "skills" / "kimi-agent-tracker" / ".config" / "downloads.json"
DEFAULT_PENDING_RECORD = Path.home() / ".workbuddy" / "skills" / "kimi-agent-tracker" / ".config" / "pending.json"
DEFAULT_DIAGNOSE_DIR = Path.home() / ".workbuddy" / "skills" / "kimi-agent-tracker" / ".logs" / "diagnose"

# File type classification
TEXT_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".yml", ".yaml", ".html", ".js", ".css", ".xml", ".sh", ".bash"}
BINARY_EXTENSIONS = {".zip", ".rar", ".7z", ".tar", ".gz", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".mp3", ".mp4", ".avi", ".mov", ".webp", ".svg", ".ico", ".ttf", ".woff", ".woff2", ".eot"}

# Strategy mapping
STRATEGY_ANCHOR = "anchor_injection"       # Fast, headless, for text files
STRATEGY_PREVIEW = "preview_extraction"    # DOM extraction, for .py files
STRATEGY_VISIBLE = "visible_fallback"        # Visible browser moved off-screen, for binary files


def _timestamp() -> str:
    """Return ISO format timestamp with timezone."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"


def _log(level: str, message: str) -> None:
    """Print structured log line."""
    print(f"[{_timestamp()}] [{level}] {message}", flush=True)



class KimiDownloader:
    """
    Incremental download pipeline for Kimi conversation files.

    Pipeline stages:
        1. DISCOVERY: Scan conversation page for file links.
        2. DEDUPLICATE: Compare against downloads.json and pending.json.
        3. DOWNLOAD: Apply strategy per file type (anchor / preview / visible).
        4. RECORD: Update pending.json and downloads.json.
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

        # Ensure directories exist
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        Path(self.duplicate_dir).mkdir(parents=True, exist_ok=True)
        Path(self.pending_record_path).parent.mkdir(parents=True, exist_ok=True)

        # Load config
        self.config = self._load_config()

        # Load state files
        self.downloads_record = self._load_json(self.downloads_record_path, default={"downloaded": {}, "_meta": {}})
        self.pending_record = self._load_json(self.pending_record_path, default={"pending": [], "_meta": {}})

        # Ensure _meta exists
        self._ensure_meta(self.downloads_record, "downloads_record")
        self._ensure_meta(self.pending_record, "pending_record")

    def _expand_path(self, path: Optional[str]) -> Optional[str]:
        """Expand user home directory (~) to absolute path."""
        if not path:
            return None
        if path.startswith("~/"):
            return str(Path.home() / path[2:])
        return str(Path(path).expanduser().resolve())

    def _load_config(self) -> Dict[str, Any]:
        """Load tracker config, skipping frontmatter if present."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Skip frontmatter (lines starting with # or --- block)
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
        """Load JSON file with fallback default."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default if default is not None else {}

    def _save_json(self, path: str, data: Any) -> None:
        """Save JSON file with pretty formatting."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            _log("ERROR", f"Failed to save JSON to {path}: {e}")

    def _ensure_meta(self, data: Dict, record_type: str) -> None:
        """Ensure _meta block exists in state file."""
        if "_meta" not in data:
            data["_meta"] = {
                "record_type": record_type,
                "skill_name": "kimi-agent-tracker",
                "version": "v1.3.0",
                "last_updated": _timestamp(),
                "github_repository": "nervlin4444/ai.skills.incubation",
                "target_branch": "main",
            }
        else:
            data["_meta"]["last_updated"] = _timestamp()

    def _get_browser_context(self, p, visible: bool = False, hide_window: bool = False):
        """
        Launch persistent browser context.

        Args:
            visible: If True, run in headed mode (window shown).
            hide_window: If True and visible, move window off-screen via Chromium args.
        """
        args = ["--disable-blink-features=AutomationControlled"]
        if hide_window and visible:
            # Move window off-screen to avoid interfering with user workflow
            args.extend([
                "--window-position=-10000,-10000",
                "--window-size=1,1",
            ])

        headless = not visible
        return p.chromium.launch_persistent_context(
            self.profile_dir,
            headless=headless,
            args=args,
            accept_downloads=True,
        )

    def _compute_sha256(self, file_path: str) -> str:
        """Compute SHA256 hash of file contents."""
        h = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def _extract_conversation_id(self, url: str) -> str:
        """Extract conversation ID from Kimi chat URL."""
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "chat":
            return parts[1]
        return "unknown"

    def _extract_page_title(self, page) -> str:
        """Extract conversation title from page."""
        try:
            title = page.title()
            # Remove " - Kimi" suffix
            if " - Kimi" in title:
                title = title.replace(" - Kimi", "").strip()
            return title or "unknown"
        except Exception:
            return "unknown"



    # =====================================================================
    # STAGE 1: DISCOVERY - Scan page for downloadable file links
    # =====================================================================

    def _find_file_links(self, page) -> List[Dict[str, str]]:
        """
        Scan conversation page for all file attachment links.

        Returns list of dicts with keys:
            href, filename, file_ext, text_content
        """
        links = []
        try:
            # Primary selector: links containing sandbox:// or file-like hrefs
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
                            # Extract filename from href
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
        """Extract clean filename from href or fallback to text."""
        # Try to extract from href path
        if "/" in href:
            parts = href.split("/")
            for part in reversed(parts):
                if part and "." in part:
                    return part
        # Fallback: use text content, sanitize
        safe_text = re.sub(r'[^\w\.\-]', '_', text.strip())
        if safe_text and "." in safe_text:
            return safe_text
        # Last resort: generic name with hash
        return f"unknown_file_{hash(href) % 10000:04d}"

    # =====================================================================
    # STAGE 2: DEDUPLICATION - Compare against local records
    # =====================================================================

    def _deduplicate_links(
        self,
        links: List[Dict[str, str]],
        conversation_id: str,
        conversation_title: str,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Filter links against downloads.json and pending.json.

        Returns:
            (new_links, pending_links, skipped_links)
            new_links: Not in downloads and not in pending -> add to pending
            pending_links: Already in pending -> keep for processing
            skipped_links: Already in downloads -> skip entirely
        """
        new_links = []
        pending_links = []
        skipped_links = []

        downloaded_map = self.downloads_record.get("downloaded", {})
        pending_list = self.pending_record.get("pending", [])

        # Build lookup sets for fast checking
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
                skipped_links.append({
                    **link,
                    "reason": "Already downloaded",
                    "conversation_id": conversation_id,
                    "conversation_title": conversation_title,
                })
            elif key in pending_keys:
                pending_links.append({
                    **link,
                    "reason": "In pending queue",
                    "conversation_id": conversation_id,
                    "conversation_title": conversation_title,
                })
            else:
                new_links.append({
                    **link,
                    "conversation_id": conversation_id,
                    "conversation_title": conversation_title,
                })

        return new_links, pending_links, skipped_links

    def _add_to_pending(self, links: List[Dict[str, str]]) -> int:
        """Add new links to pending.json. Returns count added."""
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
        """Determine download strategy based on file extension."""
        ext = file_ext.lower()
        if ext in TEXT_EXTENSIONS and ext != ".py":
            return STRATEGY_ANCHOR
        elif ext == ".py":
            return STRATEGY_PREVIEW
        else:
            return STRATEGY_VISIBLE

    def _remove_from_pending(self, conversation_id: str, filename: str) -> None:
        """Remove successfully downloaded file from pending.json."""
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
        """Increment retry count for failed download in pending.json."""
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



    # =====================================================================
    # STAGE 3: DOWNLOAD - Strategy implementations
    # =====================================================================

    def _download_anchor_injection(
        self,
        page,
        link: Dict[str, str],
        conversation_title: str,
        timeout_sec: int = 20,
    ) -> Dict[str, Any]:
        """
        Strategy A: Create anchor element with download attribute and click.
        Works in headless mode for text files. Fast (~8s per file).
        """
        href = link["href"]
        filename = link["filename"]
        result = {"status": "error", "file": filename, "reason": "", "path": "", "hash": ""}

        try:
            _log("STRAT-A", f"Anchor injection for {filename}")

            # Use JS to create anchor and trigger download
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

            # Wait for download to appear in browser download directory
            dest_path = self._wait_for_browser_download(filename, timeout_sec)
            if dest_path:
                file_hash = self._compute_sha256(dest_path)
                result.update({
                    "status": "success",
                    "path": dest_path,
                    "hash": file_hash,
                })
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
        max_attempts: int = 10,
        wait_sec: int = 3,
    ) -> Dict[str, Any]:
        """
        Strategy B: Click link, wait for preview panel, extract content from DOM.
        For .py files in headless mode. Extended wait for slow loading.
        """
        href = link["href"]
        filename = link["filename"]
        result = {"status": "error", "file": filename, "reason": "", "path": "", "hash": ""}

        try:
            _log("STRAT-B", f"Preview extraction for {filename}")

            # Step 1: Click the link to open preview panel
            _log("EXTRACT-1", f"Clicking link for {filename}")
            self._click_link_safe(page, href)

            # Step 2: Wait for preview panel with extended retry
            _log("EXTRACT-2", "Waiting for preview panel...")
            preview_selectors = self.config.get("download", {}).get("extraction", {}).get(
                "preview_selectors",
                [
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
                ]
            )

            preview_found = False
            preview_selector = ""
            for attempt in range(max_attempts):
                for selector in preview_selectors:
                    try:
                        el = page.query_selector(selector)
                        if el:
                            # Validate dimensions (must be reasonably large)
                            box = el.bounding_box()
                            if box and box.get("width", 0) > 200 and box.get("height", 0) > 200:
                                preview_found = True
                                preview_selector = selector
                                _log("EXTRACT-2", f"Preview panel found: {selector} ({box.get('width', 0):.0f}x{box.get('height', 0):.0f})")
                                break
                    except Exception:
                        continue
                if preview_found:
                    break
                _log("EXTRACT-2", f"Preview not ready, attempt {attempt + 1}/{max_attempts}")
                time.sleep(wait_sec)

            if not preview_found:
                result["reason"] = "Preview panel not found after max attempts"
                _log("EXTRACT-FAIL", f"Preview panel timeout for {filename}")
                return result

            # Step 3: Wait for content to load with extended retry
            _log("EXTRACT-3", "Waiting for content to load...")
            content_selectors = self.config.get("download", {}).get("extraction", {}).get(
                "content_selectors",
                [
                    'pre code',
                    '.view-lines',
                    '.markdown-body',
                    '[class*="cm-content"]',
                    '[class*="monaco-editor"] .view-lines',
                    'pre',
                    'code',
                ]
            )

            content_text = ""
            content_loaded = False
            min_length = self.config.get("download", {}).get("extraction", {}).get("min_content_length", 100)

            for attempt in range(max_attempts):
                for selector in content_selectors:
                    try:
                        el = page.query_selector(selector)
                        if el:
                            text = el.inner_text() or ""
                            if len(text) >= min_length:
                                content_text = text
                                content_loaded = True
                                _log("EXTRACT-3", f"Content loaded: {len(text)} chars")
                                break
                            elif len(text) > 0:
                                _log("EXTRACT-3", f"Content partial: {len(text)} chars (need {min_length})")
                    except Exception:
                        continue
                if content_loaded:
                    break
                _log("EXTRACT-3", f"Content not ready, attempt {attempt + 1}/{max_attempts}")
                time.sleep(wait_sec)

            if not content_loaded:
                result["reason"] = f"Content empty or too short after {max_attempts} attempts"
                _log("EXTRACT-FAIL", f"Content extraction failed for {filename}")
                return result

            # Step 4: Write content to local file
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
                    # Do not fail - content might be valid but with edge cases

            file_hash = self._compute_sha256(dest_path)
            result.update({
                "status": "success",
                "path": dest_path,
                "hash": file_hash,
            })
            _log("SAVED", dest_path)

        except Exception as e:
            result["reason"] = f"Preview extraction error: {e}"
            _log("ERROR", f"Preview extraction failed for {filename}: {e}")

        return result

    def _download_visible_fallback(
        self,
        link: Dict[str, str],
        conversation_title: str,
        timeout_sec: int = 30,
    ) -> Dict[str, Any]:
        """
        Strategy C: Visible browser with window moved off-screen.
        For binary files that refuse to download in headless mode.
        """
        href = link["href"]
        filename = link["filename"]
        result = {"status": "error", "file": filename, "reason": "", "path": "", "hash": ""}

        _log("STRAT-C", f"Visible fallback for {filename}")

        try:
            with sync_playwright() as p:
                # Launch visible but hidden off-screen
                context = self._get_browser_context(p, visible=True, hide_window=True)
                page = context.new_page()

                try:
                    # Re-navigate to conversation
                    conv_url = link.get("conversation_url", "")
                    if conv_url:
                        page.goto(conv_url, wait_until="domcontentloaded", timeout=30000)
                        time.sleep(2)

                    # Use anchor injection in visible mode
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

                    # Wait for download
                    dest_path = self._wait_for_browser_download(filename, timeout_sec)
                    if dest_path:
                        file_hash = self._compute_sha256(dest_path)
                        result.update({
                            "status": "success",
                            "path": dest_path,
                            "hash": file_hash,
                        })
                        _log("SAVED", dest_path)
                    else:
                        result["reason"] = "Browser download not detected in visible mode"
                        _log("SKIP", f"No download for {filename} in visible mode")

                finally:
                    context.close()

        except Exception as e:
            result["reason"] = f"Visible fallback error: {e}"
            _log("ERROR", f"Visible fallback failed for {filename}: {e}")

        return result

    def _click_link_safe(self, page, href: str) -> bool:
        """Safely click a link by href using multiple strategies."""
        try:
            # Strategy 1: Find by href and scroll into view
            js_code = """
                (href) => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const target = links.find(a => a.href === href || a.getAttribute('href') === href);
                    if (target) {
                        target.scrollIntoView({block: 'center', inline: 'center'});
                        return {found: true, x: 0, y: 0};
                    }
                    return {found: false};
                }
            """
            res = page.evaluate(js_code, href)
            if res and res.get("found"):
                time.sleep(0.5)
                # Try mouse click at center of viewport
                viewport = page.viewport_size
                if viewport:
                    x = viewport["width"] // 2
                    y = viewport["height"] // 2
                    page.mouse.move(x, y)
                    page.mouse.down()
                    time.sleep(0.15)
                    page.mouse.up()
                    return True
            return False
        except Exception as e:
            _log("WARN", f"Safe click failed: {e}")
            return False

    def _wait_for_browser_download(self, filename: str, timeout_sec: int) -> Optional[str]:
        """Wait for file to appear in browser download directory."""
        download_dir = Path(self.download_dir)
        start_time = time.time()

        while time.time() - start_time < timeout_sec:
            # Check for exact filename
            exact_path = download_dir / filename
            if exact_path.exists() and exact_path.stat().st_size > 0:
                return str(exact_path)

            # Check for partial downloads (.crdownload, .download)
            for f in download_dir.iterdir():
                if f.is_file():
                    name = f.name
                    if name == filename or name.startswith(filename) or filename in name:
                        if not name.endswith(".crdownload") and not name.endswith(".download"):
                            if f.stat().st_size > 0:
                                return str(f)

            time.sleep(1)

        return None



    # =====================================================================
    # STAGE 4: RECORD - Update downloads.json and pending.json
    # =====================================================================

    def _record_download(
        self,
        dest_path: str,
        filename: str,
        conversation_title: str,
        conversation_id: str,
        file_hash: str,
    ) -> Dict[str, Any]:
        """
        Record successful download. Handle deduplication.
        Returns record dict with status: success | duplicate.
        """
        downloaded_map = self.downloads_record.get("downloaded", {})

        # Check for duplicate by hash
        if self.dedup and file_hash in downloaded_map:
            # Move to duplicate directory
            dup_path = os.path.join(self.duplicate_dir, filename)
            shutil.move(dest_path, dup_path)
            _log("DEDUP", f"Duplicate moved to {dup_path}")
            return {
                "status": "duplicate",
                "file": filename,
                "hash": file_hash,
                "path": dup_path,
                "conversation": conversation_title,
                "conversation_id": conversation_id,
            }

        # Record as new download
        record = {
            "file": filename,
            "hash": file_hash,
            "path": dest_path,
            "conversation": conversation_title,
            "conversation_id": conversation_id,
            "downloaded_at": _timestamp(),
        }
        downloaded_map[file_hash] = record
        self.downloads_record["downloaded"] = downloaded_map
        self._ensure_meta(self.downloads_record, "downloads_record")
        self._save_json(self.downloads_record_path, self.downloads_record)

        return {
            "status": "success",
            "file": filename,
            "hash": file_hash,
            "path": dest_path,
            "conversation": conversation_title,
            "conversation_id": conversation_id,
        }

    # =====================================================================
    # MAIN DOWNLOAD FLOW
    # =====================================================================

    def download_conversation(
        self,
        url: str,
        title: Optional[str] = None,
        auto_add_pending: bool = True,
        process_pending: bool = True,
    ) -> Dict[str, Any]:
        """
        Full pipeline for a single conversation:
            1. Navigate to page
            2. DISCOVER: Find all file links
            3. DEDUPLICATE: Filter against downloads.json and pending.json
            4. If auto_add_pending: Add new links to pending.json
            5. If process_pending: Process pending files for this conversation
            6. RECORD: Update state files

        Returns result dict with success/duplicate/error/skip lists.
        """
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
                # Navigate
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

                # Extract title if not provided
                if not title or title == "unknown":
                    title = self._extract_page_title(page)
                results["conversation_title"] = title

                # STAGE 1: DISCOVERY
                links = self._find_file_links(page)
                _log("DOWNLOAD", f"Found {len(links)} file links in '{title}'")

                if not links:
                    _log("INFO", f"No file links found in conversation: {title}")
                    return results

                # STAGE 2: DEDUPLICATION
                new_links, pending_links, skipped_links = self._deduplicate_links(
                    links, conversation_id, title
                )

                # Report skipped
                for sk in skipped_links:
                    results["skipped"].append({
                        "status": "skipped",
                        "file": sk["filename"],
                        "reason": sk["reason"],
                    })

                # STAGE 3: ADD NEW TO PENDING
                if auto_add_pending and new_links:
                    added = self._add_to_pending(new_links)
                    results["pending_added"] = added
                    _log("PENDING", f"Added {added} new files to pending queue")

                # STAGE 4: PROCESS PENDING FILES FOR THIS CONVERSATION
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

                        # Build link dict
                        link = {
                            "href": href,
                            "filename": filename,
                            "file_ext": pending_item.get("file_ext", ""),
                            "conversation_url": url,
                        }

                        # Apply strategy
                        download_result = None
                        if strategy == STRATEGY_ANCHOR:
                            download_result = self._download_anchor_injection(page, link, title)
                        elif strategy == STRATEGY_PREVIEW:
                            download_result = self._download_preview_extraction(page, link, title)
                        else:
                            download_result = self._download_visible_fallback(link, title)

                        # Handle result
                        if download_result["status"] == "success":
                            dest_path = download_result["path"]
                            file_hash = download_result["hash"]

                            # Record download
                            record = self._record_download(
                                dest_path, filename, title, conversation_id, file_hash
                            )

                            if record["status"] == "duplicate":
                                results["duplicates"].append(record)
                            else:
                                results["success"].append(record)

                            # Remove from pending
                            self._remove_from_pending(conversation_id, filename)

                        elif download_result["status"] == "error":
                            error_reason = download_result.get("reason", "Unknown error")
                            results["errors"].append({
                                "status": "error",
                                "file": filename,
                                "reason": error_reason,
                            })
                            # Increment retry in pending
                            self._increment_retry(conversation_id, filename, error_reason)
                        else:
                            results["skipped"].append({
                                "status": "skipped",
                                "file": filename,
                                "reason": download_result.get("reason", "Unknown"),
                            })

            except PlaywrightTimeout:
                _log("TIMEOUT", f"Navigation timeout for {url}")
                results["errors"].append({
                    "conversation": title,
                    "error": "Navigation timeout",
                })
            except Exception as e:
                _log("ERROR", f"Download error: {e}")
                results["errors"].append({
                    "conversation": title,
                    "error": str(e),
                })
            finally:
                context.close()

        return results

    def download_from_list(self, list_path: str) -> Dict[str, Any]:
        """
        Batch download from conversations.json or pending.json.

        If list_path points to pending.json, process only pending items.
        If list_path points to conversations.json, discover + dedup + process.
        """
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

        # Detect file type by content structure
        if "pending" in data:
            # Processing pending.json
            pending_items = data.get("pending", [])
            _log("BATCH", f"Processing {len(pending_items)} pending items")

            # Group by conversation
            conv_map = {}
            for item in pending_items:
                conv_id = item.get("conversation_id", "unknown")
                if conv_id not in conv_map:
                    conv_map[conv_id] = {
                        "id": conv_id,
                        "title": item.get("conversation_title", "unknown"),
                        "url": f"https://www.kimi.com/chat/{conv_id}",
                        "items": [],
                    }
                conv_map[conv_id]["items"].append(item)

            for conv in conv_map.values():
                result = self.download_conversation(
                    conv["url"],
                    title=conv["title"],
                    auto_add_pending=False,  # Already in pending
                    process_pending=True,
                )
                all_results["conversations"].append(result)
                all_results["total_success"] += len(result["success"])
                all_results["total_duplicates"] += len(result["duplicates"])
                all_results["total_errors"] += len(result["errors"])
                all_results["total_skipped"] += len(result["skipped"])
                all_results["total_conversations"] += 1

        elif "conversations" in data or isinstance(data, list):
            # Processing conversations.json
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

                result = self.download_conversation(url, title=title)
                all_results["conversations"].append(result)
                all_results["total_success"] += len(result["success"])
                all_results["total_duplicates"] += len(result["duplicates"])
                all_results["total_errors"] += len(result["errors"])
                all_results["total_skipped"] += len(result["skipped"])
                all_results["total_conversations"] += 1

        return all_results



# =====================================================================
# CLI INTERFACE
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Kimi File Downloader v1.3.0 - Incremental Download Pipeline"
    )
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

    if args.discover_only and args.url:
        # Only discover and add to pending
        result = downloader.download_conversation(
            args.url,
            auto_add_pending=True,
            process_pending=False,
        )
        _log("RESULT", f"'{result['conversation_title']}': {result['pending_added']} added to pending")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.process_pending:
        # Only process pending items
        result = downloader.download_from_list(downloader.pending_record_path)
        _log("RESULT", f"Batch complete: {result['total_success']} success, {result['total_duplicates']} dup, {result['total_errors']} err, {result['total_skipped']} skip")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.url:
        # Full pipeline: discover + dedup + add pending + process pending
        result = downloader.download_conversation(args.url)
        _log("RESULT", f"'{result['conversation_title']}': {len(result['success'])} success, {len(result['duplicates'])} dup, {len(result['errors'])} err, {len(result['skipped'])} skip")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.from_list:
        # Batch from list
        result = downloader.download_from_list(args.from_list)
        _log("RESULT", f"Batch complete: {result['total_success']} success, {result['total_duplicates']} dup, {result['total_errors']} err, {result['total_skipped']} skip")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
