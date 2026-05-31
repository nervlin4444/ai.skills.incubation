---
title: "Web Browser Automation Correction Checklist"
name: agent-skill-improving
description: "Reverse engineering checklist for browser automation. v1.1.0 adds: HTTP header as file integrity anchor, sandbox-to-TOS redirect chain, panel-scoped selectors, Vue DOM destruction after preview close, download button as sole reliable download method."
version: "v1.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-06-01T02:30:00+08:00"
fixes: [9, 10, 11, 12, 13, 14]
auth_config:
  provider: "none"
  auth_method: "none"
  token_env_var: "none"
  env_file_path: "none"
file_mapping:
  local_path: "assets/WEB.CORRECTIONS.md"
  github_path: "agent-skill-improving/assets/WEB.CORRECTIONS.md"
---

# Web Browser Automation Correction Checklist

## Trigger Table

| Trigger | Condition | Action |
|---------|-----------|--------|
| SEL.MISS | Selector returns 0 elements / wrong elements / stale elements | Run "Selector Miss Checklist" |
| CLICK.FAIL | Click executes but page state unchanged / preview not opened / download not triggered | Run "Click Fail Checklist" |
| DOM.GHOST | Screenshot shows element exists but querySelectorAll returns nothing | Run "DOM Ghost Checklist" |
| NET.STUCK | Page.goto timeout / networkidle never fires / WebSocket keeps connection alive | Run "Network Stuck Checklist" |
| DL.LOST | Download captured but file missing / saved to wrong path / temp file not moved | Run "Download Lost Checklist" |
| DL.HTTP | Downloaded file size wrong / all files same size / Content-Length mismatch / ETag missing | Run "HTTP Header Integrity Checklist" |

## Selector Miss Checklist

Condition: Fixed class-name selectors fail on modern web apps (Vue/React/Angular scoped styles).

- [ ] **Class name guessing**: Using hardcoded class names like `file-card-info-name` or `preview-panel`?
  - Prohibit: Assume class names are semantic and stable.
  - Must: Treat class names as implementation detail. Modern frameworks use scoped hashes (e.g. `data-v-8ff6ac77`) or minified names.
  - Check: Run `document.querySelectorAll('*')` and inspect actual class names before writing selectors.
  - Case: `div[class*="file-card-info-name"]` returned 0 on Kimi because actual class was `file-card-info__name` (BEM) or scoped hash.

- [ ] **Attribute selector over-specificity**: Using `div[class*="xxx"]` when element is `span` or `a`?
  - Prohibit: Hardcode tag name in selector without verification.
  - Must: Use `*[class*="xxx"]` or verify tag name via JS diagnosis first.
  - Check: Log `el.tagName` for matched elements.

- [ ] **nth-of-type drift**: Using `:nth-of-type(N)` after filtering out non-matching elements?
  - Prohibit: Assume index stability after filtering.
  - Must: `nth-of-type` counts all siblings of same tag. If you skip element 2, element 3 is still `:nth-of-type(3)`, not `:nth-of-type(2)`.
  - Check: Use `nth-child` or re-query after each click, or use unique identifiers (data attributes, href).

- [ ] **Text-based extraction**: Relying on child element selectors to extract filenames?
  - Prohibit: `card.querySelector('.file-name').textContent` — child selector may not exist.
  - Must: Read `card.textContent` directly, then apply regex to extract filename pattern.
  - Check: Regex should match `[A-Za-z0-9_.-]+[.](py|md|json|zip|...)` against full card text.
  - Case: Kimi file cards had filename embedded in plain text, not in dedicated child element with semantic class.

## Click Fail Checklist

Condition: Click returns true but page state unchanged (preview panel not opened, download not triggered).

- [ ] **Pointer-events interception**: Element has `pointer-events: none` with child handling events?
  - Prohibit: `el.click()` on parent element.
  - Must: Use `force=True` (Playwright) or click the actual event-target child element.
  - Check: If `force=True` fails, try clicking child `<a>` or `<button>` inside the card.
  - Case: Kimi file card click worked with `force=True` but not with normal click.

