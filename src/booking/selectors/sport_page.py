"""体育项目选择页 selector - 封装项目 wrapper + 名称匹配"""


class SportPage:
    WRAPPER_SELECTOR = "div.text-wrapper-7"
    CLICK_TIMEOUT = 10000

    def __init__(self, page, chain):
        self.page = page
        self.chain = chain

    def select(self, name: str) -> None:
        """按名称选择体育项目

        构造 'div.text-wrapper-7:has-text("{name}")' 选择器并走 Chain.click(selector=)。
        找不到时由 Chain 抛 ClickError。
        """
        selector = f'{self.WRAPPER_SELECTOR}:has-text("{name}")'
        self.chain.click(selector=selector, timeout=self.CLICK_TIMEOUT)
