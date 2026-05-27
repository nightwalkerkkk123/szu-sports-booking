"""Session manager for cookie and authentication state."""
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SessionManager:
    """Manages HTTP session and cookies for API calls."""

    base_url: str = "https://ehall.szu.edu.cn/qljfwapp"
    cookies: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)

    _required_cookies: list[str] = field(default_factory=lambda: [
        "MOD_AUTH_CAS",
        "_WEU",
        "EMAP_LANG",
    ])

    def __post_init__(self):
        self._init_headers()

    def _init_headers(self):
        """Initialize default headers"""
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://ehall.szu.edu.cn",
            "Referer": "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do#/sportVenue",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }

    def set_cookie(self, name: str, value: str):
        """Set a single cookie"""
        self.cookies[name] = value

    def set_cookies(self, cookies: dict):
        """Set multiple cookies from a dict"""
        self.cookies.update(cookies)

    def set_cookies_from_browser(self, browser_context) -> bool:
        """
        Extract cookies from a browser context.

        Args:
            browser_context: CloakBrowser context or similar with cookie support

        Returns:
            True if all required cookies were found
        """
        try:
            # Try to get cookies from browser context
            if hasattr(browser_context, "cookies"):
                # It's a Playwright context
                import asyncio
                asyncio.get_event_loop().run_until_complete(
                    self._extract_cookies_async(browser_context)
                )
            elif hasattr(browser_context, "context"):
                # It's a CloakBrowser instance
                self._extract_from_cloak(browser_context)

            return self.is_authenticated()
        except Exception:
            return False

    def _extract_from_cloak(self, cloak_browser):
        """Extract cookies from CloakBrowser instance"""
        try:
            # Try to get cookies via evaluate
            page = cloak_browser.page if hasattr(cloak_browser, "page") else cloak_browser
            cookie_str = page.evaluate("""
                document.cookie
            """)
            # Parse cookie string
            for part in cookie_str.split(";"):
                if "=" in part:
                    name, value = part.strip().split("=", 1)
                    self.cookies[name.strip()] = value.strip()
        except Exception:
            pass

    def is_authenticated(self) -> bool:
        """Check if session has required authentication cookies"""
        for cookie_name in self._required_cookies:
            if cookie_name not in self.cookies:
                return False
        return True

    def get_cookie_header(self) -> str:
        """Get cookies as a header string"""
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def clear(self):
        """Clear all cookies and headers"""
        self.cookies.clear()
        self._init_headers()

    def update_headers(self, headers: dict):
        """Update headers"""
        self.headers.update(headers)