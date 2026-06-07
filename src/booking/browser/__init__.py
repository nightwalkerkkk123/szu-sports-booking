"""Browser abstraction layer."""

from booking.browser.fake_browser import FakeBrowserLifecycle, FakePage
from booking.browser.lifecycle import BrowserLifecycle, BrowserPool, CloakBrowserLifecycle

__all__ = [
    "BrowserLifecycle",
    "BrowserPool",
    "CloakBrowserLifecycle",
    "FakeBrowserLifecycle",
    "FakePage",
]