- [ ] **JS dispatch fallback**: Playwright click works at DOM level but app uses synthetic event system?
  - Prohibit: Only rely on Playwright's built-in click.
  - Must: Implement JS fallback: `el.dispatchEvent(new MouseEvent('click', {bubbles: true}))`.
  - Check: If Playwright click fails, try JS dispatch. Log which method succeeded.

- [ ] **Double-click requirement**: App requires double-click to open preview (desktop-like behavior)?
  - Prohibit: Assume single-click opens everything.
  - Must: Test `dblclick()` if single click shows no state change after 3-second wait.
  - Check: Screenshot before/after click to confirm state change.

- [ ] **Async rendering delay**: Clicking before React/Vue finishes rendering interactive elements?
  - Prohibit: Click immediately after DOM loaded.
  - Must: Wait at least 5 seconds after `domcontentloaded` for dynamic content, then 3-10 seconds after click for preview panel animation.
  - Check: Add explicit `await asyncio.sleep(N)` between steps, do not rely solely on `wait_for_selector`.

## DOM Ghost Checklist

Condition: Screenshot clearly shows element exists, but `document.querySelectorAll('*')` returns nothing for that region.

- [ ] **iframe isolation**: Element inside `<iframe>`?
  - Prohibit: Scan only `page.main_frame`.
  - Must: Iterate `page.frames`, run diagnosis in each frame.
  - Check: Log `len(page.frames)` and `frame.url` for each frame.
  - Case: Monaco Editor sometimes loads in iframe on some sites.

- [ ] **Shadow DOM encapsulation**: Element inside Web Component `shadowRoot`?
  - Prohibit: `document.querySelectorAll('*')` — does not pierce shadow DOM.
  - Must: Search for elements with `.shadowRoot` property, then query inside `shadowRoot`.
  - Check: JS diagnosis should include `el.shadowRoot` detection.

- [ ] **Canvas/WebGL rendering**: Element drawn on canvas, not DOM node?
  - Prohibit: Try to extract text from canvas-based editor.
  - Must: Detect `<canvas>` presence, switch to screenshot/OCR or API-based extraction.
  - Check: If `monaco-editor` is canvas-based, `innerText` will be empty. Must use `window.monaco.editor.getValue()`.

- [ ] **Virtual scrolling (Monaco)**: Editor only renders visible lines, `innerText` returns 32 chars?
  - Prohibit: Read `pre.innerText` or `code.innerText` expecting full file content.
  - Must: Use editor-specific API (`window.monaco.editor.getEditors()[0].getValue()`) or copy-to-clipboard button.
  - Check: If content length is suspiciously small (< 100 chars) for a code file, suspect virtual scrolling.
  - Case: Kimi "preview extraction" returned exactly 32 chars for all .py files — Monaco virtual scrolling.

- [ ] **Bounding box discovery**: When class names fail, use geometry to locate elements.
  - Prohibit: Give up when selectors return 0.
  - Must: Use `getBoundingClientRect()` to find elements by position and size.
  - Check: Preview panels are typically large (width > 500) and on the right side (left > 45% viewport).
  - Check: Download/copy buttons are typically small (width < 60) and in top-right corner (left > 80%, top < 100).

## Network Stuck Checklist

Condition: `page.goto()` timeout or `networkidle` never resolves.

- [ ] **networkidle trap**: Site has WebSocket heartbeat or long-polling keeping connections open?
  - Prohibit: Use `wait_until="networkidle"` for all sites.
  - Must: Use `wait_until="domcontentloaded"` for SPAs with persistent connections, then manual sleep.
  - Check: If navigation timeout at 60000ms with "waiting until networkidle", switch to domcontentloaded.
  - Case: Kimi chat page has WebSocket heartbeat, networkidle impossible.

- [ ] **SPA hydration delay**: DOM loaded but React/Vue/Angular not yet hydrated interactive elements?
  - Prohibit: Assume elements are interactive immediately after domcontentloaded.
  - Must: Add 3-5 second sleep after domcontentloaded before querying elements.
  - Check: If file cards are not found immediately after load, increase sleep duration.

- [ ] **Lazy loading**: File list loaded via IntersectionObserver or scroll-triggered fetch?
  - Prohibit: Query file list immediately on page load.
  - Must: Scroll to bottom of page to trigger lazy load, then query.
  - Check: If file count increases after scroll, implement scroll-then-scan pattern.

