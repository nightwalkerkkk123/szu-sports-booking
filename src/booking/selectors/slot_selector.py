"""
灵活时间段选择器 - 支持多种匹配方式
"""

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class SlotUnavailableError(Exception):
    """Raised when trying to select an unavailable slot."""

    pass


class FlexibleSlotSelector:
    """
    时间段选择器 - 支持多种匹配方式

    示例:
        selector = FlexibleSlotSelector(page)
        selector.select("19:00-20:00")           # 精确匹配
        selector.select("19:00")                 # 匹配开始时间
        selector.select(index=3)                 # 索引选择
        selector.select(contains="19:")           # 包含匹配
    """

    # 默认的时间段容器选择器
    DEFAULT_CONTAINER_SELECTOR = "div.group-2, div[class*='time'], div[class*='slot']"

    def __init__(self, page: Page, container_selector: str = None):
        self.page = page
        self.container_selector = container_selector or self.DEFAULT_CONTAINER_SELECTOR

    def _is_available(self, container) -> bool:
        """检查选项是否可用。

        颜色优先于子元素判断：
        - rgb(134, 144, 156) = 不可用
        - rgb(162, 10, 71) 或 rgb(29, 33, 41) = 可用
        颜色不明确时，用子元素判断：
        - rectangle-4 / frame-child1 = 可用
        - ellipse = 不可用
        """
        try:
            # 方法1：检查 div.element 的颜色样式（优先）
            text_el = container.query_selector("div.element")
            if text_el:
                style = text_el.get_attribute("style") or ""
                if "rgb(134, 144, 156)" in style:
                    return False
                if "rgb(162, 10, 71)" in style or "rgb(29, 33, 41)" in style:
                    return True

            # 方法2：颜色不明确时，检查子元素类型
            if container.query_selector("div.frame-child1"):
                return True
            if container.query_selector("div.rectangle-4"):
                return True
            if container.query_selector("div.ellipse"):
                return False

            # 默认返回 True（保守策略）
            return True
        except Exception:
            return True

    def select(
        self,
        target: str | int = None,
        *,
        index: int = None,
        contains: str = None,
        regex: str = None,
        value: str = None,
        container_selector: str = None,
        check_availability: bool = True,
    ) -> bool:
        """
        选择时间段

        参数:
            target: 精确匹配的文本或索引
            index: 按索引选择
            contains: 包含文本匹配
            regex: 正则匹配
            value: 按 value 属性匹配
            container_selector: 容器选择器（覆盖默认）
            check_availability: 是否检查可用性（默认True）

        返回:
            bool: 是否选择成功

        异常:
            SlotUnavailableError: 当 check_availability=True 且选项不可用时
        """
        selector = container_selector or self.container_selector

        # 获取所有选项
        options = self.get_all(selector, check_availability=check_availability)
        if not options:
            print("未找到任何时间段选项")
            return False

        # 打印可用选项（调试用）
        available_opts = [o for o in options if o.get("available", True)]
        print(f"可用时间段 ({len(available_opts)}/{len(options)} 个):")
        for i, opt in enumerate(options):
            status = "[OK]" if opt.get("available", True) else "[X]"
            print(f"  [{i}] {status} {opt['text']} (value: {opt['value']})")

        # 根据 target 类型找到匹配项
        matched = self._find_matched_option(options, target, index, contains, regex, value)

        if matched:
            # 检查可用性
            if check_availability and not matched.get("available", True):
                raise SlotUnavailableError(f"选项不可用: {matched['text']} (已满员或已过期)")

            print(f"正在选择时间段: {matched['text']}")
            matched["element"].click()
            print(f"已选择时间段: {matched['text']}")
            return True
        else:
            raise SlotUnavailableError(f"未找到匹配的时间段: {target}")

    def select_first(self, container_selector: str = None) -> bool:
        """选择第一个时间段"""
        return self.select(index=0, container_selector=container_selector)

    def select_last(self, container_selector: str = None) -> bool:
        """选择最后一个时间段"""
        options = self.get_all(container_selector or self.container_selector)
        if options:
            options[-1]["element"].click()
            return True
        return False

    def get_all(
        self, container_selector: str = None, check_availability: bool = True
    ) -> list[dict]:
        """
        获取所有可用时间段

        参数:
            container_selector: 容器选择器
            check_availability: 是否检查可用性

        返回:
            List[dict]: [{text, value, element, available}, ...]
        """
        selector = container_selector or self.container_selector

        try:
            # 等待 DOM 加载完成（不要等 networkidle，可能导致超时）
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)

            # 直接查找容器
            containers = self.page.query_selector_all(selector)
            if not containers:
                # 尝试备用选择器
                alt_selectors = ["div.group-2", "div.group", "div.time-slot", "div[class*='slot']"]
                for alt in alt_selectors:
                    containers = self.page.query_selector_all(alt)
                    if containers:
                        break

            options = []
            for container in containers:
                try:
                    # 提取文本
                    text_el = container.query_selector(
                        'div[class*="text"], span[class*="text"], label, div.element'
                    )
                    if not text_el:
                        continue

                    text = text_el.text_content().strip()
                    if not text:
                        continue

                    # 提取 value
                    radio = container.query_selector('input[type="radio"]')
                    value = radio.get_attribute("value") if radio else None

                    # 检查可用性
                    available = True
                    if check_availability:
                        available = self._is_available(container)

                    options.append(
                        {"text": text, "value": value, "element": container, "available": available}
                    )
                except Exception:
                    continue

            return options

        except Exception as e:
            print(f"获取时间段失败: {e}")
            raise SlotUnavailableError(f"获取时间段失败: {e}") from e

    def _find_matched_option(
        self,
        options: list[dict],
        target: str | int = None,
        index: int = None,
        contains: str = None,
        regex: str = None,
        value: str = None,
    ) -> dict | None:
        """找到匹配的时间段选项"""
        import re

        # 索引优先
        if index is not None:
            if 0 <= index < len(options):
                return options[index]
            print(f"索引 {index} 超出范围 (共 {len(options)} 个)")
            return None

        # 按 value 匹配
        if value is not None:
            for opt in options:
                if opt["value"] == value:
                    return opt
            return None

        # 正则匹配
        if regex is not None:
            for opt in options:
                if re.search(regex, opt["text"]) or (
                    opt["value"] and re.search(regex, opt["value"])
                ):
                    return opt
            return None

        # 包含匹配
        if contains is not None:
            for opt in options:
                if contains in opt["text"] or (opt["value"] and contains in opt["value"]):
                    return opt
            return None

        # 精确匹配（target 是字符串）
        if target is not None and isinstance(target, str):
            for opt in options:
                if opt["text"] == target:
                    return opt
                if opt["value"] == target:
                    return opt
                # 部分匹配（如 "19:00" 匹配 "19:00-20:00"）
                if target in opt["text"]:
                    return opt
            return None

        # 索引（target 是 int）
        if isinstance(target, int):
            if 0 <= target < len(options):
                return options[target]
            return None

        return None

    def wait_for_slots(self, timeout: int = 15000) -> bool:
        """等待时间段加载完成"""
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout)
            selector = self.container_selector or "div.group-2, div[class*='time']"
            self.page.wait_for_selector(selector, timeout=timeout // 2)
            return True
        except PlaywrightTimeoutError:
            print("等待时间段超时")
            return False


class TimeSlotMatcher:
    """
    时间段匹配器 - 专门处理时间段格式的匹配

    支持的格式:
        - "19:00-20:00"   完整时间段
        - "19:00"         开始时间
        - "19:00-20:00:30" 包含秒的时间（少见）
        - "19:30"         任意包含的时间
    """

    @staticmethod
    def match(text: str, target: str) -> bool:
        """
        判断 text 是否匹配 target

        参数:
            text: 时间段文本，如 "19:00-20:00"
            target: 目标文本，如 "19:00"

        返回:
            bool: 是否匹配
        """
        text = text.strip()
        target = target.strip()

        # 完全匹配
        if text == target:
            return True

        # 开始时间匹配（如 "19:00" 匹配 "19:00-20:00"）
        if "-" in text:
            start = text.split("-")[0].strip()
            if start == target:
                return True

        # 包含匹配
        if target in text:
            return True

        return False

    @staticmethod
    def extract_time(text: str) -> tuple:
        """提取时间段的开始和结束时间"""
        import re

        match = re.search(r"(\d{1,2}:\d{2})", text)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def parse(time_str: str) -> tuple:
        """解析时间字符串为 (hour, minute)"""
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])
