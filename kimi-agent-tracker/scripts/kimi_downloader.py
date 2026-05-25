"""
---
title: Kimi Downloader v3.6.1
name: kimi-agent-tracker
description: Download .py/.md/.json/.zip files from Kimi chat pages. Files saved to ~/Downloads/ with original filenames.
version: 3.6.1
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-26T00:35:00+08:00
auth_config:
  provider: none
  auth_method: none
  token_env_var: none
  env_file_path: none
file_mapping:
  local_path: "{baseDir}/scripts/kimi_downloader.py"
  github_path: "kimi-agent-tracker/scripts/kimi_downloader.py"
---
"""

import asyncio
import json
import sys
import time
import argparse
import re
import shutil
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
DOWNLOAD_DIR = Path.home() / "Downloads"

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


async def scan_files(page) -> List[Dict[str, Any]]:
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
                })
        except Exception as e:
            log(f"[WARN] Error processing card {idx}: {e}")

    log(f"[SCAN] Extracted {len(all_files)} valid files")
    return all_files


async def click_file_card(page, file_info: Dict[str, Any]) -> bool:
    card_selector = file_info.get("selector", "")
    if not card_selector:
        return False

    click_methods = [
        lambda: safe_click(page, card_selector, timeout=5000, force=True),
        lambda: safe_click(page, card_selector, timeout=5000, force=False),
        lambda: js_click(page, card_selector),
    ]

    for method_fn in click_methods:
        try:
            if await method_fn():
                log(f"[OK] Clicked file card: {file_info['filename']}")
                return True
        except Exception:
            continue

    log(f"[WARN] Failed to click file card: {file_info['filename']}")
    return False


async def click_download_button_in_preview(page) -> Optional[str]:
    """Click download button inside preview panel and capture download."""
    download_info = {"path": None}

    def handle_download(download):
        download_info["path"] = asyncio.create_task(download.path())

    page.on("download", handle_download)

    try:
        # Strategy 1: Try all buttons in top-right area
        buttons = await page.query_selector_all('button, svg, [class*="icon"]')
        for btn in buttons:
            try:
                box = await btn.bounding_box()
                if box and box["x"] > 800 and box["y"] < 100 and box["width"] < 60:
                    await btn.click(force=True)
                    log(f"[OK] Clicked top-right button at ({box['x']}, {box['y']})")
                    await asyncio.sleep(3.0)
                    if download_info["path"]:
                        path = await download_info["path"]
                        if path and Path(path).exists():
                            page.remove_listener("download", handle_download)
                            return str(path)
            except Exception:
                continue
    except Exception as e:
        log(f"[WARN] Download button click failed: {e}")
    finally:
        page.remove_listener("download", handle_download)

    return None


async def download_file(page, file_info: Dict[str, Any]) -> Optional[str]:
    """Download a single file. Returns final path in ~/Downloads/."""
    filename = file_info["filename"]
    ext = file_info["ext"]

    log(f"[DL] Processing: {filename}")

    # Strategy 1: Try direct download (for .py/.json/.zip)
    if ext in ("py", "json", "zip", "env", "txt", "csv", "yaml", "yml", "js", "html", "css", "xml"):
        log(f"[DL] Trying direct download for {filename}")
        try:
            async with page.expect_download(timeout=10000) as dl:
                clicked = await safe_click(page, file_info["selector"], timeout=5000, force=True)
                if not clicked:
                    return None
            download = await dl.value
            temp_path = await download.path()
            if temp_path and Path(temp_path).exists():
                # Move to ~/Downloads/ with correct filename
                final_path = DOWNLOAD_DIR / filename
                shutil.copy2(temp_path, final_path)
                log(f"[OK] Direct download success: {final_path}")
                return str(final_path)
        except PlaywrightTimeout:
            pass
        except Exception as e:
            log(f"[WARN] Direct download failed: {e}")

    # Strategy 2: Click card to open preview, then click download button
    log(f"[DL] Trying preview panel download for {filename}")
    if await click_file_card(page, file_info):
        await asyncio.sleep(3.0)
        temp_path = await click_download_button_in_preview(page)
        if temp_path:
            final_path = DOWNLOAD_DIR / filename
            shutil.copy2(temp_path, final_path)
            log(f"[OK] Preview download success: {final_path}")
            return str(final_path)

    # Strategy 3: JS content extraction (fallback for text files)
    log(f"[DL] Trying JS content extraction for {filename}")
    if await click_file_card(page, file_info):
        await asyncio.sleep(3.0)
        try:
            content = await page.evaluate("""
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
                    if (!best) return null;
                    return best.innerText || best.textContent || null;
                })()
            """)
            if content and len(content) > 100:
                final_path = DOWNLOAD_DIR / filename
                final_path.write_text(content, encoding="utf-8")
                log(f"[OK] JS extraction success: {final_path} ({len(content)} chars)")
                return str(final_path)
        except Exception as e:
            log(f"[WARN] JS extraction failed: {e}")

    log(f"[FAIL] All strategies failed for {filename}")
    return None


