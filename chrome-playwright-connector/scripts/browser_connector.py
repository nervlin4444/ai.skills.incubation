"""
---
title: "Browser Connector Core"
name: "chrome-playwright-connector"
description: "瀏覽器連接器核心類，封裝 Playwright 瀏覽器生命週期管理、頁面導航、元素操作、下載捕獲與診斷觸發。"
version: "1.0.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-21T16:39:00+08:00"
auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"
file_mapping:
  local_path: "{baseDir}/scripts/browser_connector.py"
  github_path: "chrome-playwright-connector/scripts/browser_connector.py"
---
"""

# -*- coding: utf-8 -*-

import os
import time
from pathlib import Path
from typing import Optional, Any

try:
    from playwright.sync_api import sync_playwright, BrowserContext, Page, ElementHandle, Download
except ImportError:
    raise ImportError("playwright not installed. Run: pip3 install playwright && python3 -m playwright install chromium")

from profile_manager import get_profile_path
from diagnostic_kit import diagnose_page, diagnose_selector


class BrowserConnector:
    """
    通用瀏覽器連接器，封裝 Playwright 瀏覽器生命週期。

    使用示例：
        driver = BrowserConnector(profile_name="kimi_com", visible=True)
        driver.launch()
        page = driver.navigate("https://www.kimi.com")
        driver.click("button.login")
        driver.close()
    """

    def __init__(
        self,
        profile_name: str = "default",
        headless: bool = True,
        download_dir: str = None,
        visible: bool = False,
        timeout: int = 30000,
    ):
        self.profile_name = profile_name
        self.headless = not visible if visible else headless
        self.download_dir = download_dir or self._default_download_dir()
        self.timeout = timeout
        self._playwright = None
        self._context = None
        self._page = None

    def _default_download_dir(self) -> str:
        base = Path(__file__).parent.parent
        d = base / "downloads"
        d.mkdir(parents=True, exist_ok=True)
        return str(d)

    def _default_diagnose_dir(self) -> str:
        base = Path(__file__).parent.parent
        d = base / "diagnose"
        d.mkdir(parents=True, exist_ok=True)
        return str(d)

    def launch(self) -> BrowserContext:
        """啟動 persistent context，返回 BrowserContext 實例。"""
        profile_path = get_profile_path(self.profile_name)
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=self.headless,
            downloads_path=self.download_dir,
            viewport={"width": 1400, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        return self._context

    def navigate(self, url: str, wait_until: str = "networkidle") -> Page:
        """導航到指定 URL，等待頁面穩定後返回 Page 實例。"""
        if not self._context:
            raise RuntimeError("Browser not launched. Call launch() first.")
        self._page = self._context.new_page()
        self._page.goto(url, wait_until=wait_until, timeout=self.timeout)
        return self._page

    def click(self, selector: str, force: bool = False, retry: int = 1) -> bool:
        """點擊元素。失敗後延遲 2s 重試 retry 次。"""
        for attempt in range(retry + 1):
            try:
                if force:
                    self._page.evaluate('document.querySelector("' + selector + '").click()')
                else:
                    self._page.click(selector, timeout=self.timeout)
                return True
            except Exception as e:
                if attempt < retry:
                    time.sleep(2)
                else:
                    diagnose_selector(self._page, selector)
                    raise e
        return False

    def fill(self, selector: str, text: str) -> bool:
        """在輸入框填寫文字。自動清除原有內容。"""
        try:
            self._page.fill(selector, text, timeout=self.timeout)
            return True
        except Exception as e:
            diagnose_selector(self._page, selector)
            raise e

    def wait_for_selector(self, selector: str, state: str = "visible", timeout: int = 30000) -> ElementHandle:
        """等待元素進入指定狀態。"""
        try:
            return self._page.wait_for_selector(selector, state=state, timeout=timeout)
        except Exception as e:
            diagnose_selector(self._page, selector)
            raise e

    def screenshot(self, path: str = None) -> str:
        """截取當前頁面。path 為 None 時自動生成到 diagnose/。"""
        if path is None:
            ts = time.strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self._default_diagnose_dir(), f"screenshot_{ts}.png")
        self._page.screenshot(path=path, full_page=True)
        return path

    def dump_html(self, path: str = None) -> str:
        """導出當前頁面完整 HTML。path 為 None 時自動生成。"""
        if path is None:
            ts = time.strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self._default_diagnose_dir(), f"page_{ts}.html")
        html = self._page.content()
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    def dump_elements(self, selector: str = "*") -> list:
        """列舉當前頁面所有匹配元素。"""
        elements = self._page.query_selector_all(selector)
        result = []
        for el in elements:
            tag = el.evaluate("el => el.tagName.toLowerCase()")
            text = el.inner_text() if hasattr(el, "inner_text") else ""
            attrs = el.evaluate("el => { const a={}; for (const k of el.getAttributeNames()) a[k]=el.getAttribute(k); return a; }")
            result.append((tag, text, attrs, selector))
        return result

    def get_download(self, timeout: int = 10000) -> Download:
        """等待並返回下一個下載事件。"""
        with self._page.expect_download(timeout=timeout) as download_info:
            pass
        return download_info.value

    def evaluate(self, js_code: str) -> Any:
        """執行 JavaScript 代碼，返回執行結果。"""
        return self._page.evaluate(js_code)

    def close(self):
        """關閉 browser context，釋放資源。"""
        if self._context:
            self._context.close()
        if self._playwright:
            self._playwright.stop()
        self._context = None
        self._playwright = None
        self._page = None


if __name__ == "__main__":
    # 簡易測試
    bc = BrowserConnector(profile_name="default", visible=True)
    bc.launch()
    bc.navigate("https://www.example.com")
    print("Page title:", bc.evaluate("document.title"))
    bc.close()
