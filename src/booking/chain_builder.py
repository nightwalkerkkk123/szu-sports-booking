"""
链式选择器 - 高度抽象的页面交互接口
支持文本、索引、正则、包含等多种匹配方式
"""

import logging

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger("booking")


class ClickError(Exception):
    """Raised when click operation fails."""

    pass


class Chain:
    """
    链式选择器，通过链式调用完成页面交互

    示例:
        Chain(page).click("粤海校区").click("网球").click(index=0)
    """

    def __init__(self, page: Page):
        self.page = page
        self.history = []

    def click(
        self,
        target: str | int = None,
        *,
        selector: str = None,
        index: int = None,
        contains: str = None,
        regex: str = None,
        timeout: int = 10000,
    ) -> "Chain":
        """
        点击元素，支持多种匹配方式

        参数:
            target: 精确匹配的文本或索引
            selector: CSS 选择器（直接按 selector 点击，区别于文字匹配）
            index: 按索引选择 (覆盖 target)
            contains: 包含文本匹配
            regex: 正则匹配，如 r"\\d{2}:\\d{2}"
            timeout: 超时时间(ms)

        示例:
            Chain(page).click("粤海校区")           # 精确匹配
            Chain(page).click(index=0)              # 第1个
            Chain(page).click(contains="网球")       # 包含"网球"
            Chain(page).click(regex=r"\\d{2}:\\d{2}")   # 正则匹配时间格式
            Chain(page).click(selector="#login_submit")  # CSS 选择器点击
        """
        if selector is not None:
            el = self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            if el is None:
                error_msg = f"未找到元素: {selector}"
                print(error_msg)
                logger.error("未找到元素", extra={"selector": selector})
                raise ClickError(error_msg)
            el.click()
            self.history.append(("click_selector", selector))
            print(f"已点击: {selector}")
            return self

        element = self._find_element(
            target=target, index=index, contains=contains, regex=regex, timeout=timeout
        )

        if element:
            element.click()
            self.history.append(("click", target))
            print(f"已点击: {target}")
        else:
            error_msg = f"未找到元素: {target}"
            print(error_msg)
            logger.error("未找到元素", extra={"target": target})
            raise ClickError(error_msg)

        return self

    def click_first(self, timeout: int = 5000) -> "Chain":
        """点击第一个可用元素"""
        try:
            elements = self.page.query_selector_all(
                'div[class*="group"], div[class*="item"], div[class*="option"]'
            )
            if elements:
                elements[0].click()
                self.history.append(("click_first", None))
                print("已点击第1个元素")
        except Exception as e:
            print(f"点击第1个元素失败: {e}")
        return self

    def wait(self, seconds: float) -> "Chain":
        """等待指定秒数"""
        import time

        time.sleep(seconds)
        return self

    def wait_for(self, selector: str, timeout: int = 10000, state: str = None) -> "Chain":
        """等待元素出现

        参数:
            selector: CSS 选择器
            timeout: 超时时间（ms）
            state: 等待的状态（"visible" / "attached" / "hidden" / "detached"）
        """
        try:
            kwargs = {"timeout": timeout}
            if state is not None:
                kwargs["state"] = state
            self.page.wait_for_selector(selector, **kwargs)
        except PlaywrightTimeoutError:
            print(f"等待元素超时: {selector}")
        return self

    def type(self, selector: str, text: str) -> "Chain":
        """输入文本"""
        try:
            element = self.page.wait_for_selector(selector, timeout=10000)
            element.fill(text)
            self.history.append(("type", selector))
        except Exception as e:
            print(f"输入失败: {e}")
        return self

    def select_radio(self, value: str, container_selector: str = "div.group") -> "Chain":
        """选择单选按钮"""
        try:
            containers = self.page.query_selector_all(container_selector)
            for container in containers:
                radio = container.query_selector('input[type="radio"]')
                if radio and radio.get_attribute("value") == value:
                    label = container.query_selector("label")
                    if label:
                        label.click()
                    else:
                        radio.click()
                    print(f"已选择 radio: {value}")
                    break
        except Exception as e:
            print(f"选择 radio 失败: {e}")
        return self

    def get_all(self, container_selector: str = "div.group") -> list[dict]:
        """获取所有可用选项"""
        try:
            containers = self.page.query_selector_all(container_selector)
            options = []
            for container in containers:
                text_el = container.query_selector('div[class*="text"], span[class*="text"], label')
                radio = container.query_selector('input[type="radio"]')
                if text_el:
                    options.append(
                        {
                            "text": text_el.text_content().strip(),
                            "value": radio.get_attribute("value") if radio else None,
                            "element": container,
                        }
                    )
            return options
        except Exception as e:
            print(f"获取选项失败: {e}")
            return []

    def print_all(self, container_selector: str = "div.group") -> "Chain":
        """打印所有可用选项（调试用）"""
        options = self.get_all(container_selector)
        print("\n可用选项:")
        for i, opt in enumerate(options):
            print(f"  [{i}] {opt['text']} (value: {opt['value']})")
        print()
        return self

    def undo(self) -> "Chain":
        """撤销上一步操作（记录历史）"""
        if self.history:
            self.history.pop()
        return self

    def get_body_text(self) -> str:
        """读 body 文本（confirm 关键字匹配用）

        返回页面 body 的 inner_text；异常时返回空串。
        """
        try:
            return self.page.inner_text("body")
        except Exception as e:
            print(f"读 body 文本失败: {e}")
            return ""

    def evaluate(self, script: str):
        """执行 JS 脚本（login 的 readonly 移除 hack 用）

        返回 evaluate 的结果；异常时透传。
        """
        return self.page.evaluate(script)

    def press_key(self, key: str) -> "Chain":
        """模拟键盘按键（login 的 Tab 用）"""
        self.page.keyboard.press(key)
        return self

    def wait_for_load_state(self, state: str = "domcontentloaded", timeout: int = 30000) -> "Chain":
        """等待页面加载状态（login 等 DOM 加载用）

        超时静默（与 BookingClient.login 原行为一致）。
        """
        try:
            self.page.wait_for_load_state(state, timeout=timeout)
        except Exception:
            pass
        return self

    def clear_cookies(self) -> "Chain":
        """清除浏览器 cookies（switch_account 用）

        异常时静默（与 BookingClient 原 switch_account 行为一致）。
        """
        try:
            self.page.context.clear_cookies()
        except Exception as e:
            print(f"清除 cookies 失败: {e}")
        return self

    def _find_element(
        self,
        target: str | int = None,
        index: int = None,
        contains: str = None,
        regex: str = None,
        timeout: int = 10000,
    ):
        """根据匹配方式找到元素"""
        # 索引优先
        if index is not None:
            return self._find_by_index(index, timeout)

        # 包含文本
        if contains:
            return self._find_by_contains(contains, timeout)

        # 正则匹配
        if regex:
            return self._find_by_regex(regex, timeout)

        # 精确匹配或默认点击第一个
        if target is not None:
            if isinstance(target, int):
                return self._find_by_index(target, timeout)
            else:
                return self._find_by_text(target, timeout)

        # 无参数，点击第一个
        return self._find_first(timeout)

    def _find_by_text(self, text: str, timeout: int = 10000):
        """精确匹配文本"""
        try:
            # 尝试多种选择器
            selectors = [
                f'text="{text}"',
                f'div:has-text("{text}")',
                f'span:has-text("{text}")',
                f'label:has-text("{text}")',
                f'button:has-text("{text}")',
            ]
            for selector in selectors:
                try:
                    return self.page.wait_for_selector(
                        selector, state="visible", timeout=timeout // len(selectors)
                    )
                except:  # noqa: E722
                    continue
            return None
        except Exception as e:
            print(f"精确匹配失败: {e}")
            return None

    def _find_by_index(self, index: int, timeout: int = 10000):
        """按索引选择"""
        try:
            # 查找所有可能的容器元素
            selectors = [
                'div[class*="group"]',
                'div[class*="item"]',
                'div[class*="option"]',
                'div[class*="card"]',
            ]
            for selector in selectors:
                elements = self.page.query_selector_all(selector)
                if elements and 0 <= index < len(elements):
                    return elements[index]
            return None
        except Exception as e:
            print(f"索引选择失败: {e}")
            return None

    def _find_by_contains(self, text: str, timeout: int = 10000):
        """包含文本匹配"""
        try:
            selectors = [
                f'div:has-text("{text}")',
                f'span:has-text("{text}")',
                f'label:has-text("{text}")',
                f'button:has-text("{text}")',
            ]
            for selector in selectors:
                try:
                    return self.page.wait_for_selector(
                        selector, state="visible", timeout=timeout // len(selectors)
                    )
                except:  # noqa: E722
                    continue
            return None
        except Exception as e:
            print(f"包含匹配失败: {e}")
            return None

    def _find_by_regex(self, pattern: str, timeout: int = 10000):
        """正则匹配"""
        import re

        try:
            elements = self.page.query_selector_all(
                'div[class*="group"], div[class*="item"], div[class*="option"]'
            )
            for el in elements:
                text = el.text_content() or ""
                if re.search(pattern, text):
                    return el
            return None
        except Exception as e:
            print(f"正则匹配失败: {e}")
            return None

    def _find_first(self, timeout: int = 5000):
        """找到第一个可点击元素"""
        try:
            selectors = [
                'div[class*="group"]',
                'div[class*="item"]',
                'div[class*="option"]',
                'div[class*="card"]',
            ]
            for selector in selectors:
                elements = self.page.query_selector_all(selector)
                if elements:
                    return elements[0]
            return None
        except Exception as e:
            print(f"查找第1个元素失败: {e}")
            return None
