"""确认预约页 selector - 封装确认页结构知识 + 关键字匹配"""


class ConfirmPage:
    CONFIRM_SELECTORS = (
        'button:has-text("确认")',
        'button:has-text("提交")',
        'button:has-text("预约")',
        'div:has-text("确认预约")',
        "#confirm",
        "#submit",
    )

    FAIL_KEYWORDS = (
        "操作过于频繁",
        "预约失败",
        "已预约过",
        "名额已满",
        "不可预约",
        "已满员",
        "已达上限",
    )

    SUCCESS_KEYWORDS = (
        "预约成功",
        "提交成功",
        "操作成功",
    )

    POST_CLICK_WAIT_MS = 2000
    SELECTOR_TIMEOUT = 5000

    def __init__(self, page, chain):
        self.page = page
        self.chain = chain

    def confirm(self) -> bool:
        """尝试 6 个 selector 找到确认按钮，点击后匹配关键字；返回是否成功"""
        for selector in self.CONFIRM_SELECTORS:
            try:
                btn = self.page.wait_for_selector(
                    selector, state="visible", timeout=self.SELECTOR_TIMEOUT
                )
                if btn is None:
                    continue
                btn.click()
                self.page.wait_for_timeout(self.POST_CLICK_WAIT_MS)
                body = self.chain.get_body_text()
                if any(kw in body for kw in self.FAIL_KEYWORDS):
                    return False
                if any(kw in body for kw in self.SUCCESS_KEYWORDS):
                    return True
                return False
            except Exception:
                continue
        return False
