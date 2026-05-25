"""
Patch script to fix kimi_selector_probe.py v1.0.0 -> v1.0.1
Run: python3 fix_probe.py
"""
import sys
from pathlib import Path

target = Path("scripts/kimi_selector_probe.py")
if not target.exists():
    print("[ERROR] scripts/kimi_selector_probe.py not found. Run from project root.")
    sys.exit(1)

content = target.read_text()

# Check if already patched
if "launch_persistent_context" in content:
    print("[OK] File already patched (v1.0.1). No changes needed.")
    sys.exit(0)

# Replace the broken launch section
old_block = """        # Launch browser
        try:
            browser = await p.chromium.launch(
                headless=not visible,
                args=["--disable-blink-features=AutomationControlled"] if visible else []
            )
            log("MAIN", "Browser launched")
            report["phases"]["p0_env"] = {"browser_launch": True}
        except Exception as e:
            log("MAIN", f"FATAL: Browser launch failed: {e}")
            report["phases"]["p0_env"] = {"browser_launch": False, "error": str(e)}
            return report
        
        # Context with persistent profile if exists
        context_args = {}
        if PROFILE_DIR.exists():
            context_args["user_data_dir"] = str(PROFILE_DIR)
            log("MAIN", f"Using persistent profile: {PROFILE_DIR}")
        
        context = await browser.new_context(**context_args)
        page = await context.new_page()"""

new_block = """        # Launch browser with persistent profile if exists
        context = None
        browser = None
        try:
            if PROFILE_DIR.exists():
                log("MAIN", f"Using persistent profile: {PROFILE_DIR}")
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    headless=not visible,
                    args=["--disable-blink-features=AutomationControlled"] if visible else []
                )
                log("MAIN", "Persistent context launched")
                page = context.pages[0] if context.pages else await context.new_page()
            else:
                browser = await p.chromium.launch(
                    headless=not visible,
                    args=["--disable-blink-features=AutomationControlled"] if visible else []
                )
                log("MAIN", "Browser launched (no persistent profile)")
                context = await browser.new_context()
                page = await context.new_page()
            report["phases"]["p0_env"] = {"browser_launch": True}
        except Exception as e:
            log("MAIN", f"FATAL: Browser launch failed: {e}")
            report["phases"]["p0_env"] = {"browser_launch": False, "error": str(e)}
            return report"""

if old_block not in content:
    print("[ERROR] Could not find the broken code block to patch.")
    sys.exit(1)

content = content.replace(old_block, new_block)

# Also fix the close section
old_close = "        await browser.close()"
new_close = """        if context:
            await context.close()
            log("MAIN", "Context closed")
        if browser:
            await browser.close()
            log("MAIN", "Browser closed")"""

if old_close in content:
    content = content.replace(old_close, new_close)

target.write_text(content)
print("[OK] scripts/kimi_selector_probe.py patched to v1.0.1")
print("[INFO] Run: python3 scripts/kimi_selector_probe.py --url ... --visible")