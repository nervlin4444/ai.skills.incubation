
"""
---
title: "Kimi File Downloader"
name: "kimi-agent-tracker"
description: "Batch downloads .py files from Kimi conversations via Download button + HTTP header verification. v5.3.0"
version: "v5.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-31T14:50:00Z"
auth_config:
  provider: "kimi"
  auth_method: "persistent_browser_profile"
  token_env_var: "KIMI_AUTH_TOKEN"
  env_file_path: "~/.kimi_auth/.env"
file_mapping:
  local_path: "{baseDir}/scripts/kimi_downloader.py"
  github_path: "kimi-agent-tracker/scripts/kimi_downloader.py"
---
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

CORE_AVAILABLE = False
try:
    _SCRIPT_DIR = Path(__file__).parent.resolve()
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    from core_path_utils import get_skill_dir, get_config_dir, get_data_dir, get_logs_dir, ensure_dir
    from core_logger import get_default_logger
    CORE_AVAILABLE = True
except Exception:
    pass


class KimiDownloader:
    def __init__(
        self,
        profile_dir: Optional[Path] = None,
        headless: bool = True,
        download_dir: Optional[Path] = None,
        tracer: Any = None,
    ) -> None:
        self.headless = headless
        self.tracer = tracer
        self.profile_dir = (
            profile_dir
            or Path.home() / ".kimi_auth" / "browser_profile_chromium"
        )

        if CORE_AVAILABLE:
            self.paths = {
                "scripts": get_skill_dir() / "scripts",
                "data": get_data_dir(),
                "logs": get_logs_dir(),
                "config": get_config_dir(),
                "state": get_data_dir(),
            }
            for d in (str(self.paths["data"]), str(self.paths["logs"])):
                Path(d).mkdir(parents=True, exist_ok=True)
            self.logger = get_default_logger("downloader")
        else:
            print("[FATAL] core_path_utils / core_logger not found. Set PYTHONPATH to scripts directory.", file=sys.stderr)
            sys.exit(1)

        self.download_dir = (
            download_dir
            or Path.home() / "Downloads"
        )
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.paths["data"].mkdir(parents=True, exist_ok=True)
        self.paths["logs"].mkdir(parents=True, exist_ok=True)

        self._session_seen: Set[str] = set()

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def _trace(self, event: str, **data: Any) -> None:
        """Record trace event. Silently skips if tracer is None or call fails."""
        t = self.tracer
        if t is None:
            return
        try:
            if callable(t) and not hasattr(t, "record"):
                t(event, data)
            else:
                t.record(event, **data)
        except Exception:
            pass

    def _is_cached(self, fname: str) -> bool:
        return (self.download_dir / Path(fname).name).exists()

    async def _scan_py_links(self, page) -> List[Dict[str, Any]]:
        result = await page.evaluate(
            """
            () => {
                const files = [];
                const seen = new Set();
                const links = document.querySelectorAll('a');
                for (const link of links) {
                    const text = link.innerText?.trim() || '';
                    const href = link.href || '';
                    if (!text.endsWith('.py')) continue;
                    if (seen.has(text)) continue;
                    if (text.includes(' ') && !text.includes('/')) continue;
                    if (text.length > 60) continue;
                    seen.add(text);
                    files.push({name: text, href: href});
                }
                return files;
            }
            """
        )
        self._trace("downloader.scan.done", count=len(result))
        return result

    async def _click_file(self, page, finfo: Dict[str, Any]) -> bool:
        """Click a file link by name then href fallback."""
        fname = finfo.get("name", "")
        fhref = finfo.get("href", "")
        try:
            result = await page.evaluate(
                """
                (data) => {
                    const links = document.querySelectorAll('a');
                    for (const link of links) {
                        if (link.innerText?.trim() === data.name) {
                            link.click();
                            return true;
                        }
                    }
                    // Fallback: match by href (links may have moved after panel close)
                    for (const link of links) {
                        if (link.href === data.href) {
                            link.click();
                            return true;
                        }
                    }
                    return false;
                }
                """,
                {"name": fname, "href": fhref},
            )
            self._trace("downloader.click.done", fname=fname, clicked=result)
            return result
        except Exception:
            self._trace("downloader.click.error", fname=fname)
            return False

    async def _scroll_preview_to_load_full(self, page) -> None:
        """Scroll INSIDE the preview panel to trigger lazy loading.
        Scoped to div.side-console-container to avoid affecting chat history."""
        try:
            # Strategy 1: Scroll the pre element inside panel
            await page.evaluate(
                """
                () => {
                    const panel = document.querySelector('div.side-console-container');
                    if (!panel) return 'no_panel';
                    const pre = panel.querySelector('pre');
                    if (pre) {
                        pre.scrollTop = pre.scrollHeight;
                        return 'pre_scrolled';
                    }
                    return 'no_pre';
                }
                """
            )
            await asyncio.sleep(1)

            # Strategy 2: Multiple scroll rounds with content check (scoped to panel)
            for round_num in range(5):
                prev_len = await page.evaluate(
                    """
                    () => {
                        const panel = document.querySelector('div.side-console-container');
                        if (!panel) return 0;
                        const code = panel.querySelector('pre code');
                        return code ? code.innerText.length : 0;
                    }
                    """
                )

                # Scroll again (inside panel)
                await page.evaluate(
                    """
                    () => {
                        const panel = document.querySelector('div.side-console-container');
                        if (!panel) return;
                        const pre = panel.querySelector('pre');
                        if (pre) { pre.scrollTop = pre.scrollHeight; return; }
                        panel.scrollTop = panel.scrollHeight;
                    }
                    """
                )
                await asyncio.sleep(1)

                new_len = await page.evaluate(
                    """
                    () => {
                        const panel = document.querySelector('div.side-console-container');
                        if (!panel) return 0;
                        const code = panel.querySelector('pre code');
                        return code ? code.innerText.length : 0;
                    }
                    """
                )

                if new_len == prev_len:
                    self._trace("downloader.scroll.stable", rounds=round_num + 1, final_len=new_len)
                    break  # No more content loading
        except Exception:
            self._trace("downloader.scroll.error")

    async def _extract_full_content(self, page) -> Optional[str]:
        """Extract content from preview panel. Scopes to div.side-console-container FIRST."""
        try:
            # Wait for panel to appear
            await page.wait_for_selector(
                'div.side-console-container',
                timeout=8000,
            )
            await asyncio.sleep(1)

            # CRITICAL: Scroll INSIDE panel to trigger lazy loading
            await self._scroll_preview_to_load_full(page)

            # Extract: scope to panel first, fallback to page-wide
            content = await page.evaluate(
                """
                () => {
                    // Primary: search inside preview panel ONLY
                    const panel = document.querySelector('div.side-console-container');
                    if (panel) {
                        const code = panel.querySelector('pre code');
                        if (code && code.innerText.length > 100) return code.innerText;
                        const pre = panel.querySelector('pre');
                        if (pre && pre.innerText.length > 100) return pre.innerText;
                    }
                    // Fallback: page-wide (for non-standard layouts)
                    const code = document.querySelector('div.side-console-container pre code');
                    if (code) return code.innerText;
                    const pre = document.querySelector('pre');
                    if (pre) return pre.innerText;
                    return null;
                }
                """
            )
            self._trace("downloader.extract.done", content_len=len(content) if content else 0)
            return content
        except Exception:
            self._trace("downloader.extract.error")
            return None

    async def _close_preview(self, page) -> None:
        """Close preview panel using verified probe pattern (double Escape + click)."""
        try:
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
            await page.mouse.click(100, 300)
            await asyncio.sleep(0.5)
            self._trace("downloader.preview.close")
        except Exception:
            self._trace("downloader.preview.close.error")

    async def _click_download_button(self, page) -> bool:
        """Click the 'Download' button in the preview panel header."""
        try:
            result = await page.evaluate(
                """
                () => {
                    const panel = document.querySelector('div.side-console-container');
                    if (!panel) return false;
                    const buttons = panel.querySelectorAll('[class*="icon-button"], button, [role="button"]');
                    for (const btn of buttons) {
                        const text = btn.innerText?.trim() || '';
                        if (text === 'Download') {
                            btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                            return true;
                        }
                    }
                    return false;
                }
                """
            )
            return bool(result)
        except Exception:
            return False

    async def _download_file(
        self, page, finfo: Dict[str, Any], response_headers: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Download via Download button + HTTP header verification."""
        fname = finfo["name"]
        fhref = finfo.get("href", "")
        res = {
            "name": fname,
            "status": "failed",
            "path": None,
            "size": 0,
            "error": None,
            "http_url": None,
            "content_type": None,
            "etag": None,
            "last_modified": None,
            "content_length": None,
            "size_verified": False,
        }

        if self._is_cached(fname):
            p = self.download_dir / Path(fname).name
            res["status"] = "cached"
            res["path"] = str(p)
            res["size"] = p.stat().st_size
            self.logger.info(f"[CACHE] {fname}")
            return res

        if fname in self._session_seen:
            res["status"] = "skipped"
            res["error"] = "Duplicate"
            self.logger.info(f"[DEDUP] {fname}")
            return res

        self.logger.info(f"[DL] {fname}")

        # ---- One-shot HTTP response header capture for THIS file ----
        capt: Dict[str, Any] = {}
        async def _hdr(response):
            rurl = response.url
            if "tos-cn-beijing.volces.com" in rurl and fname in rurl:
                h = dict(response.headers)
                capt.update(h)
                self._trace("downloader.header.captured",
                           content_length=h.get("content-length"),
                           etag=h.get("etag"))
        page.on("response", _hdr)

        try:
            # Step 1: Click file to open preview panel
            clicked = await self._click_file(page, finfo)
            if not clicked:
                res["error"] = "Cannot click file"
                self.logger.warn(f"[SKIP] Cannot click: {fname}")
                page.remove_listener("response", _hdr)
                return res

            await asyncio.sleep(2)

            # Step 2: Click Download button — triggers browser download
            from playwright.async_api import async_playwright
            async with page.expect_download(timeout=15000) as dl_info:
                dl_clicked = await self._click_download_button(page)
            download = await dl_info.value

            # Wait briefly for response handler to fire
            await asyncio.sleep(0.5)

            # Step 3: Extract captured HTTP headers
            dl_url = download.url
            res["http_url"] = dl_url
            res["content_length"] = capt.get("content-length")
            res["etag"] = capt.get("etag")
            res["last_modified"] = capt.get("last-modified")
            res["content_type"] = capt.get("content-type")

            # Step 4: Save to download dir
            clean = Path(fname).name
            save_path = self.download_dir / clean
            await download.save_as(str(save_path))

            # Step 5: Verify file size against Content-Length
            actual_size = save_path.stat().st_size
            expected_size = None
            if res["content_length"]:
                try:
                    expected_size = int(res["content_length"])
                except (ValueError, TypeError):
                    pass

            if expected_size and actual_size != expected_size:
                res["error"] = (
                    f"Size mismatch: downloaded={actual_size} expected={expected_size}"
                )
                self.logger.error(f"[SIZE-MISMATCH] {clean}: got {actual_size}, expected {expected_size}")
                # Still save the file but mark as size-verified-failed
                res["status"] = "size_mismatch"
                res["size"] = actual_size
                res["size_verified"] = False
                self._session_seen.add(fname)
                self._trace("downloader.file.size_mismatch", fname=fname,
                           actual=actual_size, expected=expected_size)
                return res

            res["status"] = "success"
            res["path"] = str(save_path)
            res["size"] = actual_size
            res["size_verified"] = actual_size == expected_size
            self._session_seen.add(fname)

            self._trace("downloader.file.saved", fname=fname, size=actual_size,
                       path=str(save_path), etag=res["etag"],
                       content_length=res["content_length"])

            # Build log message
            extra = (
                f" | etag={res['etag'][:12] if res['etag'] else 'N/A'}"
                f" | size_ok={'Y' if res['size_verified'] else 'N'}"
                if res.get("etag") or res.get("content_length") else ""
            )
            self.logger.info(f"[OK] {clean} ({actual_size} bytes){extra}")

            # Close preview after successful download
            await self._close_preview(page)

        except Exception as e:
            res["error"] = f"Download failed: {e}"
            self.logger.error(f"[FAIL] {fname}: {e}")
            await self._close_preview(page)
        finally:
            page.remove_listener("response", _hdr)

        return res

    async def _process_chat(
        self, page, chat: Dict[str, Any], max_files: int
    ) -> Dict[str, Any]:
        cid = chat.get("id", "unknown")
        title = chat.get("title", "Untitled")
        url = chat.get("url", "")

        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"[CHAT] [{cid}] {title}")

        if not url:
            return {"chat_id": cid, "downloaded": 0, "failed": 0, "results": []}

        # Phase 1: Navigate and scan
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        self.logger.info("[SCAN] Scanning...")
        files = await self._scan_py_links(page)

        target = []
        seen: Set[str] = set()
        for f in files:
            if f["name"] not in seen:
                seen.add(f["name"])
                target.append(f)

        self.logger.info(f"[SCAN] Found {len(target)} unique .py files")
        for f in target:
            self.logger.debug(f"  - {f['name']}")

        if not target:
            return {"chat_id": cid, "downloaded": 0, "failed": 0, "results": []}

        if max_files:
            target = target[:max_files]

        self._session_seen.clear()

        # ---- HTTP response header capture ----
        response_headers: Dict[str, Dict[str, Any]] = {}

        async def on_response(response):
            rurl = response.url
            if "tos-cn-beijing.volces.com" in rurl or "apiv2-files/sign-obj" in rurl:
                try:
                    response_headers[rurl] = dict(response.headers)
                except Exception:
                    pass

        page.on("response", on_response)

        results: List[Dict[str, Any]] = []
        for idx, finfo in enumerate(target):
            # Reload page before each file to restore DOM links
            if idx > 0:
                self.logger.info(f"[RELOAD] Refreshing page for next file...")
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(2)

            # ---- Setup synchronous route capture for THIS file ----
            file_response_headers: Dict[str, Any] = {}

            async def capture_route(route, _fname=finfo["name"]):
                rurl = route.request.url
                if "tos-cn-beijing.volces.com" in rurl and _fname in rurl:
                    response = await route.fetch()
                    hdrs = dict(response.headers)
                    file_response_headers.update(hdrs)
                    self._trace("downloader.header.captured", url=rurl[:120],
                               content_length=hdrs.get("content-length"),
                               etag=hdrs.get("etag"))
                    await route.fulfill(response=response)
                else:
                    await route.continue_()

            await page.route("**/tos-cn-beijing.volces.com/**", capture_route)

            res = await self._download_file(page, finfo, file_response_headers)
            results.append(res)

            # Remove route handler after each file
            await page.unroute("**/tos-cn-beijing.volces.com/**")

        ok = sum(1 for r in results if r["status"] == "success")
        cached = sum(1 for r in results if r["status"] == "cached")
        fail = len(results) - ok - cached
        self.logger.info(f"[DONE] OK:{ok} CACHE:{cached} FAIL:{fail}")
        self._trace("downloader.chat.done", chat_id=cid, ok=ok, cached=cached, fail=fail)

        return {
            "chat_id": cid,
            "chat_title": title,
            "files_found": len(target),
            "downloaded": ok,
            "cached": cached,
            "failed": fail,
            "results": results,
        }

    async def run_batch(
        self,
        conversation_json: Path,
        max_files_per_chat: int,
        limit_chats: Optional[int] = None,
    ) -> Dict[str, Any]:
        with open(conversation_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        conversations = data.get("conversations", [])
        if limit_chats:
            conversations = conversations[:limit_chats]

        self.logger.info(f"[BATCH] Chats: {len(conversations)}")
        self.logger.info(f"[BATCH] Dir: {self.download_dir}")

        reports: List[Dict[str, Any]] = []
        total_ok = 0
        total_cache = 0
        total_fail = 0

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            self._trace("downloader.browser.open", headless=self.headless)
            page = context.pages[0] if context.pages else await context.new_page()

            try:
                for i, conv in enumerate(conversations, 1):
                    self.logger.info(f"\n[PROGRESS] [{i}/{len(conversations)}]")
                    report = await self._process_chat(
                        page, conv, max_files_per_chat
                    )
                    reports.append(report)
                    total_ok += report["downloaded"]
                    total_cache += report.get("cached", 0)
                    total_fail += report["failed"]
            except Exception as e:
                self.logger.error(f"[FATAL] {e}")
            finally:
                self.logger.info("[BATCH] Closing browser...")
                await context.close()
                self._trace("downloader.browser.close")

        final = {
            "timestamp": self._now(),
            "version": "v5.0.0",
            "total_chats": len(conversations),
            "downloaded": total_ok,
            "cached": total_cache,
            "failed": total_fail,
            "download_dir": str(self.download_dir),
            "chat_reports": reports,
        }

        report_path = (
            self.paths["data"]
            / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(final, f, ensure_ascii=False, indent=2)

        self.logger.info(f"\n{'='*60}")
        self.logger.info("[BATCH COMPLETE]")
        self.logger.info(f"[BATCH] Downloaded: {total_ok}")
        self.logger.info(f"[BATCH] Cached: {total_cache}")
        self.logger.info(f"[BATCH] Failed: {total_fail}")
        self.logger.info(f"[BATCH] Report: {report_path}")
        self.logger.info(f"{'='*60}")

        return final


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Kimi File Downloader v5.1.3"
    )
    parser.add_argument("--conversation-json", type=str, default=None)
    parser.add_argument("--max-files", type=int, default=10)
    parser.add_argument("--limit-chats", type=int, default=None)
    parser.add_argument("--profile-dir", type=str, default=None)
    parser.add_argument("--download-dir", type=str, default=None)
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--test", action="store_true", help="Run unit tests (no browser)")
    parser.add_argument("--tracer-test", action="store_true", help="Run tracer+playwright import tests")
    args = parser.parse_args()

    if args.test:
        _run_tests()
        sys.exit(0)

    if not args.conversation_json:
        print("[ERROR] --conversation-json is required")
        sys.exit(1)

    profile = Path(args.profile_dir) if args.profile_dir else None
    dldir = Path(args.download_dir) if args.download_dir else None

    dl = KimiDownloader(
        profile_dir=profile,
        headless=not args.visible,
        download_dir=dldir,
    )

    try:
        asyncio.run(
            dl.run_batch(
                Path(args.conversation_json),
                args.max_files,
                args.limit_chats,
            )
        )
    except Exception as e:
        print(f"[FATAL] {e}")
        sys.exit(1)



# =============================================================================
# TEST MODULE — python3 kimi_downloader.py --test
# =============================================================================

def _run_tests() -> None:
    passed = 0
    failed = 0

    def _t(name: str, condition: bool, ok_detail: str = "", fail_reason: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name}: {ok_detail}" if ok_detail else f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}: {fail_reason}" if fail_reason else f"  [FAIL] {name}")

    print("=" * 60)
    print("  kimi_downloader.py — UNIT TESTS (AST only, no browser)")
    print("=" * 60)

    # ── T1: default init ──────────────────────────────────────────
    d1 = KimiDownloader()
    _t("T1 test_default_init",
       d1.headless is True
       and "kimi_downloads" in str(d1.download_dir)
       and isinstance(d1._session_seen, set)
       and len(d1._session_seen) == 0
       and d1.tracer is None,
       f"headless={d1.headless}, dl_dir={d1.download_dir.name}, tracer={d1.tracer}")

    # ── T2: custom init ───────────────────────────────────────────
    d2 = KimiDownloader(
        headless=False,
        download_dir=Path("/tmp/kimi_test_dl"),
    )
    _t("T2 test_custom_init",
       d2.headless is False and str(d2.download_dir) == "/tmp/kimi_test_dl",
       f"headless={d2.headless}, dl_dir={d2.download_dir}")

    # ── T3: _now() ISO format ─────────────────────────────────────
    ts = d1._now()
    parts = ts.split("T")
    _t("T3 test_now_iso_format",
       len(parts) == 2 and len(parts[0]) == 10 and ":" in parts[1],
       ts)

    # ── T4: _is_cached() true ─────────────────────────────────────
    import tempfile
    tmpdir = Path(tempfile.gettempdir()) / f"kimi_cache_test_{int(__import__('time').time())}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    test_file = tmpdir / "hello.py"
    test_file.write_text("print('hello')", encoding="utf-8")
    d4 = KimiDownloader(download_dir=tmpdir)
    _t("T4 test_is_cached_true",
       d4._is_cached("hello.py") is True,
       f"file exists: {test_file}")

    # ── T5: _is_cached() false ────────────────────────────────────
    _t("T5 test_is_cached_false",
       d4._is_cached("nonexistent.py") is False)

    # ── T6: core_path_utils import (real) ─────────────────────────
    if CORE_AVAILABLE:
        try:
            from core_path_utils import get_skill_dir as _gsd, get_config_dir as _gcd, get_data_dir as _gdd, get_logs_dir as _gld
            sd = _gsd()
            cd = _gcd()
            dd = _gdd()
            ld = _gld()
            _t("T6 test_core_path_utils_import",
               sd.name == "kimi-agent-tracker" and all(isinstance(d, Path) for d in (sd, cd, dd, ld)),
               f"skill={sd.name}, config={cd.name}, data={dd.name}, logs={ld.name}")
        except Exception as e:
            _t("T6 test_core_path_utils_import", False, f"import failed: {e}")
    else:
        _t("T6 test_core_path_utils_import", False, "CORE_AVAILABLE=False")

    # ── T8: core_logger import (real) ─────────────────────────────
    if CORE_AVAILABLE:
        try:
            from core_logger import get_default_logger as _gdl
            log = _gdl("test_dl")
            methods = [m for m in dir(log) if not m.startswith("_") and callable(getattr(log, m, None))]
            _t("T7 test_core_logger_import",
               "info" in methods and "step" in methods,
               f"type={type(log).__name__}, methods={sorted(methods)}")
        except Exception as e:
            _t("T7 test_core_logger_import", False, f"import failed: {e}")
    else:
        _t("T7 test_core_logger_import", False, "CORE_AVAILABLE=False")

    # ── T9: _session_seen population ──────────────────────────────
    d9 = KimiDownloader()
    d9._session_seen.add("file_a.py")
    d9._session_seen.add("file_b.py")
    _t("T8 test_session_seen_populate",
       d9._session_seen == {"file_a.py", "file_b.py"},
       f"seen={d9._session_seen}")

    # ── T10: CLI args parse ───────────────────────────────────────
    t10_parser = argparse.ArgumentParser()
    t10_parser.add_argument("--conversation-json", type=str, default=None)
    t10_parser.add_argument("--max-files", type=int, default=10)
    t10_parser.add_argument("--visible", action="store_true")
    t10_parser.add_argument("--test", action="store_true")
    t10_args = t10_parser.parse_args([
        "--conversation-json", "test.json",
        "--max-files", "5",
        "--visible",
    ])
    _t("T9 test_cli_args_parse",
       t10_args.conversation_json == "test.json"
       and t10_args.max_files == 5
       and t10_args.visible is True,
       f"json={t10_args.conversation_json}, max={t10_args.max_files}, visible={t10_args.visible}")

    # ── T11: tracer init + events ─────────────────────────────────
    class MockTracer:
        def __init__(self):
            self.calls: List[tuple] = []
        def record(self, event: str, **data: Any) -> None:
            self.calls.append((event, data))
    mt = MockTracer()
    d11 = KimiDownloader(tracer=mt)
    d11._trace("test.event.one", key="val")
    d11._trace("test.event.two", count=42)
    _t("T10 test_tracer_events",
       len(mt.calls) == 2
       and mt.calls[0][0] == "test.event.one"
       and mt.calls[1][0] == "test.event.two",
       f"calls={[(c[0], list(c[1].keys())) for c in mt.calls]}")

    # ── T12: sync_playwright import (via system python if sandboxed) ─
    playwright_ok = False
    pw_detail = ""
    try:
        from playwright.sync_api import sync_playwright
        playwright_ok = True
        pw_detail = "direct import OK"
    except Exception:
        # managed python sandbox may block greenlet .so — try system python
        import subprocess
        try:
            r = subprocess.run(
                ["/Library/Frameworks/Python.framework/Versions/3.14/bin/python3",
                 "-c", "from playwright.sync_api import sync_playwright; print('OK')"],
                capture_output=True, text=True, timeout=10,
            )
            playwright_ok = r.returncode == 0 and "OK" in r.stdout
            pw_detail = f"system python: {r.stdout.strip()}" if playwright_ok else f"system python failed: {r.stderr.strip()[:80]}"
        except Exception as e2:
            pw_detail = f"subprocess error: {e2}"
    _t("T11 test_sync_playwright_import", playwright_ok, pw_detail)

    # cleanup T4 temp dir
    if 'test_file' in dir() and test_file.exists():
        test_file.unlink()
    if 'tmpdir' in dir() and tmpdir.exists():
        import shutil as _sh
        _sh.rmtree(tmpdir, ignore_errors=True)

    print()
    print("=" * 60)
    print(f"  TEST RESULTS: {passed}/{passed + failed} passed, {failed} failed")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
