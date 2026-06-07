"""Tests for CampusPage selector."""


class TestCampusPageSelectors:
    """CampusPage 用的 CSS 常量。"""

    def test_button_selector_is_bh_btn(self):
        from booking.selectors.campus_page import CampusPage

        assert CampusPage.BUTTON_SELECTOR == ".bh-btn"

    def test_click_timeout_is_ten_seconds(self):
        from booking.selectors.campus_page import CampusPage

        assert CampusPage.CLICK_TIMEOUT == 10000


class TestCampusPageConstruction:
    """CampusPage 构造 + 依赖。"""

    def test_init_takes_page_and_chain(self):
        from booking.selectors.campus_page import CampusPage

        page = object()
        chain = object()
        cp = CampusPage(page, chain=chain)
        assert cp.page is page
        assert cp.chain is chain


class TestCampusPageWithFakeBrowser:
    """用 FakeBrowser 验证 CampusPage.select() 走 Chain.click(selector=)."""

    def test_select_raises_click_error_when_selector_not_found(self):
        """FakePage.wait_for_selector 是 no-op（返回 None），Chain 应当 raise ClickError"""
        from booking.browser.fake_browser import FakePage
        from booking.chain_builder import Chain, ClickError
        from booking.selectors.campus_page import CampusPage

        page = FakePage()
        chain = Chain(page)
        cp = CampusPage(page, chain=chain)

        # FakePage.wait_for_selector 不返回 button → Chain.click 抛 ClickError
        import pytest

        with pytest.raises(ClickError):
            cp.select("粤海校区")
