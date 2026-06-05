"""
灵活场地选择器 - 支持多级选择（场馆类型 -> 具体场地）
"""

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class FlexibleVenueSelector:
    """
    场地选择器 - 支持多级选择

    示例:
        selector = FlexibleVenueSelector(page)

        # 选择场馆类型
        selector.select("羽毛球")           # 按名称
        selector.select(index=0)            # 按索引

        # 或者精确到具体场地
        selector.select("羽毛球1场")
    """

    # 默认的场地容器选择器
    DEFAULT_CONTAINER_SELECTOR = "div.venue-item, div[class*='venue'], div[class*='court']"

    def __init__(self, page: Page, container_selector: str = None):
        self.page = page
        self.container_selector = container_selector or self.DEFAULT_CONTAINER_SELECTOR

    def select(
        self, venue_name: str = None, *, index: int = None, contains: str = None, regex: str = None
    ) -> bool:
        """
        选择场地

        参数:
            venue_name: 场地名称，如 "羽毛球1场"
            index: 按索引选择
            contains: 包含文本匹配
            regex: 正则匹配

        返回:
            bool: 是否选择成功
        """
        # 获取所有可用场地
        venues = self.get_all()
        if not venues:
            print("未找到任何场地")
            return False

        # 打印可用场地（调试用）
        print(f"可用场地 ({len(venues)} 个):")
        for i, v in enumerate(venues):
            print(f"  [{i}] {v['text']} (value: {v['value']})")

        # 找到匹配的场地
        matched = self._find_matched_venue(venues, venue_name, index, contains, regex)

        if matched:
            print(f"正在选择场地: {matched['text']}")
            matched["element"].click()
            print(f"已选择场地: {matched['text']}")
            return True
        else:
            print(f"未找到匹配的场地: {venue_name}")
            return False

    def select_first(self) -> bool:
        """选择第一个场地"""
        return self.select(index=0)

    def get_all(self, container_selector: str = None) -> list[dict]:
        """
        获取所有可用场地

        返回:
            List[dict]: [{text, value, element}, ...]
        """
        selector = container_selector or self.container_selector

        try:
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # 尝试多种选择器
            selectors_to_try = [
                selector,
                "div.venue-item",
                "div[class*='venue']",
                "div[class*='court']",
                "div[class*='field']",
                "div.item:has(input[type='radio'])",
            ]

            containers = []
            for sel in selectors_to_try:
                containers = self.page.query_selector_all(sel)
                if containers:
                    break

            venues = []
            for container in containers:
                try:
                    text_el = container.query_selector(
                        'div[class*="text"], span, label, div.venue-name'
                    )
                    if not text_el:
                        continue

                    text = text_el.text_content().strip()
                    if not text:
                        continue

                    radio = container.query_selector('input[type="radio"]')
                    value = radio.get_attribute("value") if radio else None

                    venues.append({"text": text, "value": value, "element": container})
                except Exception:
                    continue

            return venues

        except Exception as e:
            print(f"获取场地失败: {e}")
            return []

    def _find_matched_venue(
        self,
        venues: list[dict],
        venue_name: str = None,
        index: int = None,
        contains: str = None,
        regex: str = None,
    ) -> dict | None:
        """找到匹配的场地"""
        import re

        # 索引优先
        if index is not None:
            if 0 <= index < len(venues):
                return venues[index]
            return None

        # 精确匹配名称
        if venue_name is not None:
            for v in venues:
                if v["text"] == venue_name:
                    return v
                # 部分匹配（如 "羽毛球" 匹配 "羽毛球1场"）
                if venue_name in v["text"]:
                    return v
            return None

        # 包含匹配
        if contains is not None:
            for v in venues:
                if contains in v["text"]:
                    return v
            return None

        # 正则匹配
        if regex is not None:
            for v in venues:
                if re.search(regex, v["text"]):
                    return v
            return None

        return None

    def wait_for_venues(self, timeout: int = 15000) -> bool:
        """等待场地列表加载完成"""
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout)
            self.page.wait_for_selector(self.container_selector, timeout=timeout // 2)
            return True
        except PlaywrightTimeoutError:
            print("等待场地超时")
            return False


class VenueHierarchySelector:
    """
    场地层级选择器 - 支持场馆 -> 场地二级选择

    示例:
        selector = VenueHierarchySelector(page)

        # 选择羽毛球 -> 场地1
        selector.select_category("羽毛球")
        selector.select_venue("场地1")

        # 或者一步到位
        selector.select_full("羽毛球场地1")
    """

    def __init__(self, page: Page):
        self.page = page
        self.category_selector = FlexibleVenueSelector(page)
        self.venue_selector = FlexibleVenueSelector(page)

    def select_category(self, name: str = None, index: int = None) -> bool:
        """选择场馆类型（如羽毛球、网球）"""
        if name:
            self.category_selector.select(name)
        elif index is not None:
            self.category_selector.select(index=index)
        return True

    def select_venue(self, name: str = None, index: int = None) -> bool:
        """选择具体场地"""
        if name:
            self.venue_selector.select(name)
        elif index is not None:
            self.venue_selector.select(index=index)
        return True

    def select_full(self, full_name: str) -> bool:
        """一步选择完整的场地名称"""
        return self.venue_selector.select(full_name)

    def get_categories(self) -> list[dict]:
        """获取所有场馆类型"""
        return self.category_selector.get_all()

    def get_venues(self) -> list[dict]:
        """获取所有具体场地"""
        return self.venue_selector.get_all()