## Download Lost Checklist

Condition: Download event captured but file missing, wrong path, or wrong filename.

- [ ] **Playwright temp directory**: `download.path()` returns `/var/folders/.../playwright-artifacts-.../uuid`?
  - Prohibit: Assume download saves to browser default download folder.
  - Must: Playwright downloads to temporary directory. Must `shutil.copy2(temp_path, target_path)` to move file.
  - Check: Verify final file exists in `~/Downloads/` with correct filename, not just temp UUID path.
  - Case: v3.6.0 files saved to temp dir; v3.6.1 fixed with explicit `shutil.copy2` to `~/Downloads/filename`.

- [ ] **sandbox:// protocol → TOS redirect chain (v1.1.0 updated)**: Download link uses `sandbox:///mnt/agents/output/...`?
  - Prohibit: Use `expect_download` on `sandbox://` links directly, or `head_pre_check()` with `urllib.request` on sandbox URLs.
  - Must: Click the file element to open preview panel → click Download button → browser follows 307 redirect to TOS URL. `expect_download()` captures from the browser's native download event.
  - Must: Real HTTP headers (Content-Length, ETag, Last-Modified) are on the final TOS response, not the sandbox link.
  - Check: If URL starts with `sandbox://`, head_pre_check will fail. Use Download button path instead.
  - Case: `sandbox://` URLs parsed by urllib as `unknown url type`. Real file is at `https://prod-chat-kimi.tos-cn-beijing.volces.com/...` behind a 307 redirect from Kimi's sign-obj API.

- [ ] **Format selection dialog**: .md files trigger "Save as PDF/Word/Markdown" dialog?
  - Prohibit: Expect immediate download for .md files.
  - Must: Implement three-step flow: (1) click file to open preview, (2) click download icon, (3) select Markdown format from dialog.
  - Check: Screenshot after clicking download icon to confirm dialog appearance.

- [ ] **Incomplete download filtering**: Scanning download directory includes `.crdownload`, `.opdownload`, `.part`?
  - Prohibit: Treat temp download files as completed files.
  - Must: Filter out incomplete download suffixes when scanning or processing downloaded files.
  - Check: Skip files ending with `.crdownload` (Chrome), `.opdownload` (Opera), `.part` (Firefox), `.tmp`.

## HTTP Header Integrity Checklist (v1.1.0 NEW)

Condition: Downloaded files all have identical size (e.g. 1186 chars), Content-Length header missing, or file content clearly truncated.

**Core principle: HTTP headers are the ONLY authoritative source of file integrity. Never trust `innerText` extraction alone.**

- [ ] **innerText extraction is NOT a download**: Using `page.evaluate('code.innerText')` to capture file content?
  - Prohibit: Relying on `innerText` / `textContent` extraction as primary download method.
  - Must: Click the Download button and capture via browser's native download event (`expect_download()`).
  - Reason: innerText extraction captures only the VISIBLE portion of the preview panel, not the full file. Lazy-loaded panels render 1186 chars (frontmatter only).
  - Case: kimi_downloader v5.1.3 extracted all files as 1186 chars. Switched to Download button + expect_download → full 11826 chars.

- [ ] **Sandbox URL to TOS redirect chain**: File URL starts with `sandbox:///mnt/agents/output/...`?
  - Prohibit: Trying `head_pre_check()` with `urllib.request` on `sandbox://` URLs (fails with `unknown url type`).
  - Must: Follow the redirect chain: click file → preview panel → click Download button → browser fetches `https://www.kimi.com/apiv2-files/sign-obj/...` (307) → redirects to `https://prod-chat-kimi.tos-cn-beijing.volces.com/...` (real file).
  - Must: Capture HTTP response headers from the final TOS response — this is where `Content-Length`, `ETag`, `Last-Modified` live.
  - Case: Kimi sandbox files cannot be HTTP HEAD'd directly. The Download button triggers a signed URL → 307 → TOS URL chain. Only TOS response has real headers.

