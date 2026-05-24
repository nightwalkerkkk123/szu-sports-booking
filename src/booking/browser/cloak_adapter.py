"""CloakBrowser adapter for browser lifecycle."""
from typing import Optional

from booking.browser.lifecycle import BrowserLifecycle


class CloakBrowserLifecycle(BrowserLifecycle):
    """CloakBrowser implementation of BrowserLifecycle."""

    def __init__(self):
        """Initialize with no browser launched."""
        self._browser = None
        self._page = None

    def launch(self, headless: bool = False) -> None:
        """Launch CloakBrowser.

        Args:
            headless: Whether to run in headless mode.
        """
        from cloakbrowser import launch

        self._browser = launch(headless=headless)
        self._page = self._browser.new_page()

    def new_page(self):
        """Create a new page."""
        if self._browser is None:
            self.launch()
        return self._browser.new_page()

    def goto(self, url: str) -> None:
        """Navigate to URL.

        Args:
            url: Target URL.
        """
        if self._page is None:
            self.launch()
        self._page.goto(url)
        self._page.wait_for_load_state("domcontentloaded")

    def close(self) -> None:
        """Close the browser."""
        if self._browser:
            self._browser.close()
            self._browser = None
            self._page = None

    def screenshot(self, path: str) -> None:
        """Take a screenshot.

        Args:
            path: Output file path.
        """
        if self._page:
            self._page.screenshot(path=path)

    @property
    def page(self):
        """Get the current page."""
        return self._page

    def is_launched(self) -> bool:
        """Check if browser is launched."""
        return self._browser is not None