"""Fake browser for testing without real browser."""


class FakeBrowserLifecycle:
    """Fake browser implementation for testing."""

    def __init__(self):
        """Initialize fake browser."""
        self._page = FakePage()
        self._launched = False

    def launch(self, headless: bool = False) -> None:
        """Mark browser as launched."""
        self._launched = True

    def new_page(self):
        """Return a fake page."""
        return FakePage()

    def goto(self, url: str) -> None:
        """Record navigation (does nothing)."""
        pass

    def close(self) -> None:
        """Mark as closed."""
        self._launched = False

    def screenshot(self, path: str) -> None:
        """Record screenshot (does nothing)."""
        pass

    @property
    def page(self):
        """Get the fake page."""
        return self._page

    def is_launched(self) -> bool:
        """Check if launched."""
        return self._launched


class FakePage:
    """Fake page for testing."""

    def __init__(self):
        """Initialize fake page."""
        self._url = ""
        self._content = {}
        self.keyboard = FakeKeyboard()

    def goto(self, url: str) -> None:
        """Record URL."""
        self._url = url

    def wait_for_load_state(self, state: str) -> None:
        """No-op for fake page."""
        pass

    def wait_for_timeout(self, timeout: int) -> None:
        """No-op for fake page."""
        pass

    def wait_for_selector(self, selector: str, **kwargs) -> None:
        """No-op for fake page."""
        pass

    def screenshot(self, path: str = None) -> None:
        """No-op for fake page."""
        pass

    def click(self, selector: str) -> None:
        """Record click."""
        pass

    def fill(self, selector: str, value: str) -> None:
        """Record fill."""
        pass

    def evaluate(self, script: str) -> None:
        """No-op for fake page."""
        pass

    def query_selector(self, selector: str):
        """Return None for fake page."""
        return None

    def query_selector_all(self, selector: str):
        """Return empty list for fake page."""
        return []

    @property
    def url(self):
        return self._url

    def title(self):
        return "Fake Page"

    def content(self):
        return "<html>fake</html>"

    def is_visible(self, selector: str) -> bool:
        """Return False for fake page."""
        return False

    def is_checked(self, selector: str) -> bool:
        """Return False for fake page."""
        return False

    def input_value(self, selector: str) -> str:
        """Return empty string for fake page."""
        return ""


class FakeKeyboard:
    """Fake keyboard for testing."""

    def press(self, key: str) -> None:
        """No-op for fake keyboard."""
        pass
