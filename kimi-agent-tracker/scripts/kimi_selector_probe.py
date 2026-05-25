"""
---
title: Kimi Selector Probe v1.0.3
name: kimi-agent-tracker
description: Auto-detect working selectors for .py/.md/.json/.zip file extraction from Kimi chat pages.
version: 1.0.3
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T23:00:00+08:00
auth_config:
  provider: none
  auth_method: none
  token_env_var: none
  env_file_path: none
file_mapping:
  local_path: "{baseDir}/scripts/kimi_selector_probe.py"
  github_path: "kimi-agent-tracker/scripts/kimi_selector_probe.py"
---
"""

import asyncio
import json
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("[FATAL] playwright not installed. Run: python3 -m pip install playwright")
    print("[FATAL] Then: python3 -m playwright install chromium")
    sys.exit(1)

# Configuration
PROFILE_DIR = Path.home() / ".kimi_auth" / "browser_profile_chromium"
REPORT_PATH = Path.home() / "Downloads" / "selector_test_report.json"

# Selectors (ordered by specificity)
FILE_CARD_SELECTOR = 'div[class*="file-card-container"]'
FILE_NAME_SELECTOR = 'div[class*="file-card-info-name"]'
FILE_EXT_SELECTOR = 'div[class*="file-card-info-ext"]'
PREVIEW_PANEL_SELECTOR = 'div[class*="preview-panel"], div[class*="file-preview"], div[class*="preview-content"]'
MARKDOWN_CONTENT_SELECTOR = 'div[class*="markdown"], article[class*="markdown"]'
MONACO_EDITOR_SELECTOR = 'div[class*="monaco-editor"]'
DOWNLOAD_ICON_SELECTOR = 'button[class*="download"], div[class*="download"], svg[class*="download"]'
COPY_ICON_SELECTOR = 'button[class*="copy"], div[class*="copy"], svg[class*="copy"]'


def log(msg: str) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    print(f"[{ts}] {msg}", flush=True)


def now_ms() -> int:
    return int(time.time() * 1000)


async def safe_click(page, selector: str, timeout: int = 3000) -> bool:
    """Click with force=True to bypass pointer-events interception."""
    try:
        el = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        if el:
            await el.click(force=True)
            return True
    except Exception:
        pass
    return False


async def get_element_text(page, selector: str, timeout: int = 3000) -> Optional[str]:
    try:
        el = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        if el:
            return await el.text_content()
    except Exception:
        pass
    return None


async def get_element_inner_text(page, selector: str, timeout: int = 3000) -> Optional[str]:
    try:
        el = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        if el:
            return await el.inner_text()
    except Exception:
        pass
    return None


async def get_element_inner_html(page, selector: str, timeout: int = 3000) -> Optional[str]:
    try:
        el = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        if el:
            return await el.inner_html()
    except Exception:
        pass
    return None


