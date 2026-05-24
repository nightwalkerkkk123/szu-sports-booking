"""Browser abstraction layer."""
from booking.browser.lifecycle import BrowserLifecycle, BrowserPool, CloakBrowserLifecycle
from booking.browser.fake_browser import FakeBrowserLifecycle, FakePage

__all__ = [
    "BrowserLifecycle",
    "BrowserPool",
    "CloakBrowserLifecycle",
    "FakeBrowserLifecycle",
    "FakePage",
]