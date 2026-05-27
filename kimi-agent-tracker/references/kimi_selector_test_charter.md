---
title: "Kimi Selector Test Charter v2.0"
name: kimi-agent-tracker
description: "Standardized probe charter for reverse-engineering Kimi chat page selectors. Covers file card detection, preview panel diagnosis, content extraction, and download button discovery. Based on v1.0.0-v1.0.8 probe evolution and v3.5-v3.6.1 downloader fixes."
version: "2.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-26T01:45:00+08:00"
auth_config:
  provider: "none"
  auth_method: "none"
  token_env_var: "none"
  env_file_path: "none"
file_mapping:
  local_path: "references/kimi_selector_test_charter.md"
  github_path: "kimi-agent-tracker/references/kimi_selector_test_charter.md"
---

# Kimi Selector Test Charter v2.0

## 1. Purpose

This charter defines the standard procedure for reverse-engineering file download selectors on kimi.com chat pages. It is designed to be executed by any Playwright-based probe script when encountering a new or updated Kimi UI version.

**When to use this charter:**
- `kimi_downloader.py` fails to detect files on a conversation page.
- `kimi_downloader.py` detects files but cannot extract content or trigger downloads.
- Kimi website UI updates and existing selectors become stale.
- Adding support for a new file type not previously tested.

## 2. Phase Gate Structure

| Phase | Gate Name | Pass Criteria | Max Duration |
|-------|-----------|---------------|--------------|
| P0 | Environment | Browser launches, page loads, no navigation timeout | 2 min |
| P1 | File Scan | Detects >= 1 file card with valid filename | 1 min |
| P2 | Click Verify | Clicking file card changes page state (preview opens) | 2 min |
| P3 | Content Extract | Successfully extracts > 100 chars of file content | 2 min |
| P4 | Download Trigger | Successfully triggers browser download or saves content | 2 min |
| P5 | Stability | Same strategy works 3/3 times with < 5% length variance | 5 min |

**Abort condition:** If any phase fails after all strategies exhausted, STOP and report to user with screenshots and DOM diagnosis JSON.

## 3. Phase 0: Environment Verification

### 3.1 Browser Launch
- Verify Playwright Chromium is installed: `python3 -m playwright install chromium`
- Use persistent profile if available: `~/.kimi_auth/browser_profile_chromium/`
- Launch in visible mode for initial diagnosis: `headless=False`

### 3.2 Navigation (CRITICAL: Anti-Pattern W-06)
- **WRONG:** `page.goto(url, wait_until="networkidle")`
- **RIGHT:** `page.goto(url, wait_until="domcontentloaded")` then `asyncio.sleep(5.0)`
- **Reason:** Kimi uses WebSocket heartbeat. `networkidle` never fires.

### 3.3 Dynamic Content Wait
- After `domcontentloaded`, wait minimum 5 seconds for React/Vue hydration.
- If file cards not found after 5s, wait additional 5s (lazy loading).
- Log current URL and page title for verification.

## 4. Phase 1: File Card Detection

### 4.1 Selector Strategy (Anti-Pattern W-01, W-02)
- **WRONG:** Assume semantic class names like `file-card-info-name`.
- **RIGHT:** Use broad attribute selectors, then filter by text content.

**Candidate selectors (try in order until match):**
```
div[class*="file-card-container"]
div[class*="file-card"]
div[data-v-][class*="file"]
div[class*="file-item"]
div[class*="attachment"]
a[class*="file"]
div[data-v-]          # Vue scoped style fallback
```

### 4.2 Filename Extraction (Anti-Pattern W-01)
- **WRONG:** `card.query_selector('.file-name').text_content()`
- **RIGHT:** Read `card.text_content()`, apply regex:
  ```python
  re.search(r'([A-Za-z0-9_.-]+[.](py|md|json|zip|env|txt|csv|yaml|yml|js|html|css|xml))', text, re.I)
  ```
- **Filter:** Skip elements where extracted "filename" is just an extension label (length <= 4 and uppercase in {"MD","PY","JSON","ZIP"}).

### 4.3 Gate Criteria
- PASS: >= 1 file card detected with valid filename and extension.
- FAIL: 0 files after all selectors exhausted.
- **Action on FAIL:** Take full-page screenshot. Check if conversation actually contains file attachments. If yes, report "Selector miss" and proceed to manual DOM inspection.

## 5. Phase 2: Click Verification

### 5.1 Multi-Method Click (Anti-Pattern W-04)
Execute click methods in strict order until one succeeds:

