"""
---
title: Kimi Selector Probe v1.0.7
name: kimi-agent-tracker
description: Auto-detect working selectors for .py/.md/.json/.zip file extraction from Kimi chat pages.
version: 1.0.7
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T00:10:00+08:00
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
import re
from pathlib import Path
from datetime import datetime, timezone
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
SCREENSHOT_DIR = Path.home() / "Downloads" / "probe_screenshots"

# File card selectors
FILE_CARD_SELECTORS = [
    'div[class*="file-card-container"]',
    'div[class*="file-card"]',
    'div[data-v-][class*="file"]',
    'div[class*="file-item"]',
    'div[class*="attachment"]',
    'a[class*="file"]',
    'div[data-v-]',
]

# File extension pattern
FILE_PATTERN = re.compile(
    r'([A-Za-z0-9_.-]+[.](py|md|json|zip|env|txt|csv|yaml|yml|js|html|css|xml))',
    re.IGNORECASE
)


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    print(f"[{ts}] {msg}", flush=True)


def now_ms() -> int:
    return int(time.time() * 1000)


async def safe_click(page, selector: str, timeout: int = 3000, force: bool = True) -> bool:
    try:
        el = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        if el:
            if force:
                await el.click(force=True)
            else:
                await el.click()
            return True
    except Exception:
        pass
    return False


async def js_click(page, selector: str) -> bool:
    try:
        result = await page.evaluate(f"""
            (() => {{
                const el = document.querySelector('{selector}');
                if (el) {{
                    el.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true }}));
                    return true;
                }}
                return false;
            }})()
        """)
        return bool(result)
    except Exception:
        return False


async def double_click(page, selector: str, timeout: int = 3000) -> bool:
    try:
        el = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        if el:
            await el.dblclick(force=True)
            return True
    except Exception:
        pass
    return False


async def take_screenshot(page, name: str) -> Optional[str]:
    try:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOT_DIR / f"{name}.png"
        await page.screenshot(path=str(path), full_page=False)
        return str(path)
    except Exception as e:
        log(f"[WARN] Screenshot failed: {e}")
        return None


async def diagnose_page(page) -> Dict[str, Any]:
    """Use JavaScript to find all relevant elements on the page."""
    diagnosis = {
        "preview_panels": [],
        "monaco_editors": [],
        "download_buttons": [],
        "copy_buttons": [],
        "file_cards": [],
        "all_classes": [],
    }

    try:
        data = await page.evaluate("""
            (() => {
                const result = {
                    preview_panels: [],
                    monaco_editors: [],
                    download_buttons: [],
                    copy_buttons: [],
                    file_cards: [],
                    all_classes: [],
                };

                // Find preview-related elements
                document.querySelectorAll('*').forEach(el => {
                    const cls = el.className || '';
                    const tag = el.tagName.toLowerCase();
                    const id = el.id || '';

                    // Preview panels
                    if (cls.includes('preview') || cls.includes('drawer') || cls.includes('panel') || 
                        cls.includes('modal') || cls.includes('dialog') || cls.includes('overlay') ||
                        cls.includes('file-preview') || cls.includes('preview-panel')) {
                        result.preview_panels.push({
                            tag: tag,
                            id: id,
                            class: cls.substring(0, 200),
                            text: el.textContent?.substring(0, 100) || '',
                            rect: el.getBoundingClientRect ? {
                                width: el.getBoundingClientRect().width,
                                height: el.getBoundingClientRect().height,
                                top: el.getBoundingClientRect().top,
                                left: el.getBoundingClientRect().left,
                            } : null,
                        });
                    }

                    // Monaco editors
                    if (cls.includes('monaco') || id.includes('monaco') || 
                        el.getAttribute('data-editor') || window.monaco) {
                        result.monaco_editors.push({
                            tag: tag,
                            id: id,
                            class: cls.substring(0, 200),
                            has_window_monaco: !!window.monaco,
                        });
                    }

                    // Download buttons
                    if (cls.includes('download') || el.getAttribute('title')?.toLowerCase().includes('download') ||
                        el.getAttribute('aria-label')?.toLowerCase().includes('download') ||
                        el.innerHTML?.includes('download')) {
                        result.download_buttons.push({
                            tag: tag,
                            id: id,
                            class: cls.substring(0, 200),
                            title: el.getAttribute('title') || '',
                            aria_label: el.getAttribute('aria-label') || '',
                            html: el.outerHTML?.substring(0, 300) || '',
                        });
                    }

                    // Copy buttons
                    if (cls.includes('copy') || el.getAttribute('title')?.toLowerCase().includes('copy') ||
                        el.getAttribute('aria-label')?.toLowerCase().includes('copy')) {
                        result.copy_buttons.push({
                            tag: tag,
                            id: id,
                            class: cls.substring(0, 200),
                            title: el.getAttribute('title') || '',
                            html: el.outerHTML?.substring(0, 300) || '',
                        });
                    }

                    // File cards
                    if (cls.includes('file-card') || cls.includes('file-item') || cls.includes('attachment')) {
                        result.file_cards.push({
                            tag: tag,
                            id: id,
                            class: cls.substring(0, 200),
                            text: el.textContent?.substring(0, 100) || '',
                        });
                    }

                    // Collect interesting classes
                    if (cls && cls.length > 0 && !cls.includes(' ')) {
                        const interesting = ['preview', 'monaco', 'download', 'copy', 'file', 'card', 
                            'panel', 'drawer', 'modal', 'dialog', 'content', 'editor'];
                        if (interesting.some(k => cls.toLowerCase().includes(k))) {
                            result.all_classes.push(cls);
                        }
                    }
                });

                return result;
            })()
        """)
        return data
    except Exception as e:
        log(f"[WARN] DOM diagnosis failed: {e}")
        return diagnosis


async def test_strategy_monaco_api(page, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    """Test Monaco Editor API injection."""
    result = {"strategy": "A_monaco_api", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()

    # Check if window.monaco exists
    has_monaco = await page.evaluate("() => !!window.monaco")
    if not has_monaco:
        result["error"] = "window.monaco not available"
        result["duration_ms"] = now_ms() - start
        return result

    try:
        code = """
            (() => {
                try {
                    const editors = window.monaco?.editor?.getEditors();
                    if (editors && editors.length > 0) {
                        return editors[0].getValue();
                    }
                    const models = window.monaco?.editor?.getModels();
                    if (models && models.length > 0) {
                        return models[0].getValue();
                    }
                    return "__NO_MONACO__";
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
            result["error"] = text if text else "monaco not accessible"
    except Exception as e:
        result["duration_ms"] = now_ms() - start
        result["error"] = str(e)
    return result


async def test_strategy_preview_dom(page, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    """Extract text from preview panel using diagnosed selectors."""
    result = {"strategy": "B_preview_dom", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()

    # Try selectors from diagnosis
    preview_selectors = []
    for p in diagnosis.get("preview_panels", []):
        cls = p.get("class", "")
        if cls:
            # Build selector from class
            classes = cls.split()
            if classes:
                preview_selectors.append(f'{p["tag"]}.{classes[0]}')

    # Also try generic selectors
    preview_selectors.extend([
        'div[class*="preview"]',
        'div[class*="drawer"]',
        'div[class*="panel"]',
        'aside[class*="preview"]',
        'div[role="dialog"]',
    ])

    for sel in preview_selectors:
        try:
            el = await page.wait_for_selector(sel, timeout=2000, state="visible")
            if el:
                # Try to get text from various content selectors within preview
                content_selectors = [
                    'pre',
                    'code',
                    'div[class*="content"]',
                    'div[class*="markdown"]',
                    'div[class*="monaco"]',
                ]
                for content_sel in content_selectors:
                    try:
                        content_el = await el.wait_for_selector(content_sel, timeout=1000)
                        if content_el:
                            text = await content_el.inner_text()
                            if text and len(text) > 100:
                                result["passed"] = True
                                result["length"] = len(text)
                                result["selector"] = sel
                                result["content_selector"] = content_sel
                                result["sample"] = text[:200]
                                result["duration_ms"] = now_ms() - start
                                return result
                    except Exception:
                        continue
        except Exception:
            continue

    result["error"] = "no content found in preview panel"
    result["duration_ms"] = now_ms() - start
    return result


async def test_strategy_download_button(page, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    """Click download button and capture via global listener."""
    result = {"strategy": "C_download_button", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()

    # Build selectors from diagnosis
    download_selectors = []
    for b in diagnosis.get("download_buttons", []):
        tag = b.get("tag", "")
        cls = b.get("class", "").split()[0] if b.get("class") else ""
        if tag and cls:
            download_selectors.append(f'{tag}.{cls}')

    download_selectors.extend([
        'button[class*="download"]',
        'div[class*="download"]',
        'svg[class*="download"]',
        '[title*="download" i]',
        '[aria-label*="download" i]',
    ])

    download_info = {"path": None}
    def handle_download(download):
        download_info["path"] = asyncio.create_task(download.path())

    page.on("download", handle_download)
    try:
        clicked = False
        for sel in download_selectors:
            try:
                if await safe_click(page, sel, timeout=2000):
                    clicked = True
                    result["used_selector"] = sel
                    break
            except Exception:
                continue

        if not clicked:
            result["error"] = "no download button found or clickable"
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


async def test_strategy_copy_button(page, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    """Click copy button and read clipboard."""
    result = {"strategy": "D_copy_button", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()

    copy_selectors = []
    for b in diagnosis.get("copy_buttons", []):
        tag = b.get("tag", "")
        cls = b.get("class", "").split()[0] if b.get("class") else ""
        if tag and cls:
            copy_selectors.append(f'{tag}.{cls}')

    copy_selectors.extend([
        'button[class*="copy"]',
        'div[class*="copy"]',
        'svg[class*="copy"]',
        '[title*="copy" i]',
        '[aria-label*="copy" i]',
    ])

    clicked = False
    for sel in copy_selectors:
        try:
            if await safe_click(page, sel, timeout=2000):
                clicked = True
                result["used_selector"] = sel
                break
        except Exception:
            continue

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
    return result


async def test_file(page, file_info: Dict[str, Any], visible: bool, file_index: int) -> Dict[str, Any]:
    filename = file_info.get("filename", "unknown")
    ext = file_info.get("ext", "")
    card_selector = file_info.get("selector", "")
    log(f"[TEST] File: {filename} (.{ext})")

    if not card_selector:
        return {"filename": filename, "ext": ext, "strategies": [], "error": "no selector"}

    # Screenshot before
    before_ss = await take_screenshot(page, f"{file_index:02d}_{filename}_before")

    # Try multiple click methods
    click_methods = [
        ("force_click", lambda: safe_click(page, card_selector, timeout=5000, force=True)),
        ("normal_click", lambda: safe_click(page, card_selector, timeout=5000, force=False)),
        ("js_click", lambda: js_click(page, card_selector)),
        ("double_click", lambda: double_click(page, card_selector, timeout=5000)),
        ("child_anchor", lambda: safe_click(page, f'{card_selector} a', timeout=3000, force=True)),
    ]

    click_ok = False
    used_method = None
    for method_name, method_fn in click_methods:
        try:
            ok = await method_fn()
            if ok:
                click_ok = True
                used_method = method_name
                log(f"[OK] Click succeeded: {method_name}")
                break
        except Exception as e:
            log(f"[WARN] Click {method_name} failed: {e}")

    if not click_ok:
        log(f"[WARN] All click methods failed for {filename}")

    # Wait for preview
    log("[TEST] Waiting 8s for preview...")
    await asyncio.sleep(8.0)

    # Screenshot after
    after_ss = await take_screenshot(page, f"{file_index:02d}_{filename}_after")

    # DOM DIAGNOSIS - Key step
    log("[TEST] Running DOM diagnosis...")
    diagnosis = await diagnose_page(page)
    log(f"[DIAG] Preview panels: {len(diagnosis.get('preview_panels', []))}")
    log(f"[DIAG] Monaco editors: {len(diagnosis.get('monaco_editors', []))}")
    log(f"[DIAG] Download buttons: {len(diagnosis.get('download_buttons', []))}")
    log(f"[DIAG] Copy buttons: {len(diagnosis.get('copy_buttons', []))}")

    # Run strategies based on diagnosis
    strategies = []

    if diagnosis.get("monaco_editors"):
        strategies.append(await test_strategy_monaco_api(page, diagnosis))

    if diagnosis.get("preview_panels"):
        strategies.append(await test_strategy_preview_dom(page, diagnosis))

    if diagnosis.get("download_buttons"):
        strategies.append(await test_strategy_download_button(page, diagnosis))

    if diagnosis.get("copy_buttons"):
        strategies.append(await test_strategy_copy_button(page, diagnosis))

    # If no elements diagnosed, try generic strategies anyway
    if not strategies:
        strategies.append(await test_strategy_monaco_api(page, diagnosis))
        strategies.append(await test_strategy_preview_dom(page, diagnosis))
        strategies.append(await test_strategy_download_button(page, diagnosis))
        strategies.append(await test_strategy_copy_button(page, diagnosis))

    # Close preview
    try:
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
    except Exception:
        pass

    return {
        "filename": filename,
        "ext": ext,
        "click_method_used": used_method,
        "screenshots": {"before": before_ss, "after": after_ss},
        "diagnosis": {
            "preview_panel_count": len(diagnosis.get("preview_panels", [])),
            "monaco_editor_count": len(diagnosis.get("monaco_editors", [])),
            "download_button_count": len(diagnosis.get("download_buttons", [])),
            "copy_button_count": len(diagnosis.get("copy_buttons", [])),
            "preview_panel_first_class": diagnosis.get("preview_panels", [{}])[0].get("class", "") if diagnosis.get("preview_panels") else "",
            "monaco_editor_first_class": diagnosis.get("monaco_editors", [{}])[0].get("class", "") if diagnosis.get("monaco_editors") else "",
            "download_button_first_class": diagnosis.get("download_buttons", [{}])[0].get("class", "") if diagnosis.get("download_buttons") else "",
        },
        "strategies": strategies,
    }


async def scan_files(page, max_per_type: int = 2) -> List[Dict[str, Any]]:
    log("[SCAN] Scanning for file cards...")

    all_cards = []
    used_selector = None

    for sel in FILE_CARD_SELECTORS:
        cards = await page.query_selector_all(sel)
        if cards:
            log(f"[SCAN] Selector '{sel}' matched {len(cards)} elements")
            all_cards = cards
            used_selector = sel
            break

    if not all_cards:
        log("[SCAN] No file cards found")
        return []

    log(f"[SCAN] Using selector: {used_selector}")

    all_files = []
    for idx, card in enumerate(all_cards):
        try:
            full_text = await card.text_content()
            if not full_text:
                continue

            full_text = full_text.strip()
            match = FILE_PATTERN.search(full_text)
            if match:
                filename = match.group(1)
                ext = match.group(2).lower()
                selector = f'{used_selector}:nth-of-type({idx + 1})'

                all_files.append({
                    "filename": filename,
                    "ext": ext,
                    "selector": selector,
                    "index": idx,
                    "card_text": full_text[:100],
                })
        except Exception as e:
            log(f"[WARN] Error processing card {idx}: {e}")

    log(f"[SCAN] Extracted {len(all_files)} valid files")

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
            log(f"[SELECT] {ext}: {count}/{len(grouped[ext])}")

    for ext, items in grouped.items():
        if ext not in ("py", "md", "json", "zip"):
            count = min(max_per_type, len(items))
            selected.extend(items[:count])

    return selected


async def run_probe(url: str, visible: bool = False, max_per_type: int = 2) -> Dict[str, Any]:
    report = {
        "probe_version": "1.0.7",
        "url": url,
        "mode": "visible" if visible else "headless",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "files_tested": [],
        "summary": {},
        "error": None,
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
                log("[MAIN] No persistent profile, launching fresh browser")
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
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            log("[MAIN] DOM loaded, waiting for dynamic content...")
            await asyncio.sleep(5.0)
        except Exception as e:
            log(f"[FATAL] Navigation failed: {e}")
            report["error"] = f"Navigation failed: {e}"
            return report

        files = await scan_files(page, max_per_type=max_per_type)
        if not files:
            log("[WARN] No files found")
            report["error"] = "No files found"
            return report

        for i, f in enumerate(files):
            file_result = await test_file(page, f, visible=visible, file_index=i)
            report["files_tested"].append(file_result)

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

        await context.close()
        return report


def save_and_print_report(report: Dict[str, Any]) -> None:
    try:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[REPORT] Saved to: {REPORT_PATH}")
    except Exception as e:
        print(f"\n[REPORT] Failed to save: {e}")

    print("\n" + "=" * 60)
    print("FULL JSON REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("=" * 60)

    print("\n" + "=" * 60)
    print("PROBE SUMMARY")
    print("=" * 60)
    print(f"Files tested: {report['summary'].get('files_tested', 0)}")
    print(f"Strategies passed: {report['summary'].get('strategies_passed', 0)}/{report['summary'].get('total_strategies_attempted', 0)}")
    print(f"Success rate: {report['summary'].get('success_rate', 0)}")
    if report.get("error"):
        print(f"Error: {report['error']}")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    print("=" * 60)

    for f in report.get("files_tested", []):
        diag = f.get("diagnosis", {})
        print(f"\nFile: {f['filename']} (clicked: {f.get('click_method_used', 'none')})")
        print(f"  DOM: preview={diag.get('preview_panel_count',0)} monaco={diag.get('monaco_editor_count',0)} download={diag.get('download_button_count',0)} copy={diag.get('copy_button_count',0)}")
        print(f"  Preview class: {diag.get('preview_panel_first_class','')[:60]}")
        print(f"  Monaco class: {diag.get('monaco_editor_first_class','')[:60]}")
        print(f"  Download class: {diag.get('download_button_first_class','')[:60]}")
        for s in f.get("strategies", []):
            status = "PASS" if s.get("passed") else "FAIL"
            print(f"  [{status}] {s['strategy']}: len={s.get('length', 0)} duration={s.get('duration_ms', 0)}ms")
            if s.get("error"):
                print(f"       error: {s['error'][:80]}")


def main():
    parser = argparse.ArgumentParser(description="Kimi Selector Probe v1.0.7")
    parser.add_argument("--url", required=True, help="Kimi chat URL to probe")
    parser.add_argument("--visible", action="store_true", help="Run in visible browser mode")
    parser.add_argument("--max-per-type", type=int, default=2, help="Max files to test per extension type")
    args = parser.parse_args()

    log(f"[MAIN] Starting probe for {args.url}")
    log(f"[MAIN] Mode: {'visible' if args.visible else 'headless'}, max_per_type: {args.max_per_type}")

    report = asyncio.run(run_probe(args.url, visible=args.visible, max_per_type=args.max_per_type))
    save_and_print_report(report)


if __name__ == "__main__":
    main()
