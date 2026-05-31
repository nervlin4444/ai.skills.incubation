"""
---
title: Kimi Selector Probe v4.0.0
name: kimi-agent-tracker
description: Auto-detect working selectors for .py/.md/.json/.zip file extraction from Kimi chat pages.
version: "v4.0.0"
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: "2026-05-27T10:00:00+00:00"
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
DOWNLOAD_TEST_DIR = Path.home() / "Downloads" / "probe_download_test"

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


async def reset_page_state(page) -> None:
    """Clear any open preview panels before testing next file."""
    try:
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.3)
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.3)
        await page.mouse.click(100, 300)
        await asyncio.sleep(0.5)
    except Exception:
        pass


async def deep_diagnose(page) -> Dict[str, Any]:
    diagnosis = {
        "iframe_count": 0,
        "iframes": [],
        "shadow_hosts": [],
        "right_side_elements": [],
        "top_right_elements": [],
        "download_buttons": [],
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
                        let cls = el.className || '';
                        if (typeof cls !== 'string') {
                            cls = cls.baseVal || '';
                        }
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
                        const title = el.getAttribute('title') || '';
                        if (cls.includes('download') || title.includes('download')) {
                            result.download_like.push({tag: el.tagName, class: cls.substring(0, 100)});
                        }
                        if (cls.includes('copy') || title.includes('copy')) {
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
                    download_buttons: [],
                    all_classes: new Set(),
                };
                
                const artifactHeaders = document.querySelectorAll('[class*="artifact-header-actions"], [class*="preview-header"]');
                artifactHeaders.forEach(container => {
                    const buttons = container.querySelectorAll('button, [role="button"], .icon-button');
                    buttons.forEach((btn, idx) => {
                        const rect = btn.getBoundingClientRect();
                        let cls = btn.className || '';
                        if (typeof cls !== 'string') cls = cls.baseVal || '';
                        const svg = btn.querySelector('svg');
                        const hasSvg = !!svg;
                        let svgHint = false;
                        if (svg) {
                            const svgHtml = svg.outerHTML.toLowerCase();
                            svgHint = svgHtml.includes('download') || svgHtml.includes('arrow-down') || 
                                      svgHtml.includes('arrow') || svgHtml.includes('down');
                        }
                        const aria = btn.getAttribute('aria-label') || '';
                        const title = btn.getAttribute('title') || '';
                        const textHint = (aria + title).toLowerCase().includes('download') || 
                                         (aria + title).toLowerCase().includes('save');
                        
                        result.download_buttons.push({
                            tag: btn.tagName,
                            class: cls.substring(0, 100),
                            id: btn.id || '',
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            left: Math.round(rect.left),
                            top: Math.round(rect.top),
                            hasSvg: hasSvg,
                            svgHint: svgHint,
                            textHint: textHint,
                            index: idx,
                            containerClass: (container.className || '').substring(0, 50),
                            aria: aria,
                            title: title,
                        });
                    });
                });
                
                document.querySelectorAll('*').forEach(el => {
                    if (el.shadowRoot) {
                        let cls = el.className || '';
                        if (typeof cls !== 'string') cls = cls.baseVal || '';
                        result.shadow_hosts.push({
                            tag: el.tagName,
                            class: cls.substring(0, 100),
                            id: el.id || '',
                        });
                    }
                    const rect = el.getBoundingClientRect();
                    let cls = el.className || '';
                    if (typeof cls !== 'string') cls = cls.baseVal || '';
                    
                    if (rect.width > 300 && rect.left > window.innerWidth * 0.35 && rect.height > 200) {
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
                    if (rect.width < 80 && rect.height < 80 && rect.left > window.innerWidth * 0.75 && rect.top < 120) {
                        const title = el.getAttribute('title') || '';
                        const aria_label = el.getAttribute('aria-label') || '';
                        result.top_right_elements.push({
                            tag: el.tagName,
                            class: cls.substring(0, 100),
                            id: el.id || '',
                            title: title,
                            aria_label: aria_label,
                            html: el.outerHTML?.substring(0, 200) || '',
                        });
                    }
                    if (cls && cls.length > 0) {
                        const keywords = ['preview', 'monaco', 'download', 'copy', 'editor', 'code', 'file', 'panel', 'drawer', 'content', 'view', 'language', 'artifact'];
                        const classes = cls.split(/\\s+/);
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
        diagnosis["download_buttons"] = main_data.get("download_buttons", [])
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


async def test_strategy_download_button(page, diagnosis: Dict[str, Any], filename: str) -> Dict[str, Any]:
    result = {
        "strategy": "C_download_button",
        "passed": False,
        "length": 0,
        "duration_ms": 0,
        "error": None,
        "download_triggered": False,
        "download_path": None,
        "candidates_tried": 0,
    }
    start = now_ms()

    download_buttons = diagnosis.get("download_buttons", [])
    
    if not download_buttons:
        result["error"] = "no artifact-header download buttons found"
        result["duration_ms"] = now_ms() - start
        return result

    DOWNLOAD_TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    scored = []
    for btn in download_buttons:
        score = 0
        if btn.get("svgHint"):
            score += 30
        if btn.get("textHint"):
            score += 20
        if btn.get("hasSvg"):
            score += 10
        if btn.get("width", 100) < 50 and btn.get("height", 100) < 50:
            score += 5
        scored.append({**btn, "score": score})
    
    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    candidates = scored[:3]
    
    log(f"[TEST] Artifact download candidates: {len(candidates)} (scores: {[c.get('score',0) for c in candidates]})")

    for i, cand in enumerate(candidates):
        result["candidates_tried"] = i + 1
        tag = cand.get("tag", "div")
        cls = cand.get("class", "").split()[0] if cand.get("class") else ""
        el_id = cand.get("id", "")
        score = cand.get("score", 0)
        
        if el_id:
            selector = f'#{el_id}'
        elif cls:
            safe_cls = cls.replace(".", "\\.").replace(":", "\\:")
            selector = f'{tag}.{safe_cls}'
        else:
            continue
        
        if cand.get("index") is not None:
            selector = f'{tag}.{safe_cls}:nth-of-type({cand["index"] + 1})'
        
        log(f"[TEST] Trying artifact dl-btn {i+1}/{len(candidates)}: {selector} (score={score})")

        download_info = {"path": None}
        def handle_download(download):
            download_info["path"] = asyncio.create_task(download.path())
        page.on("download", handle_download)

        try:
            clicked = await safe_click(page, selector, timeout=1500, force=True)
            if not clicked:
                parent_selector = selector + " > button, " + selector + " > [role=button]"
                clicked = await safe_click(page, parent_selector, timeout=1000, force=True)
            
            if clicked:
                await asyncio.sleep(1.5)
                
                if download_info["path"]:
                    try:
                        path = await asyncio.wait_for(download_info["path"], timeout=3.0)
                    except asyncio.TimeoutError:
                        path = None
                    
                    if path and Path(path).exists():
                        try:
                            text = Path(path).read_text(encoding="utf-8", errors="ignore")
                        except Exception:
                            text = ""
                        result["passed"] = True
                        result["download_triggered"] = True
                        result["length"] = len(text)
                        result["sample"] = text[:200] if text else "(binary or non-text file)"
                        result["used_selector"] = selector
                        result["download_path"] = str(path)
                        result["duration_ms"] = now_ms() - start
                        page.remove_listener("download", handle_download)
                        return result
                
                try:
                    dialog = await page.evaluate("""
                        () => {
                            const dialogs = document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popover"], [class*="dropdown"], [class*="menu"]');
                            for (const d of dialogs) {
                                if (d.offsetParent !== null) return d.className;
                            }
                            return '';
                        }
                    """)
                    if dialog:
                        log(f"[TEST] Format dialog detected: {dialog[:60]}")
                        md_clicked = await page.evaluate("""
                            () => {
                                const items = document.querySelectorAll('[class*="menu"] *, [class*="dropdown"] *');
                                for (const item of items) {
                                    const text = item.innerText || item.textContent || '';
                                    if (text.toLowerCase().includes('markdown') || text.toLowerCase().includes('md')) {
                                        item.click();
                                        return true;
                                    }
                                }
                                return false;
                            }
                        """)
                        if md_clicked:
                            log("[TEST] Clicked Markdown option in dialog")
                            await asyncio.sleep(2.0)
                            if download_info["path"]:
                                try:
                                    path = await asyncio.wait_for(download_info["path"], timeout=5.0)
                                except asyncio.TimeoutError:
                                    path = None
                                if path and Path(path).exists():
                                    result["passed"] = True
                                    result["download_triggered"] = True
                                    result["used_selector"] = selector + " + Markdown dialog"
                                    result["download_path"] = str(path)
                                    result["duration_ms"] = now_ms() - start
                                    page.remove_listener("download", handle_download)
                                    return result
                        await page.keyboard.press("Escape")
                        await asyncio.sleep(0.5)
                except Exception:
                    pass

            page.remove_listener("download", handle_download)
        except Exception as e:
            log(f"[WARN] Download btn {i+1} exception: {e}")
            page.remove_listener("download", handle_download)
            continue

    result["error"] = f"tried {len(candidates)} artifact download buttons, none triggered browser download"
    result["duration_ms"] = now_ms() - start
    return result


async def test_strategy_js_content_extract(page) -> Dict[str, Any]:
    result = {
        "strategy": "D_js_content_extract",
        "passed": False,
        "length": 0,
        "duration_ms": 0,
        "error": None,
        "full_text": None,
        "element_class": None,
    }
    start = now_ms()

    try:
        data = await page.evaluate("""
            (() => {
                let best = null;
                let bestArea = 0;
                document.querySelectorAll('*').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const area = rect.width * rect.height;
                    if (area > bestArea && rect.width > 300 && rect.height > 200) {
                        let cls = el.className || '';
                        if (typeof cls !== 'string') cls = cls.baseVal || '';
                        const clsLower = cls.toLowerCase();
                        
                        const isPreviewLike = clsLower.includes('language-py') || clsLower.includes('markdown') || 
                            clsLower.includes('language-json') || clsLower.includes('monaco') ||
                            clsLower.includes('editor') || clsLower.includes('preview') ||
                            clsLower.includes('side-console') || clsLower.includes('artifact');
                        
                        if (!isPreviewLike) return;
                        
                        let parent = el.parentElement;
                        let isChatBubble = false;
                        for (let i = 0; i < 6 && parent; i++) {
                            const pCls = (parent.className || '').toLowerCase();
                            if (pCls.includes('message') || pCls.includes('chat-bubble') || 
                                pCls.includes('conversation-item') || pCls.includes('toolcall-content') ||
                                pCls.includes('chat-message')) {
                                isChatBubble = true;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                        
                        if (!isChatBubble) {
                            best = el;
                            bestArea = area;
                        }
                    }
                });
                if (!best) return {error: "no preview-like element found (all are chat bubbles or not preview-like)"};
                const text = best.innerText || best.textContent || '';
                let monacoValue = null;
                if (window.monaco) {
                    const editors = window.monaco.editor?.getEditors();
                    if (editors && editors.length > 0) monacoValue = editors[0].getValue();
                }
                let cls = best.className || '';
                if (typeof cls !== 'string') cls = cls.baseVal || '';
                return {
                    tag: best.tagName,
                    class: cls.substring(0, 200),
                    text: text,
                    text_length: text.length,
                    has_monaco: !!window.monaco,
                    monaco_value: monacoValue ? monacoValue : null,
                    monaco_length: monacoValue ? monacoValue.length : 0,
                };
            })()
        """)

        result["duration_ms"] = now_ms() - start
        result["element_class"] = data.get("class", "")[:100]
        
        if data.get("monaco_value"):
            result["passed"] = True
            result["length"] = data["monaco_length"]
            result["sample"] = data["monaco_value"][:200]
            result["full_text"] = data["monaco_value"]
            result["method"] = "monaco_api"
        elif data.get("text") and data.get("text_length", 0) > 100:
            result["passed"] = True
            result["length"] = data["text_length"]
            result["sample"] = data["text"][:200]
            result["full_text"] = data["text"]
            result["method"] = "innerText"
        else:
            result["error"] = data.get("error", "content too short")
    except Exception as e:
        result["duration_ms"] = now_ms() - start
        result["error"] = str(e)
    return result


async def test_strategy_content_save(page, filename: str, ext: str, d_result: Dict[str, Any]) -> Dict[str, Any]:
    result = {
        "strategy": "E_content_save",
        "passed": False,
        "length": 0,
        "duration_ms": 0,
        "error": None,
        "saved_path": None,
    }
    start = now_ms()
    
    if not d_result.get("passed"):
        result["error"] = "D_strategy did not pass, no content to save"
        result["duration_ms"] = now_ms() - start
        return result
    
    content = d_result.get("full_text", "")
    if not content:
        content = d_result.get("sample", "")
    
    if not content or len(content) < 100:
        result["error"] = f"content too short to save (len={len(content) if content else 0})"
        result["duration_ms"] = now_ms() - start
        return result
    
    try:
        DOWNLOAD_TEST_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', filename)
        save_path = DOWNLOAD_TEST_DIR / safe_name
        save_path.write_text(content, encoding="utf-8")
        result["passed"] = True
        result["length"] = len(content)
        result["saved_path"] = str(save_path)
        result["sample"] = content[:200]
        result["duration_ms"] = now_ms() - start
        log(f"[OK] E_strategy saved {len(content)} chars to {save_path}")
    except Exception as e:
        result["error"] = f"failed to write file: {e}"
        result["duration_ms"] = now_ms() - start
    
    return result


async def test_file(page, file_info: Dict[str, Any], visible: bool, file_index: int) -> Dict[str, Any]:
    filename = file_info.get("filename", "unknown")
    ext = file_info.get("ext", "")
    card_selector = file_info.get("selector", "")
    log(f"[TEST] File: {filename} (.{ext})")

    if not card_selector:
        return {"filename": filename, "ext": ext, "strategies": [], "error": "no selector"}

    await reset_page_state(page)
    await asyncio.sleep(1.0)

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
    log(f"[DIAG] Artifact download buttons: {len(diagnosis['download_buttons'])}")
    log(f"[DIAG] Monaco main: {diagnosis['monaco_in_main']}, iframe: {diagnosis['monaco_in_iframe']}")
    if diagnosis.get("download_buttons"):
        first = diagnosis['download_buttons'][0]
        log(f"[DIAG] First dl-btn: {first.get('class','')[:40]} score={first.get('score',0)} svg={first.get('hasSvg')} svgHint={first.get('svgHint')} textHint={first.get('textHint')}")
    if diagnosis.get("right_side_elements"):
        log(f"[DIAG] First right-side: {diagnosis['right_side_elements'][0].get('class', '')[:60]}")

    strategies = []
    
    d_result = await test_strategy_js_content_extract(page)
    strategies.append(d_result)
    
    strategies.append(await test_strategy_content_save(page, filename, ext, d_result))
    
    strategies.append(await test_strategy_monaco_api(page, diagnosis))
    
    strategies.append(await test_strategy_preview_content(page, diagnosis))
    
    strategies.append(await test_strategy_download_button(page, diagnosis, filename))

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
            "download_button_count": len(diagnosis["download_buttons"]),
            "monaco_main": diagnosis["monaco_in_main"],
            "monaco_iframe": diagnosis["monaco_in_iframe"],
            "right_side_first_class": diagnosis.get("right_side_elements", [{}])[0].get("class", "") if diagnosis.get("right_side_elements") else "",
            "top_right_first_class": diagnosis.get("top_right_elements", [{}])[0].get("class", "") if diagnosis.get("top_right_elements") else "",
            "top_right_first_title": diagnosis.get("top_right_elements", [{}])[0].get("title", "") if diagnosis.get("top_right_elements") else "",
            "download_button_first_class": diagnosis.get("download_buttons", [{}])[0].get("class", "") if diagnosis.get("download_buttons") else "",
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
                selector = f'{used_selector} >> nth={idx}'
                
                download_btn_selector = None
                try:
                    has_icon = await card.evaluate("""
                        (card) => {
                            const icons = card.querySelectorAll('.icon-button, [class*=\"download\"], svg');
                            return icons.length > 0 ? icons[0].className || 'svg' : null;
                        }
                    """)
                    if has_icon:
                        download_btn_selector = f'{used_selector} >> nth={idx} .icon-button'
                except Exception:
                    pass

                all_files.append({
                    "filename": filename,
                    "ext": ext,
                    "selector": selector,
                    "download_btn_selector": download_btn_selector,
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
        "probe_version": "1.1.1",
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
    print(f"Download test dir: {DOWNLOAD_TEST_DIR}")
    print("=" * 60)

    for f in report.get("files_tested", []):
        diag = f.get("diagnosis", {})
        print(f"\nFile: {f['filename']} (clicked: {f.get('click_method_used', 'none')})")
        print(f"  DOM: iframes={diag.get('iframe_count',0)} shadow={diag.get('shadow_host_count',0)} right={diag.get('right_side_count',0)} top-right={diag.get('top_right_count',0)} dl-btns={diag.get('download_button_count',0)}")
        print(f"  Monaco: main={diag.get('monaco_main',False)} iframe={diag.get('monaco_iframe',False)}")
        print(f"  Right-side class: {diag.get('right_side_first_class','')[:60]}")
        print(f"  Download btn class: {diag.get('download_button_first_class','')[:60]}")
        print(f"  Interesting classes: {', '.join(diag.get('interesting_classes', [])[:5])}")
        for s in f.get("strategies", []):
            status = "PASS" if s.get("passed") else "FAIL"
            extra = ""
            if s.get("download_triggered"):
                extra = f" [DOWNLOADED -> {s.get('download_path', 'unknown')}]"
            if s.get("saved_path"):
                extra = f" [SAVED -> {s.get('saved_path', 'unknown')}]"
            print(f"  [{status}] {s['strategy']}: len={s.get('length', 0)} duration={s.get('duration_ms', 0)}ms{extra}")
            if s.get("error"):
                print(f"       error: {s['error'][:80]}")
            if s.get("candidates_tried") is not None:
                print(f"       candidates tried: {s['candidates_tried']}")
            if s.get("method"):
                print(f"       method: {s['method']}, class: {s.get('element_class', 'unknown')}")


def main():
    parser = argparse.ArgumentParser(description="Kimi Selector Probe v1.1.1")
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