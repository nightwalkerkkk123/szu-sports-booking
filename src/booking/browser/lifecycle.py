"""Browser lifecycle abstraction."""
from abc import ABC, abstractmethod


class BrowserLifecycle(ABC):
    """Abstract interface for browser lifecycle management."""

    @abstractmethod
    def launch(self, headless: bool = False) -> None:
        """Launch the browser.

        Args:
            headless: Whether to run browser in headless mode.
        """
        pass

    @abstractmethod
    def new_page(self):
        """Create a new page."""
        pass

    @abstractmethod
    def goto(self, url: str) -> None:
        """Navigate to a URL.

        Args:
            url: Target URL.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the browser."""
        pass

    @abstractmethod
    def screenshot(self, path: str) -> None:
        """Take a screenshot.

        Args:
            path: Output file path.
        """
        pass


class BrowserPool:
    """Pool of browser instances for concurrent operations."""

    def __init__(self, max_instances: int = 3):
        """Initialize browser pool.

        Args:
            max_instances: Maximum number of browser instances.
        """
        self.max_instances = max_instances
        self._browsers: list[BrowserLifecycle] = []

    def acquire(self) -> BrowserLifecycle:
        """Acquire a browser from the pool."""
        # For now, simple implementation - just create a new browser
        # In production, would reuse available browsers from pool
        browser = CloakBrowserLifecycle()
        self._browsers.append(browser)
        return browser

    def release(self, browser: BrowserLifecycle) -> None:
        """Release a browser back to the pool."""
        if browser in self._browsers:
            self._browsers.remove(browser)
            browser.close()


# Import concrete implementation
from booking.browser.cloak_adapter import CloakBrowserLifecycle  # noqa: E402