- [ ] **Content-Length vs actual file size**: After download, does `os.path.getsize(file) == int(Content-Length)`?
  - Prohibit: Mark file as `success` without verifying Content-Length matches actual size.
  - Must: `actual_size == expected_size` → `size_verified: true`. Mismatch → `size_mismatch`.
  - Check: All files in batch_report should have `size_verified: true` for success status.
  - Case: 5 files reported as "downloaded" at 1186 chars. Content-Length said 11826. Actual check revealed every file was truncated.

- [ ] **ETag as dedup key**: Does download_state.json store ETag per file?
  - Must: Every downloaded file record stores `etag`, `content_length`, `last_modified`, `content_type`, `http_url`.
  - Must: Before re-downloading, check `download_state.json` for same `filename + etag` → skip.
  - Benefit: ETag unchanged = file unchanged → skip download entirely, no browser needed.
  - Case: Cycle 6 of kimi daemon completed in 0.4s (ETag skip) vs 63s (full download).

- [ ] **Per-file handler for response headers**: Using `page.on("response")` to capture headers?
  - Prohibit: Global handler that captures ALL responses for the entire batch.
  - Must: Create fresh handler per file with `page.on("response", hdr)`, remove with `page.remove_listener()` in `finally` block.
  - Case: Global handler missed 2/3 files because events interleaved between downloads and handler was not scoped to current file.

- [ ] **Scope querySelector to panel, not document**: Using `document.querySelector('pre code')` to extract preview content?
  - Prohibit: `document.querySelector()` — Kimi chat page has 109 `pre code` elements (chat history code blocks). First match is NOT the preview panel.
  - Must: `document.querySelector('div.side-console-container pre code')` — scope to preview panel FIRST.
  - Check: If extracted content length < 2000 chars for a >10KB file, suspect wrong selector scope.
  - Case: Page-wide `querySelector('pre code')` returned 1186 chars (chat history code block). Panel-scoped `div.side-console-container pre code` returned 11826 chars (full file).

## Vue DOM Destruction After Preview Close (v1.1.0 NEW)

- [ ] **Links disappear after preview close**: Clicking file 2 fails with "click returned null"?
  - Root cause: Kimi is a Vue SPA. After closing the preview panel, Vue re-renders the DOM. ALL `<a>` tags with `.py` filenames are **removed** and replaced with plain text.
  - Pre-close: 15 `<a>` links with `sandbox://` hrefs.
  - Post-close: 0 `<a>` links. Only `<span>` text nodes remain.
  - Must: Reload the page (`page.goto(url)`) before each file download to restore DOM links.
  - Must: Reload time is ~3s per file — acceptable cost for 100% click reliability.
  - Evidence: kimi_click_why_probe.py captured DOM state before/after close. 15→0 links confirmed.

## Proven Patterns (from kimi_downloader v3.6.1)

### Pattern 1: File Card Scanning
```python
# Do NOT use child element selectors for filenames
# Do NOT assume semantic class names

cards = await page.query_selector_all('div[class*="file-card"]')  # broad match
for card in cards:
    full_text = await card.text_content()  # read ALL text
    match = re.search(r'([A-Za-z0-9_.-]+[.](py|md|json|zip))', full_text, re.I)
    if match:
        filename = match.group(1)  # extract from text, not DOM structure
```

### Pattern 2: Preview Panel Content Extraction (when Monaco absent)
```python
# When window.monaco does not exist, use bounding box discovery
content = await page.evaluate("""
    (() => {
        let best = null, bestArea = 0;
        document.querySelectorAll('*').forEach(el => {
            const rect = el.getBoundingClientRect();
            const area = rect.width * rect.height;
            // Preview panel: large, on right side
            if (rect.left > window.innerWidth * 0.45 && area > bestArea 
                && rect.width > 400 && rect.height > 300) {
                best = el;
                bestArea = area;
            }
        });
        return best ? (best.innerText || best.textContent) : null;
    })()
""")
```

### Pattern 3: Top-Right Button Discovery
```python
# Download/Copy buttons are small icons in top-right corner
buttons = await page.query_selector_all('button, svg, [class*="icon"]')
for btn in buttons:
    box = await btn.bounding_box()
    if box and box["x"] > 800 and box["y"] < 100 and box["width"] < 60:
        await btn.click(force=True)  # likely download or copy button
```

