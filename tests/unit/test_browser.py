"""Tests for browser abstraction layer."""
from booking.browser.fake_browser import FakeBrowserLifecycle, FakePage, FakeKeyboard


class TestFakeBrowserLifecycle:
    """Tests for FakeBrowserLifecycle."""

    def test_initial_state(self):
        """初始状态"""
        browser = FakeBrowserLifecycle()
        assert browser.is_launched() is False

    def test_launch(self):
        """launch 启动"""
        browser = FakeBrowserLifecycle()
        browser.launch(headless=False)
        assert browser.is_launched() is True

    def test_close(self):
        """close 关闭"""
        browser = FakeBrowserLifecycle()
        browser.launch()
        browser.close()
        assert browser.is_launched() is False

    def test_new_page(self):
        """new_page 创建新页面"""
        browser = FakeBrowserLifecycle()
        page = browser.new_page()
        assert page is not None
        assert isinstance(page, FakePage)

    def test_page_property(self):
        """page 属性"""
        browser = FakeBrowserLifecycle()
        page = browser.page
        assert isinstance(page, FakePage)

    def test_screenshot(self):
        """screenshot 截图（no-op）"""
        browser = FakeBrowserLifecycle()
        browser.screenshot("/tmp/test.png")

    def test_goto(self):
        """goto 导航（no-op）"""
        browser = FakeBrowserLifecycle()
        browser.goto("https://example.com")


class TestFakePage:
    """Tests for FakePage."""

    def test_url_tracking(self):
        """URL 跟踪"""
        page = FakePage()
        page.goto("https://example.com")
        assert page.url == "https://example.com"

    def test_goto_defaults(self):
        """goto 默认值"""
        page = FakePage()
        assert page.url == ""

    def test_title(self):
        """title 返回默认值"""
        page = FakePage()
        assert page.title() == "Fake Page"

    def test_content(self):
        """content 返回默认值"""
        page = FakePage()
        assert page.content() == "<html>fake</html>"

    def test_is_visible(self):
        """is_visible 返回 False"""
        page = FakePage()
        assert page.is_visible("selector") is False

    def test_is_checked(self):
        """is_checked 返回 False"""
        page = FakePage()
        assert page.is_checked("selector") is False

    def test_input_value(self):
        """input_value 返回空"""
        page = FakePage()
        assert page.input_value("selector") == ""

    def test_query_selector(self):
        """query_selector 返回 None"""
        page = FakePage()
        assert page.query_selector("div") is None

    def test_query_selector_all(self):
        """query_selector_all 返回空列表"""
        page = FakePage()
        assert page.query_selector_all("div") == []

    def test_wait_for_load_state(self):
        """wait_for_load_state 不报错"""
        page = FakePage()
        page.wait_for_load_state("domcontentloaded")

    def test_wait_for_timeout(self):
        """wait_for_timeout 不报错"""
        page = FakePage()
        page.wait_for_timeout(100)

    def test_wait_for_selector(self):
        """wait_for_selector 不报错"""
        page = FakePage()
        page.wait_for_selector("selector")

    def test_click(self):
        """click 不报错"""
        page = FakePage()
        page.click("button")

    def test_fill(self):
        """fill 不报错"""
        page = FakePage()
        page.fill("input", "value")

    def test_evaluate(self):
        """evaluate 不报错"""
        page = FakePage()
        page.evaluate("console.log('test')")

    def test_screenshot(self):
        """screenshot 不报错"""
        page = FakePage()
        page.screenshot("/tmp/screenshot.png")

    def test_keyboard(self):
        """keyboard 属性"""
        page = FakePage()
        assert isinstance(page.keyboard, FakeKeyboard)


class TestFakeKeyboard:
    """Tests for FakeKeyboard."""

    def test_press(self):
        """press 不报错"""
        kb = FakeKeyboard()
        kb.press("Tab")
        kb.press("Enter")
