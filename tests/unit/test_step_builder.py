"""Tests for StepBuilder."""
from unittest.mock import MagicMock
import pytest

from booking.step_builder import StepBuilder


def _make_page():
    """Helper: create a mock Playwright Page."""
    page = MagicMock()
    element = MagicMock()
    page.query_selector_all.return_value = [element]
    page.wait_for_selector.return_value = element
    return page


class TestStepBuilderInit:
    """Tests for StepBuilder initialization."""

    def test_init(self):
        """初始化"""
        page = MagicMock()
        builder = StepBuilder(page)
        assert builder.page is page
        assert builder.steps == []

    def test_init_creates_chain(self):
        """初始化创建 Chain"""
        page = MagicMock()
        builder = StepBuilder(page)
        assert builder.chain is not None


class TestStepBuilderStep:
    """Tests for StepBuilder.step definition."""

    def test_step_definition(self):
        """step 定义步骤"""
        page = MagicMock()
        builder = StepBuilder(page)
        result = builder.step("选择校区")

        assert result is builder
        assert len(builder.steps) == 1
        assert builder.steps[0]["description"] == "选择校区"
        assert builder.steps[0]["retries"] == 3

    def test_multiple_steps(self):
        """多个步骤定义"""
        page = MagicMock()
        builder = StepBuilder(page)
        builder.step("步骤1").step("步骤2").step("步骤3")
        assert len(builder.steps) == 3

    def test_step_defaults(self):
        """步骤默认值"""
        page = MagicMock()
        builder = StepBuilder(page)
        builder.step("测试步骤")

        step = builder.steps[0]
        assert step["description"] == "测试步骤"
        assert step["retries"] == 3
        assert step["delay"] == 0
        assert step["action"] is None
        assert step["on_error"] is None


class TestStepBuilderActions:
    """Tests for StepBuilder action methods."""

    def test_click_action(self):
        """click 动作"""
        page = MagicMock()
        builder = StepBuilder(page)
        result = builder.step("点击校区").click("粤海校区")

        assert result is builder
        action_type, params = builder.steps[0]["action"]
        assert action_type == "click"
        assert params["target"] == "粤海校区"

    def test_click_with_index(self):
        """click 按索引"""
        page = MagicMock()
        builder = StepBuilder(page)
        builder.step("选择").click(index=0)

        _, params = builder.steps[0]["action"]
        assert params["index"] == 0

    def test_click_with_contains(self):
        """click 包含匹配"""
        page = MagicMock()
        builder = StepBuilder(page)
        builder.step("选择").click(contains="粤海")

        _, params = builder.steps[0]["action"]
        assert params["contains"] == "粤海"

    def test_click_first(self):
        """click_first 动作"""
        page = MagicMock()
        builder = StepBuilder(page)
        result = builder.step("点击第一个").click_first()

        assert result is builder
        action_type, _ = builder.steps[0]["action"]
        assert action_type == "click_first"

    def test_wait_action(self):
        """wait 动作"""
        page = MagicMock()
        builder = StepBuilder(page)
        builder.step("等待").wait(2.0)

        action_type, seconds = builder.steps[0]["action"]
        assert action_type == "wait"
        assert seconds == 2.0

    def test_wait_for_action(self):
        """wait_for 动作"""
        page = MagicMock()
        builder = StepBuilder(page)
        builder.step("等待元素").wait_for(".selector", timeout=5000)

        action_type, params = builder.steps[0]["action"]
        assert action_type == "wait_for"
        assert params["selector"] == ".selector"
        assert params["timeout"] == 5000


class TestStepBuilderRetry:
    """Tests for StepBuilder retry/delay configuration."""

    def test_retries(self):
        """retries 设置重试次数"""
        page = MagicMock()
        builder = StepBuilder(page)
        builder.step("步骤").retries(5)
        assert builder.steps[0]["retries"] == 5

    def test_delay(self):
        """delay 设置延迟"""
        page = MagicMock()
        builder = StepBuilder(page)
        builder.step("步骤").delay(1.5)
        assert builder.steps[0]["delay"] == 1.5

    def test_on_error(self):
        """on_error 设置错误回调"""
        page = MagicMock()
        callback = MagicMock()
        builder = StepBuilder(page)
        builder.step("步骤").on_error(callback)
        assert builder.steps[0]["on_error"] is callback


class TestStepBuilderRun:
    """Tests for StepBuilder.run."""

    def test_run_empty_steps(self):
        """run 空步骤"""
        page = _make_page()
        builder = StepBuilder(page)
        result = builder.run()
        assert result is True

    def test_run_single_step(self):
        """run 单步骤"""
        page = _make_page()
        builder = StepBuilder(page)
        builder.step("等待").wait(0.01)
        result = builder.run()
        assert result is True

    def test_run_multiple_steps(self):
        """run 多步骤"""
        page = _make_page()
        builder = StepBuilder(page)
        builder.step("等待1").wait(0.01)
        builder.step("等待2").wait(0.01)
        result = builder.run()
        assert result is True

    def test_run_with_click_first(self):
        """run 包含 click_first"""
        page = _make_page()
        builder = StepBuilder(page)
        builder.step("点击").click_first()
        result = builder.run()
        assert isinstance(result, bool)

    def test_run_stop_on_error_with_no_elements(self):
        """run stop_on_error 模式"""
        page = MagicMock()
        # Make click_first fail
        page.query_selector_all.return_value = []

        builder = StepBuilder(page)
        builder.step("步骤").click_first()
        result = builder.run(stop_on_error=True)
        # Should not crash, just continue or handle error
        assert isinstance(result, bool)


class TestStepBuilderChain:
    """Tests for StepBuilder chaining API."""

    def test_chain_step_click(self):
        """链式定义步骤"""
        page = MagicMock()
        builder = StepBuilder(page)
        builder \
            .step("步骤1").click("按钮1") \
            .step("步骤2").click(index=0) \
            .step("步骤3").wait(1.0)

        assert len(builder.steps) == 3
        assert builder.steps[0]["action"][0] == "click"
        assert builder.steps[1]["action"][0] == "click"
        assert builder.steps[2]["action"][0] == "wait"
