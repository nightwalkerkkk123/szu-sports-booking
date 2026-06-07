"""Tests for SportPage selector."""


class TestSportPageSelectors:
    """SportPage 用的 CSS 常量。"""

    def test_wrapper_selector_is_text_wrapper_7(self):
        from booking.selectors.sport_page import SportPage

        assert SportPage.WRAPPER_SELECTOR == "div.text-wrapper-7"

    def test_click_timeout_is_ten_seconds(self):
        from booking.selectors.sport_page import SportPage

        assert SportPage.CLICK_TIMEOUT == 10000


class TestSportPageConstruction:
    """SportPage 构造 + 依赖。"""

    def test_init_takes_page_and_chain(self):
        from booking.selectors.sport_page import SportPage

        page = object()
        chain = object()
        sp = SportPage(page, chain=chain)
        assert sp.page is page
        assert sp.chain is chain


class TestSportPageWithFakeBrowser:
    """用 FakeBrowser 验证 SportPage.select() 走 Chain.click(selector=)."""

    def test_select_raises_click_error_when_selector_not_found(self):
        """FakePage.wait_for_selector 是 no-op（返回 None），Chain 应当 raise ClickError"""
        from booking.browser.fake_browser import FakePage
        from booking.chain_builder import Chain, ClickError
        from booking.selectors.sport_page import SportPage

        page = FakePage()
        chain = Chain(page)
        sp = SportPage(page, chain=chain)

        import pytest

        with pytest.raises(ClickError):
            sp.select("网球")