| Order | Method | Code | When to use |
|-------|--------|------|-------------|
| 1 | Playwright force click | `el.click(force=True)` | Default. Bypasses pointer-events interception. |
| 2 | Playwright normal click | `el.click()` | If force click triggers wrong element. |
| 3 | JS dispatchEvent | `el.dispatchEvent(new MouseEvent('click', {bubbles:true}))` | If Playwright click fails due to synthetic event system. |
| 4 | Double click | `el.dblclick(force=True)` | If app requires desktop-like double-click to open. |
| 5 | Child anchor click | Click `<a>` inside card | If card is container and actual link is child element. |

### 5.2 State Verification
After click, wait 3-10 seconds, then verify page state changed:
- **Screenshot comparison:** Before/after screenshots must show visual difference.
- **DOM diagnosis:** Run deep diagnosis to detect new elements (preview panel, modal, drawer).
- **URL change:** Some SPAs update hash or query params on preview open.

### 5.3 Gate Criteria
- PASS: Page state visibly changes after click (preview panel appears, modal opens, or URL updates).
- FAIL: All 5 click methods executed, no state change after 10s wait.
- **Action on FAIL:** Report "Click fail". Check if element is actually clickable (not just decorative). Try clicking at coordinates instead of element reference.

## 6. Phase 3: Content Extraction

### 6.1 Diagnosis First (Anti-Pattern W-03)
Before attempting extraction, run deep DOM diagnosis:

```javascript
// Execute in page context
(() => {
    const result = {
        iframe_count: document.querySelectorAll('iframe').length,
        shadow_hosts: [],
        right_side_elements: [],
        top_right_elements: [],
        has_monaco: !!window.monaco,
    };

    // Detect shadow DOM
    document.querySelectorAll('*').forEach(el => {
        if (el.shadowRoot) result.shadow_hosts.push(el.tagName);
    });

    // Detect right-side large elements (preview panel candidates)
    document.querySelectorAll('*').forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width > 500 && rect.left > window.innerWidth * 0.45 && rect.height > 300) {
            result.right_side_elements.push({
                tag: el.tagName, class: el.className.substring(0,100),
                width: rect.width, height: rect.height,
                left: rect.left, top: rect.top
            });
        }
    });

    // Detect top-right small elements (icon buttons)
    document.querySelectorAll('*').forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width < 60 && rect.height < 60 && rect.left > window.innerWidth * 0.8 && rect.top < 100) {
            result.top_right_elements.push({
                tag: el.tagName, class: el.className.substring(0,100),
                title: el.getAttribute('title'), aria_label: el.getAttribute('aria-label')
            });
        }
    });

    return result;
})()
```

### 6.2 Extraction Strategy Matrix

Based on diagnosis results, choose strategy:

| Condition | Primary Strategy | Fallback |
|-----------|-----------------|----------|
| `window.monaco` exists | `monaco.editor.getEditors()[0].getValue()` | `monaco.editor.getModels()[0].getValue()` |
| No monaco, right-side element found | Bounding box `innerText` extraction | `innerHTML` then strip tags |
| iframe detected | Run diagnosis in each iframe | Extract from correct frame |
| Shadow DOM detected | Query inside `shadowRoot` | Use slot content or host element |
| Content < 100 chars | Suspect virtual scrolling | Try copy-to-clipboard button |

### 6.3 Bounding Box Content Extraction (Proven Pattern)
When class names are unknown:

```python
content = await page.evaluate("""
    (() => {
        let best = null, bestArea = 0;
        document.querySelectorAll('*').forEach(el => {
            const rect = el.getBoundingClientRect();
            const area = rect.width * rect.height;
            if (rect.left > window.innerWidth * 0.45 && area > bestArea 
                && rect.width > 400 && rect.height > 300) {
                best = el;
                bestArea = area;
            }
        });
        return best ? (best.innerText || best.textContent || null) : null;
    })()
""")
```

### 6.4 Gate Criteria
- PASS: Extracted content length > 100 chars for code files, > 50 chars for config files.
- FAIL: Content too short or null after all strategies.
- **Action on FAIL:** Check for canvas-based rendering. If Monaco present but content short, virtual scrolling is active. Use copy button or API injection.

## 7. Phase 4: Download Trigger

### 7.1 File-Type Strategy

| Type | Strategy | Notes |
|------|----------|-------|
| .py / .json / .zip | Direct download via `expect_download` after clicking card | Most reliable for binary/text files |
| .md | Preview panel -> click download icon -> select Markdown format | Three-step flow required |
| .env / .txt | Direct download or JS extraction | Treat as text files |

