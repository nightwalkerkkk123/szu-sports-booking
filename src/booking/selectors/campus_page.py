"""校区选择页 selector - 封装校区按钮 + 名称匹配"""


class CampusPage:
    BUTTON_SELECTOR = ".bh-btn"
    CLICK_TIMEOUT = 10000

    def __init__(self, page, chain):
        self.page = page
        self.chain = chain

    def select(self, name: str) -> None:
        """按名称选择校区

        构造 '.bh-btn:has-text("{name}")' 选择器并走 Chain.click(selector=)。
        找不到时由 Chain 抛 ClickError。
        """
        selector = f'{self.BUTTON_SELECTOR}:has-text("{name}")'
        self.chain.click(selector=selector, timeout=self.CLICK_TIMEOUT)
