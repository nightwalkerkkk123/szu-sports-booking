"""Tests for slot selector and venue selector."""
from unittest.mock import MagicMock

from booking.selectors.slot_selector import (
    FlexibleSlotSelector,
    SlotUnavailableError,
)


def _make_container(color_style=None, has_rectangle=False, has_frame_child=False,
                    has_ellipse=False):
    """Helper: create a mock container element."""
    container = MagicMock()

    # Mock the div.element sub-element
    text_el = MagicMock()
    if color_style:
        text_el.get_attribute.return_value = color_style
    else:
        text_el.get_attribute.return_value = ""
    container.query_selector.return_value = text_el

    # Mock specific child elements
    def query_child(selector):
        if selector == "div.element":
            return text_el
        if selector == "div.rectangle-4":
            return MagicMock() if has_rectangle else None
        if selector == "div.frame-child1":
            return MagicMock() if has_frame_child else None
        if selector == "div.ellipse":
            return MagicMock() if has_ellipse else None
        return None

    container.query_selector = query_child
    return container


class TestSlotUnavailableError:
    """Tests for SlotUnavailableError."""

    def test_is_exception(self):
        """SlotUnavailableError 是 Exception 的子类"""
        err = SlotUnavailableError("不可用")
        assert isinstance(err, Exception)

    def test_message_is_stored(self):
        """错误消息被保存"""
        err = SlotUnavailableError("时间段已满员")
        assert "时间段已满员" in str(err)


class TestFlexibleSlotSelectorIsAvailable:
    """Tests for _is_available."""

    def test_available_color_rgb_162_10_71(self):
        """可用颜色 rgb(162, 10, 71) 返回 True"""
        container = _make_container(color_style="color: rgb(162, 10, 71)")
        selector = FlexibleSlotSelector(MagicMock())

        assert selector._is_available(container) is True

    def test_available_color_rgb_29_33_41(self):
        """可用颜色 rgb(29, 33, 41) 返回 True"""
        container = _make_container(color_style="color: rgb(29, 33, 41)")
        selector = FlexibleSlotSelector(MagicMock())

        assert selector._is_available(container) is True

    def test_unavailable_color_rgb_134_144_156(self):
        """不可用颜色 rgb(134, 144, 156) 返回 False"""
        container = _make_container(color_style="color: rgb(134, 144, 156)")
        selector = FlexibleSlotSelector(MagicMock())

        assert selector._is_available(container) is False

    def test_available_by_rectangle_element(self):
        """通过 div.rectangle-4 判断可用"""
        container = _make_container(has_rectangle=True)
        selector = FlexibleSlotSelector(MagicMock())

        assert selector._is_available(container) is True

    def test_unavailable_by_ellipse_element(self):
        """通过 div.ellipse 判断不可用"""
        container = _make_container(has_ellipse=True)
        selector = FlexibleSlotSelector(MagicMock())

        assert selector._is_available(container) is False

    def test_unavailable_priority_over_available(self):
        """ellipse 和 rectangle 同时存在时，ellipse 方法先执行"""
        # ellipse 和 rectangle 都找不到时，从 color 方法 fallback
        # 但如果 .element 元素颜色也是不可用的，则返回 False
        container = _make_container(
            color_style="color: rgb(134, 144, 156)",  # 不可用
            has_rectangle=True,
            has_ellipse=True
        )
        selector = FlexibleSlotSelector(MagicMock())

        # 方法1：颜色检查 rgb(134, 144, 156) -> False
        assert selector._is_available(container) is False

    def test_fallback_to_true(self):
        """无法判断时默认为可用"""
        container = _make_container()
        selector = FlexibleSlotSelector(MagicMock())

        assert selector._is_available(container) is True

    def test_exception_returns_true(self):
        """异常时默认为可用（避免阻塞）"""
        container = MagicMock()
        container.query_selector.side_effect = Exception("查询失败")
        selector = FlexibleSlotSelector(MagicMock())

        assert selector._is_available(container) is True

    def test_available_by_frame_child(self):
        """通过 div.frame-child1 判断可用"""
        container = _make_container(has_frame_child=True)
        selector = FlexibleSlotSelector(MagicMock())

        assert selector._is_available(container) is True


