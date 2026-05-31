
"""
---
title: "Kimi Conversation Lister"
name: "kimi-agent-tracker"
description: "Extracts conversation list from Kimi platform using Playwright persistent profile. Outputs standardized JSON for downstream download automation. Integrates with core_path_utils and core_logger."
version: "5.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-28T08:55:00Z"
auth_config:
  provider: "kimi"
  auth_method: "persistent_browser_profile"
  token_env_var: "KIMI_AUTH_TOKEN"
  env_file_path: "~/.kimi_auth/.env"
file_mapping:
  local_path: "{baseDir}/scripts/kimi_conversation_lister.py"
  github_path: "kimi-agent-tracker/scripts/kimi_conversation_lister.py"
---
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# =============================================================================
# Core Module Integration (with fallback)
# =============================================================================
CORE_AVAILABLE = False
try:
    _SCRIPT_DIR = Path(__file__).parent.resolve()
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    from core_path_utils import get_skill_paths, ensure_dir
    from core_logger import get_logger, LogLevel
    CORE_AVAILABLE = True
except Exception:
    pass


class SimpleLogger:
    """Fallback logger when core_logger is unavailable."""

    def __init__(self, name: str, log_dir: Optional[Path] = None) -> None:
        self.name = name

    def info(self, msg: str) -> None:
        print(f"[INFO] [{self.name}] {msg}", flush=True)

    def debug(self, msg: str) -> None:
        print(f"[DEBUG] [{self.name}] {msg}", flush=True)

    def warning(self, msg: str) -> None:
        print(f"[WARN] [{self.name}] {msg}", flush=True)

    def error(self, msg: str) -> None:
        print(f"[ERROR] [{self.name}] {msg}", flush=True)


class SimplePathUtils:
    """Fallback path utilities when core_path_utils is unavailable."""

    @staticmethod
    def get_skill_paths(skill_name: str) -> Dict[str, Path]:
        home = Path.home()
        base = home / ".workbuddy" / "skills" / skill_name
        return {
            "scripts": base / "scripts",
            "data": base / "data",
            "logs": base / "logs",
            "config": base / "config",
            "state": base / "state",
        }

    @staticmethod
    def ensure_dir(path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path


# =============================================================================
# Conversation Lister
# =============================================================================
class ConversationLister:
    """Extracts Kimi conversation metadata using Playwright persistent profile."""

    def __init__(
        self,
        profile_dir: Optional[Path] = None,
        headless: bool = True,
    ) -> None:
        self.headless = headless
        self.profile_dir = (
            profile_dir
            or Path.home() / ".kimi_auth" / "browser_profile_chromium"
        )

        # Initialize core modules or fallback
        if CORE_AVAILABLE:
            self.paths = get_skill_paths("kimi-agent-tracker")
            self.logger = get_logger("conversation_lister", self.paths["logs"])
        else:
            self.paths = SimplePathUtils.get_skill_paths("kimi-agent-tracker")
            self.logger = SimpleLogger("conversation_lister")
            self.logger.warning(
                "Core modules not found. Using fallback implementations."
            )

        # Ensure output directories exist
        SimplePathUtils.ensure_dir(self.paths["data"])
        SimplePathUtils.ensure_dir(self.paths["logs"])
        SimplePathUtils.ensure_dir(self.paths["state"])

    async def extract_conversations(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Extract conversation list from Kimi platform."""
        conversations: List[Dict[str, Any]] = []

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )

            page = browser.pages[0] if browser.pages else await browser.new_page()

            try:
                self.logger.info("Navigating to Kimi conversation list...")
                await page.goto(
                    "https://kimi.moonshot.cn/",
                    wait_until="domcontentloaded",
                )

                # CRITICAL FIX v5.0.0: networkidle -> domcontentloaded
                # Reduces wait time by ~60-80% compared to networkidle
                await page.wait_for_load_state("domcontentloaded")

                # Wait for conversation list container to appear
                await page.wait_for_selector(
                    '[class*="conversation"], .chat-list, .history-list, '
                    '[data-testid="conversation-list"]',
                    timeout=30000,
                )

                # Extract conversation metadata via page evaluation
                conversations = await page.evaluate(
                    """
                    () => {
                        const items = [];
                        const selectors = [
                            '[class*="conversation"]',
                            '.chat-list-item',
                            '.history-item',
                            '[data-testid="conversation-item"]',
                            'div[class*="chat"] > div',
                        ];
                        let elements = [];
                        for (const sel of selectors) {
                            elements = document.querySelectorAll(sel);
                            if (elements.length > 0) break;
                        }
                        elements.forEach((el, idx) => {
                            const titleEl = el.querySelector(
                                'div[class*="title"], .chat-title, h3, h4, span'
                            ) || el;
                            const linkEl = (
                                el.querySelector('a')
                                || el.closest('a')
                                || el
                            );
                            const href = linkEl.href || '';
                            const idMatch = (
                                href.match(/chat\\/([a-f0-9-]+)/)
                                || href.match(/([a-f0-9-]{20,})/)
                            );
                            const timeEl = el.querySelector(
                                'time, [class*="time"], [class*="date"]'
                            );
                            items.push({
                                index: idx,
                                title: titleEl.innerText?.trim() || 'Untitled',
                                url: href,
                                id: idMatch ? idMatch[1] : null,
                                updated_text: timeEl?.innerText?.trim() || null,
                                extracted_at: new Date().toISOString(),
                            });
                        });
                        return items;
                    }
                    """
                )

                self.logger.info(
                    f"Extracted {len(conversations)} conversations"
                )

                if limit and conversations:
                    conversations = conversations[:limit]
                    self.logger.info(
                        f"Limited to top {len(conversations)} conversations"
                    )

            except Exception as e:
                self.logger.error(f"Extraction failed: {e}")
                raise
            finally:
                await browser.close()

        return conversations

    def save_results(
        self,
        conversations: List[Dict[str, Any]],
        filename: Optional[str] = None,
    ) -> Path:
        """Save conversation list to JSON for downstream processing."""
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_list_{ts}.json"

        output_path = self.paths["data"] / filename

        payload = {
            "generated_at": datetime.now().isoformat(),
            "generator": "kimi_conversation_lister.py",
            "version": "5.0.0",
            "count": len(conversations),
            "profile_dir": str(self.profile_dir),
            "conversations": conversations,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Results saved to: {output_path}")
        return output_path


# =============================================================================
# CLI Entry Point
# =============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Kimi Conversation Lister v5.0.0"
    )
    parser.add_argument(
        "--profile-dir",
        type=str,
        default=None,
        help="Persistent browser profile directory "
             '(default: ~/.kimi_auth/browser_profile_chromium)',
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of conversations to extract",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON filename (placed in data/ directory)",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run in visible mode (non-headless)",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable Playwright tracing for debugging",
    )

    args = parser.parse_args()

    profile = Path(args.profile_dir) if args.profile_dir else None
    lister = ConversationLister(
        profile_dir=profile,
        headless=not args.visible,
    )

    try:
        conversations = asyncio.run(
            lister.extract_conversations(limit=args.limit)
        )
        output_path = lister.save_results(
            conversations,
            filename=args.output,
        )

        print(f"\n{'=' * 60}")
        print(f"[SUCCESS] Output: {output_path}")
        print(f"[INFO] Total conversations: {len(conversations)}")
        if conversations:
            print(f"[INFO] First: {conversations[0]['title']}")
            print(f"[INFO] Last:  {conversations[-1]['title']}")
        print(f"{'=' * 60}")

        # Print batch download hint
        if conversations:
            print("\n[BATCH DOWNLOAD COMMAND]")
            print("# Iterate all conversations and download .py files:")
            print("cat " + str(output_path) + " | python3 -c '")
            print("import json,sys,subprocess")
            print("data=json.load(sys.stdin)")
            print('for c in data["conversations"]:')
            print('    url=c["url"]')
            print('    if url:')
            print('        subprocess.run([')
            print('            "python3", "./scripts/kimi_downloader.py",')
            print('            "--url", url,')
            print('            "--file-types", "py",')
            print('            "--max-files", "10",')
            print('        ])')
            print("'")

    except Exception as e:
        lister.logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