async def run_downloader(url: str, visible: bool = False, max_files: int = 10) -> Dict[str, Any]:
    report = {
        "downloader_version": "3.6.1",
        "url": url,
        "mode": "visible" if visible else "headless",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "files_downloaded": [],
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

        files = await scan_files(page)
        if not files:
            log("[WARN] No files found")
            report["error"] = "No files found"
            return report

        files = files[:max_files]
        log(f"[MAIN] Processing {len(files)} files (max: {max_files})")

        for f in files:
            path = await download_file(page, f)
            if path:
                report["files_downloaded"].append({
                    "filename": f["filename"],
                    "ext": f["ext"],
                    "path": path,
                    "size": Path(path).stat().st_size if Path(path).exists() else 0,
                })
            else:
                report["files_downloaded"].append({
                    "filename": f["filename"],
                    "ext": f["ext"],
                    "path": None,
                    "error": "All download strategies failed",
                })

            await asyncio.sleep(1.0)

        success_count = sum(1 for f in report["files_downloaded"] if f.get("path"))
        report["summary"] = {
            "total_files": len(report["files_downloaded"]),
            "success_count": success_count,
            "failure_count": len(report["files_downloaded"]) - success_count,
            "success_rate": round(success_count / len(report["files_downloaded"]), 2) if report["files_downloaded"] else 0,
        }

        await context.close()
        return report


def save_and_print_report(report: Dict[str, Any]) -> None:
    report_path = DOWNLOAD_DIR / "kimi_download_report.json"
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[REPORT] Saved to: {report_path}")
    except Exception as e:
        print(f"\n[REPORT] Failed to save: {e}")

    print("\n" + "=" * 60)
    print("DOWNLOAD REPORT")
    print("=" * 60)
    print(f"Total: {report['summary'].get('total_files', 0)}")
    print(f"Success: {report['summary'].get('success_count', 0)}")
    print(f"Failure: {report['summary'].get('failure_count', 0)}")
    print(f"Rate: {report['summary'].get('success_rate', 0)}")
    print("=" * 60)

    for f in report.get("files_downloaded", []):
        if f.get("path"):
            size = f.get("size", 0)
            print(f"  [OK] {f['filename']} -> {f['path']} ({size} bytes)")
        else:
            print(f"  [FAIL] {f['filename']} - {f.get('error', 'Unknown error')}")


def main():
    parser = argparse.ArgumentParser(description="Kimi Downloader v3.6.1")
    parser.add_argument("--url", required=True, help="Kimi chat URL")
    parser.add_argument("--visible", action="store_true", help="Run in visible browser mode")
    parser.add_argument("--max-files", type=int, default=10, help="Max files to download")
    args = parser.parse_args()

    log(f"[MAIN] Starting downloader for {args.url}")
    log(f"[MAIN] Mode: {'visible' if args.visible else 'headless'}, max_files: {args.max_files}")

    report = asyncio.run(run_downloader(args.url, visible=args.visible, max_files=args.max_files))
    save_and_print_report(report)


if __name__ == "__main__":
    main()
