"""Playwright 基础爬虫类

提供公共的浏览器管理、反检测、请求间隔等功能。
"""
import asyncio
import random
import logging
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from backend.config import settings

logger = logging.getLogger(__name__)

# 常用 User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]


class BaseCrawler:
    """Playwright 爬虫基类"""

    def __init__(self, name: str = "base"):
        self.name = name
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self.headless = settings.crawler_headless
        self.timeout = settings.crawler_timeout_ms
        self.min_interval = settings.crawler_request_interval_min
        self.max_interval = settings.crawler_request_interval_max

    async def start(self):
        """启动浏览器"""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

    async def new_context(self) -> BrowserContext:
        """创建带反检测的新上下文"""
        ua = random.choice(USER_AGENTS)
        viewport = {
            "width": random.randint(1280, 1920),
            "height": random.randint(720, 1080),
        }
        context = await self._browser.new_context(
            user_agent=ua,
            viewport=viewport,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        # 隐藏自动化特征
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        """)
        return context

    async def random_delay(self):
        """随机等待间隔，模拟人类操作"""
        delay = random.uniform(self.min_interval, self.max_interval)
        await asyncio.sleep(delay)

    async def safe_goto(self, page: Page, url: str, retries: int = 2):
        """带重试的安全页面导航"""
        for attempt in range(retries):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                await self.random_delay()
                return True
            except Exception as e:
                logger.warning(f"[{self.name}] goto {url} attempt {attempt+1} failed: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(5)
        return False

    async def safe_text(self, page: Page, selector: str, default: str = "") -> str:
        """安全提取文本"""
        try:
            el = await page.wait_for_selector(selector, timeout=5000)
            return (await el.inner_text()).strip() if el else default
        except Exception:
            return default

    async def safe_attr(self, page: Page, selector: str, attr: str, default: str = "") -> str:
        """安全提取属性"""
        try:
            el = await page.wait_for_selector(selector, timeout=5000)
            return (await el.get_attribute(attr)) or default
        except Exception:
            return default

    async def close(self):
        """关闭浏览器"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
