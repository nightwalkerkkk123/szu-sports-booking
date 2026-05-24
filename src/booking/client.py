"""
预约客户端 - 统一的链式调用接口
整合浏览器管理、登录、选择器等功能
"""
import logging
from typing import Union, Optional
from .chain_builder import Chain, ClickError
from .step_builder import StepBuilder
from .selectors.slot_selector import FlexibleSlotSelector, SlotUnavailableError
from .selectors.venue_selector import FlexibleVenueSelector

logger = logging.getLogger("booking.client")

class BookingClient:
    """
    预约客户端 - 链式调用接口

    示例:
        client = BookingClient()
        client.login("2023150090", "11282577")
        client.select_campus("粤海校区")
        client.select_sport("网球")
        client.select_date(0)
        client.select_time_slot("19:00-20:00")
        client.confirm()

    或链式调用:
        BookingClient() \\
            .login("2023150090", "11282577") \\
            .select_campus("粤海校区") \\
            .select_sport("网球") \\
            .select_time_slot("19:00-20:00") \\
            .confirm()
    """

    def __init__(self, headless: bool = False, use_fake_browser: bool = False,
                 trace_id: str = None):
        self.page = None
        self.browser = None
        self.headless = headless
        self._use_fake_browser = use_fake_browser
        self._config = {}
        self._tracker = None  # StepTracker, 延迟初始化

        # 初始化组件
        self.chain = None
        self.step_builder = None
        self.slot_selector = None
        self.venue_selector = None

        # 如果提供了 trace_id，初始化步骤追踪
        if trace_id:
            from booking.observability.step_tracker import StepTracker
            self._tracker = StepTracker(trace_id)

    def enable_tracking(self, trace_id: str) -> "BookingClient":
        """启用步骤追踪"""
        from booking.observability.step_tracker import StepTracker
        self._tracker = StepTracker(trace_id)
        return self

    def get_tracker(self):
        """获取 StepTracker 实例"""
        return self._tracker

    def _ensure_browser(self):
        """确保浏览器已初始化"""
        if self.browser is None:
            if self._use_fake_browser:
                from booking.browser.fake_browser import FakeBrowserLifecycle
                self.browser = FakeBrowserLifecycle()
                self.browser.launch(headless=self.headless)
                self.page = self.browser.new_page()
                self._init_selectors()
            else:
                from cloakbrowser import launch
                self.browser = launch(headless=self.headless)
                self.page = self.browser.new_page()
                self._init_selectors()
        return self.browser

    def _init_selectors(self):
        """初始化选择器"""
        self.chain = Chain(self.page)
        self.step_builder = StepBuilder(self.page)
        self.slot_selector = FlexibleSlotSelector(self.page)
        self.venue_selector = FlexibleVenueSelector(self.page)

    def _ensure_page_loaded(self, url: str):
        """确保页面已加载"""
        self._ensure_browser()
        if self.page.url != url:
            self.page.goto(url)
            self.page.wait_for_load_state("domcontentloaded")

    # ===== 浏览器控制 =====

    def launch(self, headless: bool = None) -> "BookingClient":
        """启动浏览器"""
        if headless is not None:
            self.headless = headless
        self._ensure_browser()
        return self

    def set_browser(self, browser) -> "BookingClient":
        """设置自定义浏览器实例（用于干跑模式）"""
        self.browser = browser
        self.page = browser.page if hasattr(browser, 'page') else browser
        self._init_selectors()
        return self

    def open(self, url: str) -> "BookingClient":
        """打开页面"""
        self._ensure_browser()
        self.page.goto(url)
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None

    # ===== 登录 =====

    def login(self, username: str, password: str) -> "BookingClient":
        """登录"""
        self._ensure_browser()

        print(f"\n正在登录: {username}")
        logger.info("开始登录", extra={"username": username})
        if self._tracker:
            self._tracker.start_step("用户登录", details={"username": username})

        # 输入用户名
        self.page.fill('#username', username)
        self.page.keyboard.press("Tab")

        # 输入密码
        self.page.wait_for_selector('#password', state="visible", timeout=20000)
        self.page.evaluate("""
            el = document.querySelector('#password');
            if (el) {
                el.removeAttribute('readonly');
                el.classList.remove('no-auto-input');
            }
        """)
        self.page.fill('#password', password)

        # 点击登录
        self.page.click('#login_submit')

        # 等待登录完成，跳转到预约页面
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        except Exception:
            pass  # 超时继续，可能已经跳转

        # 等待校区选择按钮出现
        try:
            self.page.wait_for_selector('.bh-btn', state="visible", timeout=15000)
        except Exception:
            pass  # 超时继续

        print("登录完成")
        logger.info("登录完成", extra={"username": username})
        if self._tracker:
            self._tracker.step_success()
        return self

    def switch_account(self, username: str, password: str = None) -> "BookingClient":
        """切换账号（不重新打开浏览器）

        登出当前账号并用新账号登录。
        """
        # 如果密码为空，保留当前会话
        if password is None:
            print(f"切换到账号: {username}（使用当前会话）")
            return self

        # 否则登出并重新登录
        print(f"切换账号: {username}")

        # 1. 登出 CAS
        try:
            logout_url = "https://authserver.szu.edu.cn/authserver/logout"
            print(f"登出中...")
            self.page.goto(logout_url)
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass  # 登出失败，继续尝试登录

        # 2. 清除 cookies
        try:
            self.page.context.clear_cookies()
        except Exception:
            pass

        # 3. 导航回登录页
        try:
            login_url = "https://authserver.szu.edu.cn/authserver/login"
            self.page.goto(login_url)
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        # 4. 用新账号登录
        return self.login(username, password)

    # ===== 选择器方法 =====

    def select_campus(self, name: str = None, index: int = None) -> "BookingClient":
        """选择校区"""
        self._ensure_browser()

        if index is not None:
            self.chain.click(index=index)
        elif name:
            # Use CSS selector directly - .bh-btn contains the text
            try:
                element = self.page.wait_for_selector(f'.bh-btn:has-text("{name}")', state="visible", timeout=10000)
                element.click()
                print(f"已点击: {name}")
                logger.info("选择校区", extra={"campus": name})
            except Exception as e:
                print(f"未找到元素: {name}")
                raise ClickError(f"未找到元素: {name}")
        else:
            self.chain.click_first()

        return self.wait(1)

    def select_sport(self, name: str = None, index: int = None) -> "BookingClient":
        """选择体育项目"""
        self._ensure_browser()

        if index is not None:
            self.chain.click(index=index)
        elif name:
            # Use CSS selector directly - div.text-wrapper-7 contains sport name
            try:
                element = self.page.wait_for_selector(f'div.text-wrapper-7:has-text("{name}")', state="visible", timeout=10000)
                element.click()
                print(f"已点击: {name}")
                logger.info("选择项目", extra={"sport": name})
            except Exception as e:
                print(f"未找到元素: {name}")
                raise ClickError(f"未找到元素: {name}")
        else:
            self.chain.click_first()

        return self.wait(1)

    def select_venue(self, name: str = None, index: int = None) -> "BookingClient":
        """选择场地（选择时间段后场地选项才会出现）"""
        self._ensure_browser()

        # 场地和时间段使用相同的 div.group-2 结构
        # 但场地选择需要检查可用性
        if name:
            # 精确匹配场地名称
            self.slot_selector.select(
                target=name,
                container_selector="div.group-2",
                check_availability=True
            )
        elif index is not None:
            # 按索引选择
            self.slot_selector.select(
                index=index,
                container_selector="div.group-2",
                check_availability=True
            )
        else:
            # 默认选择第一个可用的场地
            options = self.slot_selector.get_all("div.group-2", check_availability=True)
            available_options = [o for o in options if o.get("available", True)]

            # 场地和可用时间段都有 frame-child1，无法用它区分。
            # 唯一可靠区分：场地文本不包含时间格式 HH:MM-HH:MM
            import re
            time_pattern = re.compile(r"\d{2}:\d{2}-\d{2}:\d{2}")
            venue_options = [
                o for o in available_options
                if not time_pattern.search(o.get("text", ""))
            ]

            if not venue_options:
                raise SlotUnavailableError("没有可用的场地")

            first_available = venue_options[0]
            print(f"选择可用场地: {first_available['text']}")
            first_available["element"].click()

        return self.wait(1)

    def select_date(self, selector: Union[int, str] = 0) -> "BookingClient":
        """
        选择日期

        参数:
            selector: 0=今天, 1=明天, 2=后天 或 "2025-05-25" 格式的日期
        """
        self._ensure_browser()

        self.slot_selector.select(selector, container_selector="div.group-9")
        return self.wait(1)

    def select_time_slot(
        self,
        target: Union[str, int] = None,
        *,
        index: int = None,
        contains: str = None,
        regex: str = None
    ) -> "BookingClient":
        """
        选择时间段

        参数:
            target: 精确匹配文本，如 "19:00-20:00"
            index: 按索引选择
            contains: 包含匹配
            regex: 正则匹配
        """
        self._ensure_browser()

        self.slot_selector.select(
            target=target,
            index=index,
            contains=contains,
            regex=regex,
            container_selector="div.group-2"
        )
        return self.wait(1)

    def confirm(self) -> bool:
        """确认预约"""
        self._ensure_browser()

        print("\n正在确认预约...")

        try:
            # 尝试多种确认按钮选择器
            confirm_selectors = [
                'button:has-text("确认")',
                'button:has-text("提交")',
                'button:has-text("预约")',
                'div:has-text("确认预约")',
                '#confirm',
                '#submit'
            ]

            for selector in confirm_selectors:
                try:
                    btn = self.page.wait_for_selector(selector, state="visible", timeout=5000)
                    btn.click()
                    print("已点击确认按钮")

                    # 等待页面响应，检查结果
                    self.page.wait_for_timeout(2000)

                    # 检查失败提示
                    page_text = self.page.inner_text("body")
                    fail_keywords = ["操作过于频繁", "预约失败", "已预约过", "名额已满",
                                     "不可预约", "已满员", "已达上限"]
                    for kw in fail_keywords:
                        if kw in page_text:
                            print(f"✗ 预约被拒绝: 页面提示「{kw}」")
                            logger.warning("预约被拒绝", extra={"reason": kw})
                            if self._tracker:
                                self._tracker.step_failed(f"预约被拒绝: {kw}")
                            return False

                    # 检查成功提示
                    success_keywords = ["预约成功", "提交成功", "操作成功"]
                    for kw in success_keywords:
                        if kw in page_text:
                            print("✓ 预约成功（页面确认）")
                            logger.info("确认预约成功")
                            if self._tracker:
                                self._tracker.step_success()
                            return True

                    # 无明确提示，保守返回 False
                    print("? 预约状态未知，未检测到成功或失败提示")
                    logger.warning("预约状态未知")
                    return False
                except:
                    continue

            print("未找到确认按钮")
            logger.warning("未找到确认按钮")
            return False

        except Exception as e:
            print(f"确认预约失败: {e}")
            logger.error("确认预约失败", extra={"error": str(e)})
            return False

    # ===== 快捷方法 =====

    def config(self, **kwargs) -> "BookingClient":
        """批量配置"""
        self._config.update(kwargs)
        return self

    def wait(self, seconds: float) -> "BookingClient":
        """等待"""
        self.page.wait_for_timeout(int(seconds * 1000))
        return self

    def click(self, target: str, **kwargs) -> "BookingClient":
        """通用点击"""
        self._ensure_browser()
        self.chain.click(target, **kwargs)
        return self.wait(0.5)

    # ===== 步骤执行 =====

    def step(self, description: str) -> StepBuilder:
        """开始一个步骤"""
        self._ensure_browser()
        return self.step_builder.step(description)

    def run_steps(self, steps: list) -> bool:
        """
        运行步骤列表

        参数:
            steps: 步骤配置列表
                [
                    {"action": "click", "target": "粤海校区"},
                    {"action": "click", "target": "网球"},
                    {"action": "select", "target": "19:00-20:00"},
                ]

        返回:
            bool: 是否全部成功
        """
        self._ensure_browser()

        for i, step in enumerate(steps):
            action = step.get("action")
            target = step.get("target")

            print(f"[步骤 {i+1}] {action}: {target}")

            if action == "click":
                self.chain.click(target)
            elif action == "select":
                self.slot_selector.select(target)
            elif action == "wait":
                self.wait(target)

            self.wait(1)

        return True

    # ===== 快捷运行 =====

    def quick_book(
        self,
        campus: str = None,
        sport: str = None,
        date: int = 0,
        time_slot: str = None,
        venue: str = None
    ) -> bool:
        """
        一键预约

        参数:
            campus: 校区，如 "粤海校区"
            sport: 体育项目，如 "网球"
            date: 日期索引，0=今天, 1=明天
            time_slot: 时间段，如 "19:00-20:00"
            venue: 场地（可选）
        """
        print("\n" + "=" * 50)
        print("开始快捷预约")
        print("=" * 50)

        if campus:
            self.select_campus(campus)
        if sport:
            self.select_sport(sport)
        if date is not None:
            self.select_date(date)
        if time_slot:
            self.select_time_slot(time_slot)
        if venue:
            self.select_venue(venue)

        print("\n正在确认预约...")
        result = self.confirm()

        print("=" * 50)
        print(f"预约{'成功' if result else '失败'}")
        print("=" * 50 + "\n")

        return result

    # ===== 上下文管理器 =====

    def __enter__(self):
        self._ensure_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False