async def test_strategy_a1_monaco_editor_api(page) -> Dict[str, Any]:
    """Inject JS to call monaco.editor.getEditors()[0].getValue()"""
    result = {"strategy": "A1_monaco_editor_api", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()
    try:
        # Wait for monaco editor to appear in preview panel
        await page.wait_for_selector(MONACO_EDITOR_SELECTOR, timeout=5000)
        # Inject extraction script
        code = """
            (() => {
                try {
                    const editors = window.monaco?.editor?.getEditors();
                    if (editors && editors.length > 0) {
                        return editors[0].getValue();
                    }
                    return "__NO_MONACO_EDITORS__";
                } catch (e) {
                    return "__ERROR__: " + e.message;
                }
            })()
        """
        text = await page.evaluate(code)
        result["duration_ms"] = now_ms() - start
        if text and not text.startswith("__"):
            result["passed"] = True
            result["length"] = len(text)
            result["sample"] = text[:200]
        else:
            result["error"] = text if text else "monaco editor not found"
    except Exception as e:
        result["duration_ms"] = now_ms() - start
        result["error"] = str(e)
    return result


async def test_strategy_a2_monaco_model_api(page) -> Dict[str, Any]:
    """Inject JS to call monaco.editor.getModels()[0].getValue()"""
    result = {"strategy": "A2_monaco_model_api", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()
    try:
        await page.wait_for_selector(MONACO_EDITOR_SELECTOR, timeout=5000)
        code = """
            (() => {
                try {
                    const models = window.monaco?.editor?.getModels();
                    if (models && models.length > 0) {
                        return models[0].getValue();
                    }
                    return "__NO_MONACO_MODELS__";
                } catch (e) {
                    return "__ERROR__: " + e.message;
                }
            })()
        """
        text = await page.evaluate(code)
        result["duration_ms"] = now_ms() - start
        if text and not text.startswith("__"):
            result["passed"] = True
            result["length"] = len(text)
            result["sample"] = text[:200]
        else:
            result["error"] = text if text else "monaco models not found"
    except Exception as e:
        result["duration_ms"] = now_ms() - start
        result["error"] = str(e)
    return result


async def test_strategy_a3_copy_button_clipboard(page) -> Dict[str, Any]:
    """Click copy button and read clipboard via pyperclip."""
    result = {"strategy": "A3_copy_button_clipboard", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()
    try:
        clicked = await safe_click(page, COPY_ICON_SELECTOR, timeout=3000)
        if not clicked:
            result["error"] = "copy button not found"
            result["duration_ms"] = now_ms() - start
            return result
        await asyncio.sleep(1.0)
        try:
            import pyperclip
            text = pyperclip.paste()
            result["duration_ms"] = now_ms() - start
            if text and len(text) > 50:
                result["passed"] = True
                result["length"] = len(text)
                result["sample"] = text[:200]
            else:
                result["error"] = "clipboard empty or too short"
        except ImportError:
            result["error"] = "pyperclip not installed"
            result["duration_ms"] = now_ms() - start
    except Exception as e:
        result["duration_ms"] = now_ms() - start
        result["error"] = str(e)
    return result


async def test_strategy_a4_download_button_expect(page) -> Dict[str, Any]:
    """Click download icon and capture via expect_download."""
    result = {"strategy": "A4_download_button_expect", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()
    try:
        # Try to find and click download button in preview panel
        async with page.expect_download(timeout=8000) as dl:
            clicked = await safe_click(page, DOWNLOAD_ICON_SELECTOR, timeout=3000)
            if not clicked:
                result["error"] = "download button not found"
                result["duration_ms"] = now_ms() - start
                return result
        download = await dl.value
        path = await download.path()
        if path and Path(path).exists():
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
            result["passed"] = True
            result["length"] = len(text)
            result["sample"] = text[:200]
            result["file_path"] = str(path)
        else:
            result["error"] = "download path not found"
        result["duration_ms"] = now_ms() - start
    except PlaywrightTimeout:
        result["duration_ms"] = now_ms() - start
        result["error"] = "expect_download timeout (sandbox link or no download triggered)"
    except Exception as e:
        result["duration_ms"] = now_ms() - start
        result["error"] = str(e)
    return result


async def test_strategy_b1_preview_dom_extraction(page) -> Dict[str, Any]:
    """Extract text from preview panel markdown/monaco/pre elements."""
    result = {"strategy": "B1_preview_dom_extraction", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()
    try:
        # Wait for preview panel
        await page.wait_for_selector(PREVIEW_PANEL_SELECTOR, timeout=5000)
        # Try multiple content selectors in order of preference
        selectors = [
            MARKDOWN_CONTENT_SELECTOR,
            'pre',
            'code',
            'div[class*="content"]',
            MONACO_EDITOR_SELECTOR,
        ]
        for sel in selectors:
            text = await get_element_inner_text(page, sel, timeout=2000)
            if text and len(text) > 100:
                result["passed"] = True
                result["length"] = len(text)
                result["selector_used"] = sel
                result["sample"] = text[:200]
                break
        if not result["passed"]:
            result["error"] = "no content found in preview panel"
        result["duration_ms"] = now_ms() - start
    except Exception as e:
        result["duration_ms"] = now_ms() - start
        result["error"] = str(e)
    return result


async def test_strategy_b2_download_button_global_listener(page) -> Dict[str, Any]:
    """Use page.on('download') global listener + click download button."""
    result = {"strategy": "B2_download_button_global_listener", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()
    download_info = {"path": None}

    def handle_download(download):
        download_info["path"] = asyncio.create_task(download.path())

    page.on("download", handle_download)
    try:
        clicked = await safe_click(page, DOWNLOAD_ICON_SELECTOR, timeout=3000)
        if not clicked:
            result["error"] = "download button not found"
            result["duration_ms"] = now_ms() - start
            return result
        await asyncio.sleep(3.0)
        if download_info["path"]:
            path = await download_info["path"]
            if path and Path(path).exists():
                text = Path(path).read_text(encoding="utf-8", errors="ignore")
                result["passed"] = True
                result["length"] = len(text)
                result["sample"] = text[:200]
                result["file_path"] = str(path)
            else:
                result["error"] = "download captured but path invalid"
        else:
            result["error"] = "no download event captured"
        result["duration_ms"] = now_ms() - start
    except Exception as e:
        result["duration_ms"] = now_ms() - start
        result["error"] = str(e)
    finally:
        page.remove_listener("download", handle_download)
    return result


async def test_file(page, file_info: Dict[str, Any], visible: bool) -> Dict[str, Any]:
    """Test all strategies for a single file."""
    filename = file_info.get("filename", "unknown")
    ext = file_info.get("ext", "")
    log(f"[TEST] File: {filename} (.{ext})")

    # Click the file card to open preview
    card_selector = file_info.get("selector")
    if not card_selector:
        log(f"[SKIP] No selector for {filename}")
        return {"filename": filename, "ext": ext, "strategies": [], "error": "no selector"}

    click_ok = await safe_click(page, card_selector, timeout=5000)
    if not click_ok:
        log(f"[WARN] Failed to click file card: {filename}")
    else:
        log(f"[OK] Clicked file card: {filename}")
        await asyncio.sleep(2.0)  # Wait for preview panel to open

    strategies = []

    # For .py files: test Monaco API strategies first
    if ext == "py":
        strategies.append(await test_strategy_a1_monaco_editor_api(page))
        strategies.append(await test_strategy_a2_monaco_model_api(page))
        strategies.append(await test_strategy_a3_copy_button_clipboard(page))
        strategies.append(await test_strategy_a4_download_button_expect(page))
        strategies.append(await test_strategy_b1_preview_dom_extraction(page))
        strategies.append(await test_strategy_b2_download_button_global_listener(page))
    # For .md files: test DOM extraction and download button
    elif ext == "md":
        strategies.append(await test_strategy_b1_preview_dom_extraction(page))
        strategies.append(await test_strategy_b2_download_button_global_listener(page))
        strategies.append(await test_strategy_a4_download_button_expect(page))
        strategies.append(await test_strategy_a3_copy_button_clipboard(page))
    # For .json / .zip / others: test download strategies
    else:
        strategies.append(await test_strategy_a4_download_button_expect(page))
        strategies.append(await test_strategy_b2_download_button_global_listener(page))
        strategies.append(await test_strategy_b1_preview_dom_extraction(page))

    # Close preview if possible (look for close button or press Escape)
    try:
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
    except Exception:
        pass

    return {
        "filename": filename,
        "ext": ext,
        "strategies": strategies,
    }


async def scan_files(page, max_per_type: int = 2) -> List[Dict[str, Any]]:
    """Scan page for file cards, group by extension, return up to max_per_type per extension."""
    log("[SCAN] Scanning for file cards...")
    file_cards = await page.query_selector_all(FILE_CARD_SELECTOR)
    log(f"[SCAN] Found {len(file_cards)} file card elements")

    all_files = []
    for idx, card in enumerate(file_cards):
        try:
            # Extract filename from the card
            name_el = await card.query_selector(FILE_NAME_SELECTOR)
            ext_el = await card.query_selector(FILE_EXT_SELECTOR)
            name_text = await name_el.text_content() if name_el else None
            ext_text = await ext_el.text_content() if ext_el else None

            if not name_text:
                continue

            # Clean up: some sites show extension separately
            filename = name_text.strip()
            if ext_text:
                ext = ext_text.strip().lower().replace(".", "")
            else:
                ext = Path(filename).suffix.lstrip(".").lower()

            # Skip if looks like a label/tag rather than filename (heuristic)
            if len(filename) <= 4 and filename.upper() in ("MD", "PY", "JSON", "ZIP", "ENV", "TXT", "CSV"):
                log(f"[SKIP] Element {idx} looks like extension tag: '{filename}', skipping")
                continue

            # Build a unique selector for this card
            # Use nth-of-type as fallback if no stable class
            selector = f'{FILE_CARD_SELECTOR}:nth-of-type({idx + 1})'

            all_files.append({
                "filename": filename,
                "ext": ext,
                "selector": selector,
                "index": idx,
            })
        except Exception as e:
            log(f"[WARN] Error processing card {idx}: {e}")

    log(f"[SCAN] Filtered to {len(all_files)} valid files")

    # Group by extension and limit per type
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for f in all_files:
        ext = f["ext"]
        if ext not in grouped:
            grouped[ext] = []
        grouped[ext].append(f)

    selected = []
    for ext in ("py", "md", "json", "zip"):
        if ext in grouped:
            count = min(max_per_type, len(grouped[ext]))
            selected.extend(grouped[ext][:count])
            log(f"[SELECT] {ext}: selected {count}/{len(grouped[ext])}")

    # Add any remaining types if we have room
    for ext, items in grouped.items():
        if ext not in ("py", "md", "json", "zip"):
            count = min(max_per_type, len(items))
            selected.extend(items[:count])

    return selected


async def run_probe(url: str, visible: bool = False, max_per_type: int = 2) -> Dict[str, Any]:
    report = {
        "probe_version": "1.0.3",
        "url": url,
        "mode": "visible" if visible else "headless",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "files_tested": [],
        "summary": {},
    }

    async with async_playwright() as p:
        log("[MAIN] Browser launching...")
        try:
            if PROFILE_DIR.exists():
                log(f"[MAIN] Using persistent profile: {PROFILE_DIR}")
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    headless=not visible,
                    args=["--disable-blink-features=AutomationControlled"] if visible else [],
                    viewport={"width": 1280, "height": 900} if visible else None,
                )
                page = context.pages[0] if context.pages else await context.new_page()
            else:
                log("[MAIN] No persistent profile found, launching fresh browser")
                browser = await p.chromium.launch(
                    headless=not visible,
                    args=["--disable-blink-features=AutomationControlled"] if visible else [],
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 900} if visible else None,
                )
                page = await context.new_page()
        except Exception as e:
            log(f"[FATAL] Browser launch failed: {e}")
            report["error"] = f"Browser launch failed: {e}"
            return report

        log("[MAIN] Browser launched")

        try:
            log(f"[MAIN] Navigating to {url}")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            log("[MAIN] Page loaded")
            await asyncio.sleep(3.0)  # Extra wait for dynamic content
        except Exception as e:
            log(f"[FATAL] Navigation failed: {e}")
            report["error"] = f"Navigation failed: {e}"
            return report

        # Scan for files
        files = await scan_files(page, max_per_type=max_per_type)
        if not files:
            log("[WARN] No files found on page")
            report["error"] = "No files found"
            return report

        # Test each file
        for f in files:
            file_result = await test_file(page, f, visible=visible)
            report["files_tested"].append(file_result)

        # Summary
        total_strategies = 0
        passed_strategies = 0
        for f in report["files_tested"]:
            for s in f.get("strategies", []):
                total_strategies += 1
                if s.get("passed"):
                    passed_strategies += 1

        report["summary"] = {
            "files_tested": len(report["files_tested"]),
            "total_strategies_attempted": total_strategies,
            "strategies_passed": passed_strategies,
            "success_rate": round(passed_strategies / total_strategies, 2) if total_strategies > 0 else 0,
        }

        # Save report
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"[DONE] Report saved to: {REPORT_PATH}")

        await context.close()
        return report


def main():
    parser = argparse.ArgumentParser(description="Kimi Selector Probe v1.0.3")
    parser.add_argument("--url", required=True, help="Kimi chat URL to probe")
    parser.add_argument("--visible", action="store_true", help="Run in visible browser mode")
    parser.add_argument("--max-per-type", type=int, default=2, help="Max files to test per extension type")
    args = parser.parse_args()

    log(f"[MAIN] Starting probe for {args.url}")
    log(f"[MAIN] Mode: {'visible' if args.visible else 'headless'}, max_per_type: {args.max_per_type}")

    report = asyncio.run(run_probe(args.url, visible=args.visible, max_per_type=args.max_per_type))

    # Print summary
    print("\n" + "=" * 60)
    print("PROBE SUMMARY")
    print("=" * 60)
    print(f"Files tested: {report['summary'].get('files_tested', 0)}")
    print(f"Strategies passed: {report['summary'].get('strategies_passed', 0)}/{report['summary'].get('total_strategies_attempted', 0)}")
    print(f"Success rate: {report['summary'].get('success_rate', 0)}")
    print(f"Report: {REPORT_PATH}")
    print("=" * 60)

    # Print per-file results
    for f in report.get("files_tested", []):
        print(f"\nFile: {f['filename']}")
        for s in f.get("strategies", []):
            status = "PASS" if s.get("passed") else "FAIL"
            print(f"  [{status}] {s['strategy']}: len={s.get('length', 0)} duration={s.get('duration_ms', 0)}ms error={s.get('error', 'None')}")


if __name__ == "__main__":
    main()
