"""Tests for ChainBuilder."""

from unittest.mock import MagicMock

import pytest

from booking.chain_builder import Chain, ClickError


def _make_element():
    """Helper: create a mock Playwright element."""
    element = MagicMock()
    element.click.return_value = None
    return element


def _make_page(elements=None):
    """Helper: create a mock Playwright Page."""
    page = MagicMock()

    if elements is None:
        elements = [_make_element()]

    page.query_selector_all.return_value = elements
    page.wait_for_selector.return_value = _make_element()
    return page


class TestClickError:
    """Tests for ClickError."""

    def test_is_exception(self):
        """ClickError 是 Exception 的子类"""
        err = ClickError("错误")
        assert isinstance(err, Exception)

    def test_message_is_stored(self):
        """错误消息被保存"""
        err = ClickError("未找到元素")
        assert "未找到元素" in str(err)


class TestChainInit:
    """Tests for Chain initialization."""

    def test_init(self):
        """初始化"""
        page = MagicMock()
        chain = Chain(page)
        assert chain.page is page
        assert chain.history == []


class TestChainWait:
    """Tests for Chain.wait."""

    def test_wait_returns_self(self):
        """wait 返回 self 支持链式调用"""
        page = MagicMock()
        chain = Chain(page)
        result = chain.wait(0.01)
        assert result is chain

    def test_wait_for(self):
        """wait_for 等待元素"""
        page = MagicMock()
        chain = Chain(page)
        result = chain.wait_for(".selector")
        assert result is chain


class TestChainType:
    """Tests for Chain.type."""

    def test_type_returns_self(self):
        """type 返回 self"""
        page = MagicMock()
        page.wait_for_selector.return_value = _make_element()
        chain = Chain(page)
        result = chain.type("input", "value")
        assert result is chain


class TestChainSelectRadio:
    """Tests for Chain.select_radio."""

    def test_select_radio_returns_self(self):
        """select_radio 返回 self"""
        page = MagicMock()
        page.query_selector_all.return_value = []
        chain = Chain(page)
        result = chain.select_radio("value")
        assert result is chain


class TestChainGetAll:
    """Tests for Chain.get_all."""

    def test_get_all_empty(self):
        """get_all 空结果"""
        page = MagicMock()
        page.query_selector_all.return_value = []
        chain = Chain(page)
        results = chain.get_all()
        assert results == []

    def test_get_all_returns_empty_on_error(self):
        """get_all 异常时返回空列表"""
        page = MagicMock()
        page.query_selector_all.side_effect = Exception("错误")
        chain = Chain(page)
        results = chain.get_all()
        assert results == []


class TestChainClickFirst:
    """Tests for Chain.click_first."""

    def test_click_first_with_elements(self):
        """click_first 有点击元素"""
        page = _make_page()
        chain = Chain(page)
        result = chain.click_first()
        assert result is chain

    def test_click_first_empty(self):
        """click_first 无元素"""
        page = MagicMock()
        page.query_selector_all.return_value = []
        chain = Chain(page)
        result = chain.click_first()
        assert result is chain

    def test_click_first_on_error(self):
        """click_first 异常时继续"""
        page = MagicMock()
        page.query_selector_all.side_effect = Exception("错误")
        chain = Chain(page)
        result = chain.click_first()
        assert result is chain


class TestChainClick:
    """Tests for Chain.click."""

    def test_click_by_index(self):
        """click 按索引找到元素时点击"""
        page = MagicMock()
        element = _make_element()
        # _find_by_index 使用 query_selector_all 获取元素
        page.query_selector_all.return_value = [element]

        chain = Chain(page)
        result = chain.click(index=0)
        assert result is chain
        # click(index=0) stores target=None in history
        assert ("click", 0) in chain.history or ("click", None) in chain.history

    def test_click_history_records(self):
        """click 记录历史"""
        page = MagicMock()
        element = _make_element()
        page.query_selector_all.return_value = [element]

        chain = Chain(page)
        chain.click(index=0)
        assert len(chain.history) == 1

    def test_click_raises_on_no_element(self):
        """click 找不到元素时抛出 ClickError"""
        page = MagicMock()
        page.wait_for_selector.side_effect = Exception("timeout")
        page.query_selector_all.return_value = []

        chain = Chain(page)
        with pytest.raises(ClickError):
            chain.click("不存在的元素")

    def test_click_raises_on_none_target(self):
        """click target=None 找不到元素时抛出 ClickError"""
        page = MagicMock()
        page.query_selector_all.return_value = []

        chain = Chain(page)
        with pytest.raises(ClickError):
            chain.click(None)


class TestChainChaining:
    """Tests for Chain chaining."""

    def test_chain_multiple_operations(self):
        """多个链式操作"""
        page = MagicMock()
        element = _make_element()
        page.query_selector_all.return_value = [element]
        page.wait_for_selector.return_value = element

        chain = Chain(page)
        chain.click(index=0).wait(0.01).click_first().wait_for(".test")

        assert len(chain.history) >= 1
