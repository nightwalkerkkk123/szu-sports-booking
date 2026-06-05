"""Tests for BookingClient."""

from booking.browser.fake_browser import FakeBrowserLifecycle
from booking.client import BookingClient


class TestBookingClientBasic:
    """Basic tests for BookingClient that don't trigger browser creation."""

    def test_init(self):
        """客户端初始化"""
        client = BookingClient()
        assert client.page is None
        assert client.browser is None
        assert client.headless is False

    def test_init_with_headless(self):
        """带 headless 参数初始化"""
        client = BookingClient(headless=True)
        assert client.headless is True

    def test_set_browser(self):
        """set_browser 设置自定义浏览器"""
        fake = FakeBrowserLifecycle()
        client = BookingClient()
        result = client.set_browser(fake)
        assert result is client
        assert client.browser is fake
        assert client.page is fake.page

    def test_open(self):
        """open 打开页面"""
        client = BookingClient()
        fake = FakeBrowserLifecycle()
        fake.launch()
        client.set_browser(fake)
        result = client.open("https://example.com")
        assert result is client
        assert client.page.url == "https://example.com"

    def test_close(self):
        """close 关闭浏览器"""
        client = BookingClient()
        fake = FakeBrowserLifecycle()
        fake.launch()
        client.set_browser(fake)
        client.close()
        assert client.browser is None
        assert client.page is None

    def test_config(self):
        """config 批量配置"""
        client = BookingClient()
        result = client.config(campus="粤海校区", sport="网球")
        assert result is client
        assert client._config["campus"] == "粤海校区"
        assert client._config["sport"] == "网球"

    def test_wait_returns_self(self):
        """wait 返回 client 支持链式调用"""
        client = BookingClient()
        fake = FakeBrowserLifecycle()
        fake.launch()
        client.set_browser(fake)
        result = client.wait(0.01)
        assert result is client


class TestBookingClientContextManager:
    """Tests for BookingClient context manager."""

    def test_enter_sets_browser(self):
        """__enter__ 使用已设置的 fake browser"""
        client = BookingClient()
        client.set_browser(FakeBrowserLifecycle())
        with client:
            assert client.browser is not None

    def test_exit_closes_browser(self):
        """__exit__ 关闭浏览器"""
        client = BookingClient()
        fake = FakeBrowserLifecycle()
        fake.launch()
        client.set_browser(fake)
        with client:
            pass  # 不使用 context manager 内部的浏览器创建
        assert client.browser is None


class TestBookingClientConfirm:
    """Tests for BookingClient.confirm."""

    def test_confirm_returns_bool(self):
        """confirm 返回布尔值"""
        client = BookingClient()
        fake = FakeBrowserLifecycle()
        fake.launch()
        client.set_browser(fake)
        result = client.confirm()
        assert isinstance(result, bool)


class TestBookingClientRunSteps:
    """Tests for BookingClient.run_steps."""

    def test_run_steps_returns_bool(self):
        """run_steps 返回布尔值"""
        client = BookingClient()
        fake = FakeBrowserLifecycle()
        fake.launch()
        client.set_browser(fake)
        steps = [{"action": "wait", "target": 0.01}]
        result = client.run_steps(steps)
        assert result is True

    def test_run_steps_empty(self):
        """run_steps 空列表"""
        client = BookingClient()
        fake = FakeBrowserLifecycle()
        fake.launch()
        client.set_browser(fake)
        result = client.run_steps([])
        assert result is True
