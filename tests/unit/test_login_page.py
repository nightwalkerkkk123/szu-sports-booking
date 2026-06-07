"""Tests for LoginPage selector."""


class TestLoginPageSelectors:
    """LoginPage 用的 CSS 常量。"""

    def test_username_selector_is_username_input(self):
        from booking.selectors.login_page import LoginPage

        assert LoginPage.USERNAME_SELECTOR == "#username"

    def test_password_selector_is_password_input(self):
        from booking.selectors.login_page import LoginPage

        assert LoginPage.PASSWORD_SELECTOR == "#password"

    def test_submit_selector_is_login_submit_button(self):
        from booking.selectors.login_page import LoginPage

        assert LoginPage.SUBMIT_SELECTOR == "#login_submit"

    def test_logged_in_indicator_is_bh_btn(self):
        from booking.selectors.login_page import LoginPage

        assert LoginPage.LOGGED_IN_INDICATOR == ".bh-btn"

    def test_remove_readonly_script_targets_password(self):
        from booking.selectors.login_page import LoginPage

        script = LoginPage.REMOVE_READONLY_SCRIPT
        assert "removeAttribute" in script
        assert "readonly" in script
        assert "#password" in script
        assert "no-auto-input" in script


class TestLoginPageConstruction:
    """LoginPage 构造 + 依赖。"""

    def test_init_takes_page_and_chain(self):
        from booking.selectors.login_page import LoginPage

        page = object()
        chain = object()
        lp = LoginPage(page, chain=chain)
        assert lp.page is page
        assert lp.chain is chain
