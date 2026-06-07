"""登录页 selector - 封装登录页结构知识"""


class LoginPage:
    USERNAME_SELECTOR = "#username"
    PASSWORD_SELECTOR = "#password"
    SUBMIT_SELECTOR = "#login_submit"
    LOGGED_IN_INDICATOR = ".bh-btn"

    REMOVE_READONLY_SCRIPT = """
        el = document.querySelector('#password');
        if (el) {
            el.removeAttribute('readonly');
            el.classList.remove('no-auto-input');
        }
    """

    USERNAME_FILL_TIMEOUT = 10000
    PASSWORD_WAIT_TIMEOUT = 20000
    LOAD_STATE_TIMEOUT = 30000
    LOGGED_IN_WAIT_TIMEOUT = 15000

    def __init__(self, page, chain):
        self.page = page
        self.chain = chain

    def login(self, username: str, password: str) -> bool:
        """填表 + 提交 + 等待登录完成；返回是否成功"""
        self.chain.type(self.USERNAME_SELECTOR, username)
        self.chain.press_key("Tab")
        self.chain.wait_for(
            self.PASSWORD_SELECTOR, state="visible", timeout=self.PASSWORD_WAIT_TIMEOUT
        )
        self.chain.evaluate(self.REMOVE_READONLY_SCRIPT)
        self.chain.type(self.PASSWORD_SELECTOR, password)
        self.chain.click(selector=self.SUBMIT_SELECTOR)
        self.chain.wait_for_load_state("domcontentloaded", timeout=self.LOAD_STATE_TIMEOUT)
        return self.chain.wait_for(
            self.LOGGED_IN_INDICATOR, state="visible", timeout=self.LOGGED_IN_WAIT_TIMEOUT
        )
