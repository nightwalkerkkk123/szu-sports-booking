"""Tests for ConfirmPage selector."""


class TestConfirmPageSelectors:
    """ConfirmPage 用的 CSS / 关键字常量。"""

    def test_confirm_selectors_has_six_entries(self):
        from booking.selectors.confirm_page import ConfirmPage

        assert len(ConfirmPage.CONFIRM_SELECTORS) == 6

    def test_fail_keywords_has_seven_entries(self):
        from booking.selectors.confirm_page import ConfirmPage

        assert len(ConfirmPage.FAIL_KEYWORDS) == 7

    def test_success_keywords_has_three_entries(self):
        from booking.selectors.confirm_page import ConfirmPage

        assert len(ConfirmPage.SUCCESS_KEYWORDS) == 3

    def test_specific_fail_keywords_present(self):
        from booking.selectors.confirm_page import ConfirmPage

        for kw in (
            "操作过于频繁",
            "预约失败",
            "已预约过",
            "名额已满",
            "不可预约",
            "已满员",
            "已达上限",
        ):
            assert kw in ConfirmPage.FAIL_KEYWORDS

    def test_specific_success_keywords_present(self):
        from booking.selectors.confirm_page import ConfirmPage

        for kw in ("预约成功", "提交成功", "操作成功"):
            assert kw in ConfirmPage.SUCCESS_KEYWORDS


class TestConfirmPageConstruction:
    """ConfirmPage 构造 + 依赖。"""

    def test_init_takes_page_and_chain(self):
        from booking.selectors.confirm_page import ConfirmPage

        page = object()
        chain = object()
        cp = ConfirmPage(page, chain=chain)
        assert cp.page is page
        assert cp.chain is chain


class _FakeButton:
    def click(self):
        pass


class _ProgrammablePage:
    """测试用 page：wait_for_selector 按 registered_selectors 返回 button 或 None。"""

    def __init__(self):
        self._registered_selectors: dict[str, _FakeButton | None] = {}
        self.wait_for_timeout_calls: list[int] = []

    def register_selector(self, selector: str, button: _FakeButton | None) -> None:
        self._registered_selectors[selector] = button

    def wait_for_selector(self, selector: str, **kwargs):
        return self._registered_selectors.get(selector)

    def wait_for_timeout(self, ms: int) -> None:
        self.wait_for_timeout_calls.append(ms)


class _ProgrammableChain:
    def __init__(self, body_text: str = ""):
        self._body_text = body_text

    def get_body_text(self) -> str:
        return self._body_text


class TestConfirmPageWithFakeBrowser:
    """用 programmable page + chain 验证 ConfirmPage.confirm() 行为。"""

    def test_returns_false_when_no_selector_matches(self):
        """6 个 selector 都不存在 → False"""
        from booking.selectors.confirm_page import ConfirmPage

        page = _ProgrammablePage()
        chain = _ProgrammableChain(body_text="")
        cp = ConfirmPage(page, chain=chain)

        # 不注册任何 selector
        result = cp.confirm()
        assert result is False

    def test_returns_false_when_body_has_fail_keyword(self):
        """命中 FAIL_KEYWORDS → False"""
        from booking.selectors.confirm_page import ConfirmPage

        page = _ProgrammablePage()
        chain = _ProgrammableChain(body_text="操作过于频繁，请稍后再试")
        cp = ConfirmPage(page, chain=chain)
        page.register_selector('button:has-text("确认")', _FakeButton())

        result = cp.confirm()
        assert result is False

    def test_returns_true_when_body_has_success_keyword(self):
        """命中 SUCCESS_KEYWORDS → True"""
        from booking.selectors.confirm_page import ConfirmPage

        page = _ProgrammablePage()
        chain = _ProgrammableChain(body_text="预约成功，请按时到场")
        cp = ConfirmPage(page, chain=chain)
        page.register_selector('button:has-text("确认")', _FakeButton())

        result = cp.confirm()
        assert result is True

    def test_returns_false_when_body_has_neither_keyword(self):
        """都不命中 → False（保守策略）"""
        from booking.selectors.confirm_page import ConfirmPage

        page = _ProgrammablePage()
        chain = _ProgrammableChain(body_text="页面没有任何关键字提示")
        cp = ConfirmPage(page, chain=chain)
        page.register_selector('button:has-text("确认")', _FakeButton())

        result = cp.confirm()
        assert result is False

    def test_skips_to_second_selector_when_first_fails(self):
        """第 1 个 selector 不存在、第 2 个命中 success → True"""
        from booking.selectors.confirm_page import ConfirmPage

        page = _ProgrammablePage()
        chain = _ProgrammableChain(body_text="预约成功")
        cp = ConfirmPage(page, chain=chain)
        # 第一个不注册，第二个注册
        page.register_selector('button:has-text("提交")', _FakeButton())

        result = cp.confirm()
        assert result is True

    def test_fail_keyword_takes_precedence_over_success(self):
        """同一 body 包含 success 和 fail → fail 优先（先检查 fail）"""
        from booking.selectors.confirm_page import ConfirmPage

        page = _ProgrammablePage()
        chain = _ProgrammableChain(body_text="预约成功... 但是操作过于频繁")
        cp = ConfirmPage(page, chain=chain)
        page.register_selector('button:has-text("确认")', _FakeButton())

        result = cp.confirm()
        assert result is False

    def test_waits_after_click(self):
        """点击后调 wait_for_timeout(POST_CLICK_WAIT_MS)"""
        from booking.selectors.confirm_page import ConfirmPage

        page = _ProgrammablePage()
        chain = _ProgrammableChain(body_text="预约成功")
        cp = ConfirmPage(page, chain=chain)
        page.register_selector('button:has-text("确认")', _FakeButton())

        cp.confirm()
        assert page.wait_for_timeout_calls == [ConfirmPage.POST_CLICK_WAIT_MS]