### 7.2 Download Button Discovery (Anti-Pattern W-08)
- **WRONG:** `button[class*="download"]` — icon may be `<svg>` with no semantic class.
- **RIGHT:** Bounding box scan of top-right corner:
  ```python
  buttons = await page.query_selector_all('button, svg, [class*="icon"]')
  for btn in buttons:
      box = await btn.bounding_box()
      if box and box["x"] > 800 and box["y"] < 100 and box["width"] < 60:
          await btn.click(force=True)
  ```

### 7.3 Download Capture (Anti-Pattern W-07)
- **WRONG:** Assume file saves to `~/Downloads/`.
- **RIGHT:** Playwright returns temp UUID path. Must copy to target directory:
  ```python
  temp_path = await download.path()
  final_path = Path.home() / "Downloads" / filename
  shutil.copy2(temp_path, final_path)
  ```

### 7.4 sandbox:// Protocol (Anti-Pattern W-07)
- If download URL starts with `sandbox://`, `expect_download` will timeout.
- Use global `page.on("download", handler)` instead of `expect_download` context manager.

### 7.5 Gate Criteria
- PASS: File saved to target directory with correct filename and non-zero size.
- FAIL: Download not triggered or file not found after 15s.

## 8. Phase 5: Stability Verification

### 8.1 Repeatability Test
- Run the same successful strategy 3 times on the same conversation.
- All 3 runs must PASS.
- Content length variance must be < 5%.

### 8.2 Multi-Type Coverage
- Test at least 2 files per type: .py, .md, .json, .zip.
- Log per-type success rate.

### 8.3 Gate Criteria
- PASS: 3/3 success, variance < 5%, all target types covered.
- FAIL: Intermittent success or high variance.
- **Action on FAIL:** Strategy is not stable. Look for timing-dependent behavior. Add longer waits or retry logic.

## 9. Failure Decision Tree

```
File scan returns 0?
├── YES -> Check broader selectors (div[data-v-], a[class*="file"])
│   └── Still 0? -> Screenshot + manual DOM inspection
└── NO -> File cards found
    Click has no effect?
    ├── YES -> Try all 5 click methods (force, normal, JS, dblclick, child)
    │   └── Still no effect? -> Check if element is decorative (no event listener)
    └── NO -> Preview opens
        Content extraction returns null/short?
        ├── YES -> Check for iframe/Shadow DOM/Canvas/Monaco virtual scroll
        │   └── Run deep diagnosis
        └── NO -> Content extracted
            Download not triggered?
            ├── YES -> Try top-right bounding box scan for download icon
            │   └── Still no? -> Use global download listener + manual trigger
            └── NO -> Download success
                File not in ~/Downloads/?
                ├── YES -> shutil.copy2 from Playwright temp path
                └── NO -> COMPLETE
```

## 10. Output Format

Probe must output JSON report with this structure:

```json
{
  "probe_version": "1.0.x",
  "url": "https://www.kimi.com/chat/...",
  "timestamp": "2026-05-26T...",
  "phases": {
    "p0_environment": {"passed": true, "duration_ms": 1200},
    "p1_file_scan": {"passed": true, "files_found": 11, "selector_used": "..."},
    "p2_click_verify": {"passed": true, "method_used": "force_click"},
    "p3_content_extract": {"passed": true, "strategy": "bounding_box_innerText", "length": 1669},
    "p4_download_trigger": {"passed": true, "path": "/Users/.../Downloads/file.py"},
    "p5_stability": {"passed": true, "success_rate": 1.0}
  },
  "per_file_results": [...],
  "diagnosis": {
    "iframe_count": 0,
    "shadow_host_count": 0,
    "right_side_elements": [...],
    "top_right_elements": [...],
    "has_window_monaco": false
  }
}
```

## 11. Integration with Downloader

Once probe passes all 5 phases, update `kimi_downloader.py`:

1. Update `FILE_CARD_SELECTORS` list with working selector.
2. Update click method priority based on which method passed P2.
3. Update content extraction strategy based on which strategy passed P3.
4. Update download button discovery based on P4 results.
5. Increment downloader version in docstring and frontmatter.

## 12. Version History

| Charter Version | Date | Changes |
|-----------------|------|---------|
| v1.0.0 | 2026-05-25 | Initial 4-phase charter with basic selector strategies |
| v2.0.0 | 2026-05-26 | Added P5 Stability, failure decision tree, anti-patterns W-01~W-08, bounding box patterns, multi-method click matrix, sandbox protocol warning |

## 13. References

- `assets/WEB.CORRECTIONS.md` — Full anti-pattern catalog with error records.
- `scripts/kimi_selector_probe.py` — Reference implementation of this charter.
- `scripts/kimi_downloader.py` — Production downloader using proven strategies.
