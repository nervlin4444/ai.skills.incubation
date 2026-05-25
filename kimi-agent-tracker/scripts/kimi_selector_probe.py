"""
---
title: Kimi Selector Probe v1.0.8
name: kimi-agent-tracker
description: Auto-detect working selectors for .py/.md/.json/.zip file extraction from Kimi chat pages.
version: 1.0.8
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T00:25:00+08:00
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

PROFILE_DIR = Path.home() / ".kimi_auth" / "browser_profile_chromium"
REPORT_PATH = Path.home() / "Downloads" / "selector_test_report.json"
SCREENSHOT_DIR = Path.home() / "Downloads" / "probe_screenshots"

FILE_CARD_SELECTORS = [
    'div[class*="file-card-container"]',
    'div[class*="file-card"]',
    'div[data-v-][class*="file"]',
    'div[class*="file-item"]',
    'div[class*="attachment"]',
    'a[class*="file"]',
    'div[data-v-]',
]

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


async def deep_diagnose(page) -> Dict[str, Any]:
    diagnosis = {
        "iframe_count": 0,
        "iframes": [],
        "shadow_hosts": [],
        "right_side_elements": [],
        "top_right_elements": [],
        "all_visible_classes": [],
        "monaco_in_iframe": False,
        "monaco_in_main": False,
    }

    frames = page.frames
    diagnosis["iframe_count"] = len(frames)
    log(f"[DIAG] Found {len(frames)} frames")

    for i, frame in enumerate(frames):
        try:
            url = frame.url
            frame_data = await frame.evaluate("""
                () => {
                    const result = {
                        url: location.href,
                        has_monaco: !!window.monaco,
                        body_classes: document.body?.className || '',
                        element_count: document.querySelectorAll('*').length,
                        preview_like: [],
                        download_like: [],
                        copy_like: [],
                    };
                    document.querySelectorAll('*').forEach(el => {
                        const cls = el.className || '';
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 400 && rect.left > window.innerWidth * 0.4) {
                            result.preview_like.push({
                                tag: el.tagName,
                                class: cls.substring(0, 100),
                                width: rect.width,
                                height: rect.height,
                                left: rect.left,
                                top: rect.top,
                            });
                        }
                        if (cls.includes('download') || el.getAttribute('title')?.includes('download')) {
                            result.download_like.push({tag: el.tagName, class: cls.substring(0, 100)});
                        }
                        if (cls.includes('copy') || el.getAttribute('title')?.includes('copy')) {
                            result.copy_like.push({tag: el.tagName, class: cls.substring(0, 100)});
                        }
                    });
                    return result;
                }
            """)
            diagnosis["iframes"].append({
                "index": i,
                "url": url[:100],
                "has_monaco": frame_data.get("has_monaco", False),
                "body_classes": frame_data.get("body_classes", "")[:100],
                "element_count": frame_data.get("element_count", 0),
                "preview_like_count": len(frame_data.get("preview_like", [])),
                "download_like_count": len(frame_data.get("download_like", [])),
                "copy_like_count": len(frame_data.get("copy_like", [])),
                "preview_like_first": frame_data.get("preview_like", [{}])[0] if frame_data.get("preview_like") else None,
            })
            if frame_data.get("has_monaco"):
                diagnosis["monaco_in_iframe"] = True
        except Exception as e:
            log(f"[WARN] Frame {i} diagnosis failed: {e}")

    try:
        main_data = await page.evaluate("""
            () => {
                const result = {
                    has_monaco: !!window.monaco,
                    body_classes: document.body?.className || '',
                    shadow_hosts: [],
                    right_side_elements: [],
                    top_right_elements: [],
                    all_classes: new Set(),
                };
                document.querySelectorAll('*').forEach(el => {
                    if (el.shadowRoot) {
                        result.shadow_hosts.push({
                            tag: el.tagName,
                            class: (el.className || '').substring(0, 100),
                            id: el.id || '',
                        });
                    }
                    const rect = el.getBoundingClientRect();
                    const cls = el.className || '';
                    if (rect.width > 500 && rect.left > window.innerWidth * 0.45 && rect.height > 300) {
                        result.right_side_elements.push({
                            tag: el.tagName,
                            class: cls.substring(0, 150),
                            id: el.id || '',
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            left: Math.round(rect.left),
                            top: Math.round(rect.top),
                        });
                    }
                    if (rect.width < 60 && rect.height < 60 && rect.left > window.innerWidth * 0.8 && rect.top < 100) {
                        result.top_right_elements.push({
                            tag: el.tagName,
                            class: cls.substring(0, 100),
                            id: el.id || '',
                            title: el.getAttribute('title') || '',
                            aria_label: el.getAttribute('aria-label') || '',
                            html: el.outerHTML?.substring(0, 200) || '',
                        });
                    }
                    if (cls && cls.length > 0) {
                        const keywords = ['preview', 'monaco', 'download', 'copy', 'editor', 'code', 'file', 'panel', 'drawer', 'content', 'view'];
                        const classes = cls.split(/\s+/);
                        classes.forEach(c => {
                            if (c.length > 3 && keywords.some(k => c.toLowerCase().includes(k))) {
                                result.all_classes.add(c);
                            }
                        });
                    }
                });
                result.all_classes = Array.from(result.all_classes).slice(0, 50);
                return result;
            }
        """)
        diagnosis["monaco_in_main"] = main_data.get("has_monaco", False)
        diagnosis["shadow_hosts"] = main_data.get("shadow_hosts", [])
        diagnosis["right_side_elements"] = main_data.get("right_side_elements", [])
        diagnosis["top_right_elements"] = main_data.get("top_right_elements", [])
        diagnosis["all_visible_classes"] = main_data.get("all_classes", [])
    except Exception as e:
        log(f"[WARN] Main frame diagnosis failed: {e}")

    return diagnosis


async def test_strategy_monaco_api(page, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    result = {"strategy": "A_monaco_api", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()

    has_monaco = await page.evaluate("() => !!window.monaco")
    if has_monaco:
        try:
            text = await page.evaluate("""
                (() => {
                    try {
                        const editors = window.monaco?.editor?.getEditors();
                        if (editors && editors.length > 0) return editors[0].getValue();
                        const models = window.monaco?.editor?.getModels();
                        if (models && models.length > 0) return models[0].getValue();
                        return "__NO_MONACO__";
                    } catch (e) { return "__ERROR__: " + e.message; }
                })()
            """)
            if text and not text.startswith("__"):
                result["passed"] = True
                result["length"] = len(text)
                result["sample"] = text[:200]
                result["duration_ms"] = now_ms() - start
                return result
        except Exception as e:
            result["error"] = f"main frame monaco error: {e}"

    for i, frame in enumerate(page.frames):
        try:
            has_monaco_frame = await frame.evaluate("() => !!window.monaco")
            if has_monaco_frame:
                text = await frame.evaluate("""
                    (() => {
                        try {
                            const editors = window.monaco?.editor?.getEditors();
                            if (editors && editors.length > 0) return editors[0].getValue();
                            const models = window.monaco?.editor?.getModels();
                            if (models && models.length > 0) return models[0].getValue();
                            return "__NO_MONACO__";
                        } catch (e) { return "__ERROR__: " + e.message; }
                    })()
                """)
                if text and not text.startswith("__"):
                    result["passed"] = True
                    result["length"] = len(text)
                    result["sample"] = text[:200]
                    result["iframe_index"] = i
                    result["duration_ms"] = now_ms() - start
                    return result
        except Exception:
            continue

    result["error"] = result.get("error", "window.monaco not available in any frame")
    result["duration_ms"] = now_ms() - start
    return result


async def test_strategy_preview_content(page, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    result = {"strategy": "B_preview_content", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()

    right_elements = diagnosis.get("right_side_elements", [])
    if not right_elements:
        result["error"] = "no right-side elements found"
        result["duration_ms"] = now_ms() - start
        return result

    for el_info in right_elements[:3]:
        tag = el_info.get("tag", "div")
        cls = el_info.get("class", "").split()[0] if el_info.get("class") else ""
        el_id = el_info.get("id", "")

        if el_id:
            selector = f'#{el_id}'
        elif cls:
            selector = f'{tag}.{cls}'
        else:
            continue

        try:
            el = await page.wait_for_selector(selector, timeout=2000, state="visible")
            if el:
                content_selectors = ['pre', 'code', 'div[class*="content"]', 'div[class*="monaco"]', 'div[class*="editor"]']
                for content_sel in content_selectors:
                    try:
                        content_el = await el.wait_for_selector(content_sel, timeout=1000)
                        if content_el:
                            text = await content_el.inner_text()
                            if text and len(text) > 100:
                                result["passed"] = True
                                result["length"] = len(text)
                                result["selector"] = selector
                                result["content_selector"] = content_sel
                                result["sample"] = text[:200]
                                result["duration_ms"] = now_ms() - start
                                return result
                    except Exception:
                        continue

                text = await el.inner_text()
                if text and len(text) > 100:
                    result["passed"] = True
                    result["length"] = len(text)
                    result["selector"] = selector
                    result["sample"] = text[:200]
                    result["duration_ms"] = now_ms() - start
                    return result
        except Exception:
            continue

    result["error"] = "no content found in right-side elements"
    result["duration_ms"] = now_ms() - start
    return result


async def test_strategy_top_right_buttons(page, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    result = {"strategy": "C_top_right_buttons", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()

    top_right = diagnosis.get("top_right_elements", [])
    if not top_right:
        result["error"] = "no top-right elements found"
        result["duration_ms"] = now_ms() - start
        return result

    for el_info in top_right:
        tag = el_info.get("tag", "div")
        cls = el_info.get("class", "").split()[0] if el_info.get("class") else ""
        el_id = el_info.get("id", "")

        if el_id:
            selector = f'#{el_id}'
        elif cls:
            selector = f'{tag}.{cls}'
        else:
            continue

        log(f"[TEST] Trying top-right: {selector}")

        download_info = {"path": None}
        def handle_download(download):
            download_info["path"] = asyncio.create_task(download.path())
        page.on("download", handle_download)

        try:
            clicked = await safe_click(page, selector, timeout=2000)
            if clicked:
                await asyncio.sleep(2.0)
                if download_info["path"]:
                    path = await download_info["path"]
                    if path and Path(path).exists():
                        text = Path(path).read_text(encoding="utf-8", errors="ignore")
                        result["passed"] = True
                        result["length"] = len(text)
                        result["sample"] = text[:200]
                        result["used_selector"] = selector
                        result["file_path"] = str(path)
                        result["duration_ms"] = now_ms() - start
                        page.remove_listener("download", handle_download)
                        return result
            page.remove_listener("download", handle_download)
        except Exception:
            page.remove_listener("download", handle_download)
            continue

    result["error"] = "no top-right button triggered download"
    result["duration_ms"] = now_ms() - start
    return result


async def test_strategy_js_content_extract(page) -> Dict[str, Any]:
    result = {"strategy": "D_js_content_extract", "passed": False, "length": 0, "duration_ms": 0, "error": None}
    start = now_ms()

    try:
        data = await page.evaluate("""
            (() => {
                let best = null;
                let bestArea = 0;
                document.querySelectorAll('*').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const area = rect.width * rect.height;
                    if (rect.left > window.innerWidth * 0.45 && area > bestArea && rect.width > 400 && rect.height > 300) {
                        best = el;
                        bestArea = area;
                    }
                });
                if (!best) return {error: "no large right-side element"};
                const text = best.innerText || best.textContent || '';
                let monacoValue = null;
                if (window.monaco) {
                    const editors = window.monaco.editor?.getEditors();
                    if (editors && editors.length > 0) monacoValue = editors[0].getValue();
                }
                return {
                    tag: best.tagName,
                    class: (best.className || '').substring(0, 200),
                    text: text.substring(0, 500),
                    text_length: text.length,
                    has_monaco: !!window.monaco,
                    monaco_value: monacoValue ? monacoValue.substring(0, 500) : null,
                    monaco_length: monacoValue ? monacoValue.length : 0,
                };
            })()
        """)

        result["duration_ms"] = now_ms() - start
        if data.get("monaco_value"):
            result["passed"] = True
            result["length"] = data["monaco_length"]
            result["sample"] = data["monaco_value"][:200]
            result["method"] = "monaco_api"
        elif data.get("text") and data.get("text_length", 0) > 100:
            result["passed"] = True
            result["length"] = data["text_length"]
            result["sample"] = data["text"][:200]
            result["method"] = "innerText"
            result["element_class"] = data.get("class", "")[:100]
        else:
            result["error"] = data.get("error", "content too short")
            result["element_class"] = data.get("class", "")[:100]
    except Exception as e:
        result["duration_ms"] = now_ms() - start
        result["error"] = str(e)
    return result


async def test_file(page, file_info: Dict[str, Any], visible: bool, file_index: int) -> Dict[str, Any]:
    filename = file_info.get("filename", "unknown")
    ext = file_info.get("ext", "")
    card_selector = file_info.get("selector", "")
    log(f"[TEST] File: {filename} (.{ext})")

    if not card_selector:
        return {"filename": filename, "ext": ext, "strategies": [], "error": "no selector"}

    before_ss = await take_screenshot(page, f"{file_index:02d}_{filename}_before")

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
                log(f"[OK] Click: {method_name}")
                break
        except Exception as e:
            log(f"[WARN] Click {method_name} failed: {e}")

    if not click_ok:
        log(f"[WARN] All click methods failed for {filename}")

    log("[TEST] Waiting 8s for preview...")
    await asyncio.sleep(8.0)

    after_ss = await take_screenshot(page, f"{file_index:02d}_{filename}_after")

    log("[TEST] Running deep DOM diagnosis...")
    diagnosis = await deep_diagnose(page)
    log(f"[DIAG] Frames: {diagnosis['iframe_count']}, Shadow hosts: {len(diagnosis['shadow_hosts'])}")
    log(f"[DIAG] Right-side elements: {len(diagnosis['right_side_elements'])}, Top-right: {len(diagnosis['top_right_elements'])}")
    log(f"[DIAG] Monaco main: {diagnosis['monaco_in_main']}, iframe: {diagnosis['monaco_in_iframe']}")
    if diagnosis.get("right_side_elements"):
        log(f"[DIAG] First right-side: {diagnosis['right_side_elements'][0].get('class', '')[:60]}")
    if diagnosis.get("top_right_elements"):
        log(f"[DIAG] First top-right: {diagnosis['top_right_elements'][0].get('class', '')[:60]} title={diagnosis['top_right_elements'][0].get('title', '')}")

    strategies = []
    strategies.append(await test_strategy_js_content_extract(page))
    strategies.append(await test_strategy_monaco_api(page, diagnosis))
    strategies.append(await test_strategy_preview_content(page, diagnosis))
    strategies.append(await test_strategy_top_right_buttons(page, diagnosis))

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
            "iframe_count": diagnosis["iframe_count"],
            "shadow_host_count": len(diagnosis["shadow_hosts"]),
            "right_side_count": len(diagnosis["right_side_elements"]),
            "top_right_count": len(diagnosis["top_right_elements"]),
            "monaco_main": diagnosis["monaco_in_main"],
            "monaco_iframe": diagnosis["monaco_in_iframe"],
            "right_side_first_class": diagnosis.get("right_side_elements", [{}])[0].get("class", "") if diagnosis.get("right_side_elements") else "",
            "top_right_first_class": diagnosis.get("top_right_elements", [{}])[0].get("class", "") if diagnosis.get("top_right_elements") else "",
            "top_right_first_title": diagnosis.get("top_right_elements", [{}])[0].get("title", "") if diagnosis.get("top_right_elements") else "",
            "interesting_classes": diagnosis.get("all_visible_classes", [])[:10],
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
        "probe_version": "1.0.8",
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
        print(f"  DOM: iframes={diag.get('iframe_count',0)} shadow={diag.get('shadow_host_count',0)} right={diag.get('right_side_count',0)} top-right={diag.get('top_right_count',0)}")
        print(f"  Monaco: main={diag.get('monaco_main',False)} iframe={diag.get('monaco_iframe',False)}")
        print(f"  Right-side class: {diag.get('right_side_first_class','')[:60]}")
        print(f"  Top-right class: {diag.get('top_right_first_class','')[:60]} title={diag.get('top_right_first_title','')}")
        print(f"  Interesting classes: {', '.join(diag.get('interesting_classes', [])[:5])}")
        for s in f.get("strategies", []):
            status = "PASS" if s.get("passed") else "FAIL"
            print(f"  [{status}] {s['strategy']}: len={s.get('length', 0)} duration={s.get('duration_ms', 0)}ms")
            if s.get("error"):
                print(f"       error: {s['error'][:80]}")


def main():
    parser = argparse.ArgumentParser(description="Kimi Selector Probe v1.0.8")
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