### Pattern 4: Multi-Method Click with Fallback
```python
click_methods = [
    lambda: safe_click(page, selector, force=True),   # Playwright force
    lambda: safe_click(page, selector, force=False),  # Playwright normal
    lambda: js_click(page, selector),                 # JS dispatchEvent
    lambda: double_click(page, selector),             # dblclick
    lambda: safe_click(page, f'{selector} a', force=True),  # child anchor
]
for method in click_methods:
    if await method():
        break  # stop at first success
```

### Pattern 5: Navigation State Machine
```python
# Do NOT use networkidle for SPAs with persistent connections
await page.goto(url, wait_until="domcontentloaded", timeout=60000)
await asyncio.sleep(5.0)  # wait for SPA hydration
# Now safe to query dynamic elements
```

## Error Records Archive

| ID | Date | Trigger | Summary | Status |
|----|------|---------|---------|--------|
| W-01 | 2026-05-25 | SEL.MISS | `div[class*="file-card-info-name"]` returned 0 because Kimi uses scoped Vue classes, not semantic BEM | Resolved via text_content + regex |
| W-02 | 2026-05-25 | SEL.MISS | `div[class*="preview-panel"]` returned 0 because actual class was `language-py` / `markdown` | Resolved via bounding box discovery |
| W-03 | 2026-05-25 | DOM.GHOST | `document.querySelectorAll('*')` found 0 preview elements because they were not in iframe/Shadow DOM — simply had unexpected class names | Resolved via deep_diagnose() |
| W-04 | 2026-05-25 | CLICK.FAIL | Single click on file card did not open preview; needed force=True or JS dispatch | Resolved via multi-method click |
| W-05 | 2026-05-25 | DOM.GHOST | Monaco Editor `innerText` returned 32 chars due to virtual scrolling | Resolved via window.monaco.editor.getValue() (but Kimi has no monaco, so used bounding box innerText instead) |
| W-06 | 2026-05-25 | NET.STUCK | `page.goto` timeout at 60000ms with networkidle because Kimi WebSocket heartbeat keeps connection alive | Resolved via domcontentloaded + manual sleep |
| W-07 | 2026-05-25 | DL.LOST | Downloaded files saved to `/var/folders/.../playwright-artifacts-.../uuid` instead of ~/Downloads/ | Resolved via shutil.copy2 to target dir |
| W-08 | 2026-05-25 | SEL.MISS | Download button selectors (button[class*="download"]) failed because icon was `<svg>` with no semantic class | Resolved via top-right bounding box scan |
| W-09 | 2026-06-01 | DL.HTTP | All 5 files downloaded with identical size 1186 chars. Root cause: `innerText` extraction from preview panel only captured frontmatter. Fix: switched to Download button + `expect_download()`, now gets full 11826 chars. | Resolved |
| W-10 | 2026-06-01 | DL.HTTP | `head_pre_check()` returned `unknown url type: sandbox` for all Kimi file links. Root cause: file links are `sandbox://` protocol, not HTTP. Fix: follow Download button → 307 redirect → TOS URL chain to get real headers. | Resolved |
| W-11 | 2026-06-01 | SEL.MISS | `document.querySelector('pre code')` returned 1186 chars (first match in chat history), not preview panel content. Root cause: Kimi chat page has 109 `pre code` elements. Fix: scope to `div.side-console-container pre code`. | Resolved |
| W-12 | 2026-06-01 | CLICK.FAIL | Files 2+3 click returned null after file 1 download. Root cause: Vue SPA re-renders DOM after preview close, removes ALL `<a>` tags (15→0). Fix: `page.goto(url)` reload between files. | Resolved |
| W-13 | 2026-06-01 | DL.HTTP | `page.on("response")` global handler missed headers for 2/3 files. Root cause: handler attached once for batch, events interleaved. Fix: per-file handler with `finally: page.remove_listener()`. | Resolved |
| W-14 | 2026-06-01 | DL.HTTP | `head_pre_check()` SSL verification failed on TOS URL (`SSL: CERTIFICATE_VERIFY_FAILED`). Root cause: Volces TOS uses self-signed cert. Fix: `ssl._create_unverified_context()`. | Resolved |

---
*Last updated: 2026-06-01*
*This file is LLM execution instruction set, human-readable explanation see README.md*