class TestFlexibleSlotSelectorInit:
    """Tests for FlexibleSlotSelector initialization."""

    def test_default_container_selector(self):
        """默认容器选择器"""
        page = MagicMock()
        selector = FlexibleSlotSelector(page)
        assert selector.page is page
        assert "div.group-2" in selector.container_selector

    def test_custom_container_selector(self):
        """自定义容器选择器"""
        page = MagicMock()
        selector = FlexibleSlotSelector(page, container_selector=".custom")
        assert selector.container_selector == ".custom"


class TestSlotUnavailableErrorUsage:
    """Regression tests for venue/time_slot confusion bug."""

    def test_frame_child1_appears_on_time_slots_too(self):
        """Bug: 可用时间段也有 frame-child1，不能用来区分场地。
        场地唯一可靠特征：文本不含 HH:MM-HH:MM 时间格式。"""
        # 可用时间段：frame-child1 + rgb(29,33,41) + 时间格式文本
        container = _make_container(has_frame_child=True)
        selector = FlexibleSlotSelector(MagicMock())
        assert selector._is_available(container) is True

    def test_ellipse_means_unavailable_regardless(self):
        """ellipse 出现时不可用（不管颜色）"""
        container = _make_container(has_ellipse=True)
        selector = FlexibleSlotSelector(MagicMock())
        # ellipse 判断在颜色和 frame-child1 之后
        # 如果颜色不明确且有 ellipse → 不可用
        assert selector._is_available(container) is False


class TestFlexibleSlotSelectorGetAll:
    """Tests for get_all."""

    def test_get_all_filters_unavailable(self):
        """get_all 过滤不可用选项"""
        page = MagicMock()

        # Available handle: div.element has available color
        available = MagicMock()
        available_el = MagicMock()
        available_el.get_attribute.return_value = "color: rgb(162, 10, 71)"

        def avail_query(sel):
            if "div.element" in sel or "text" in sel:
                return available_el
            return None  # no rectangle, ellipse, etc.

        available.query_selector.side_effect = avail_query
        available.inner_text.return_value = "19:00-20:00"
        available.text_content.return_value = "19:00-20:00"

        # Unavailable handle: div.element has unavailable color
        unavailable = MagicMock()
        unavailable_el = MagicMock()
        unavailable_el.get_attribute.return_value = "color: rgb(134, 144, 156)"

        def unavail_query(sel):
            if "div.element" in sel or "text" in sel:
                return unavailable_el
            return None

        unavailable.query_selector.side_effect = unavail_query
        unavailable.inner_text.return_value = "已满员"
        unavailable.text_content.return_value = "已满员"

        page.query_selector_all.return_value = [available, unavailable]

        selector = FlexibleSlotSelector(page)
        results = selector.get_all("div.group-2", check_availability=True)

        # get_all 返回所有选项（包括不可用的），只是标记 available 字段
        assert len(results) == 2
        assert results[0]["available"] is True
        assert results[1]["available"] is False

    def test_get_all_no_check(self):
        """get_all 不检查可用性时返回所有选项"""
        page = MagicMock()
        handle1 = MagicMock()
        handle1.inner_text.return_value = "19:00-20:00"
        handle2 = MagicMock()
        handle2.inner_text.return_value = "20:00-21:00"
        page.query_selector_all.return_value = [handle1, handle2]

        selector = FlexibleSlotSelector(page)
        results = selector.get_all("div.group-2", check_availability=False)

        assert len(results) == 2

    def test_get_all_empty(self):
        """get_all 空结果"""
        page = MagicMock()
        page.query_selector_all.return_value = []

        selector = FlexibleSlotSelector(page)
        results = selector.get_all("div.group-2")

        assert results == []
