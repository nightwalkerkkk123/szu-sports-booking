"""
预约客户端 - 统一的链式调用接口
整合浏览器管理、登录、选择器等功能
"""

import logging
from pathlib import Path

from .chain_builder import Chain
from .selectors.campus_page import CampusPage
from .selectors.confirm_page import ConfirmPage
from .selectors.login_page import LoginPage
from .selectors.slot_selector import FlexibleSlotSelector, SlotUnavailableError
from .selectors.sport_page import SportPage
from .selectors.venue_selector import FlexibleVenueSelector
from .step_builder import StepBuilder

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

    def __init__(
        self,
        headless: bool = False,
        use_fake_browser: bool = False,
        trace_id: str = None,
        plan=None,
    ):
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
        self.login_page = None
        self.confirm_page = None
        self.campus_page = None
        self.sport_page = None

        # 如果提供了 trace_id，初始化步骤追踪
        if trace_id:
            from booking.observability.step_tracker import StepTracker

            self._tracker = StepTracker(trace_id)

        # Plan / critical points (optional). When set, callers can use
        # verify_point / verify_all / save_screenshot to record evidence.
        # Setting a plan does *not* modify any of the existing booking
        # methods, so existing tests and call sites are unaffected.
        self._plan = plan
        self._screenshots_dir = None

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
        self.login_page = LoginPage(self.page, chain=self.chain)
        self.confirm_page = ConfirmPage(self.page, chain=self.chain)
        self.campus_page = CampusPage(self.page, chain=self.chain)
        self.sport_page = SportPage(self.page, chain=self.chain)

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
        self.page = browser.page if hasattr(browser, "page") else browser
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

        self.login_page.login(username, password)

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
            print("登出中...")
            self.page.goto(logout_url)
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass  # 登出失败，继续尝试登录

        # 2. 清除 cookies
        self.chain.clear_cookies()

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
            logger.info("选择校区", extra={"campus": name})
            self.campus_page.select(name)
        else:
            self.chain.click_first()

        return self.wait(1)

    def select_sport(self, name: str = None, index: int = None) -> "BookingClient":
        """选择体育项目"""
        self._ensure_browser()

        if index is not None:
            self.chain.click(index=index)
        elif name:
            logger.info("选择项目", extra={"sport": name})
            self.sport_page.select(name)
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
                target=name, container_selector="div.group-2", check_availability=True
            )
        elif index is not None:
            # 按索引选择
            self.slot_selector.select(
                index=index, container_selector="div.group-2", check_availability=True
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
                o for o in available_options if not time_pattern.search(o.get("text", ""))
            ]

            if not venue_options:
                raise SlotUnavailableError("没有可用的场地")

            first_available = venue_options[0]
            print(f"选择可用场地: {first_available['text']}")
            first_available["element"].click()

        return self.wait(1)

    def select_date(self, selector: int | str = 0) -> "BookingClient":
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
        target: str | int = None,
        *,
        index: int = None,
        contains: str = None,
        regex: str = None,
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
            container_selector="div.group-2",
        )
        return self.wait(1)

    def confirm(self) -> bool:
        """确认预约"""
        self._ensure_browser()

        print("\n正在确认预约...")

        if self._tracker:
            self._tracker.start_step("确认预约")

        confirmed = self.confirm_page.confirm()

        if confirmed:
            print("[OK] 预约成功（页面确认）")
            logger.info("确认预约成功")
            if self._tracker:
                self._tracker.step_success()
        else:
            print("[X] 预约未成功")
            logger.warning("预约未成功")
            if self._tracker:
                self._tracker.step_failed("确认未通过")

        return confirmed

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

            print(f"[步骤 {i + 1}] {action}: {target}")

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
        venue: str = None,
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

    # ===== Plan / critical points (Webwright-style verification) =====

    def set_plan(self, plan) -> "BookingClient":
        """Attach a :class:Plan and return `self` for chaining.

        When a plan is attached, callers may use :meth:erify_point,
        :meth:erify_all, and :meth:save_screenshot to record evidence.
        Setting a plan does *not* modify any of the existing booking methods.
        """
        self._plan = plan
        return self

    def get_plan(self):
        """Return the current :class:Plan or `None`."""
        return self._plan

    def set_screenshots_dir(self, path) -> None:
        """Set the directory where :meth:save_screenshot writes PNGs.

        Usually called by the CLI when a :class:RunManager is active; the
        default of `None` means screenshots are kept in memory only.
        """
        self._screenshots_dir = Path(path) if path else None

    def save_screenshot(self, name: str, png_bytes: bytes | None = None) -> str | None:
        """Persist a screenshot and return its path.

        Args:
            name: Filename suffix (e.g. `"after_login"`).
            png_bytes: PNG bytes. If `None`, captures the current page.

        Returns:
            Absolute path string on success, `None` if no screenshots dir
            is configured or capture failed.
        """
        if self._screenshots_dir is None:
            return None
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        out = self._screenshots_dir / f"{name}.png"
        try:
            if png_bytes is None:
                if self.page is None:
                    return None
                png_bytes = self.page.screenshot()
            out.write_bytes(png_bytes)
            return str(out)
        except Exception as exc:  # noqa: BLE001
            logger.warning("save_screenshot failed: %s", exc)
            return None

    def verify_point(self, name: str, status=None, note: str | None = None) -> bool:
        """Manually mark a critical point.

        Args:
            name: Critical point name.
            status: `PointStatus.PASSED` / `PointStatus.FAILED` /
                `PointStatus.SKIPPED`. If `None`, the point's status is
                left unchanged and only `note` is attached.
            note: Free-form note (e.g. failure reason).

        Returns:
            `True` if a point with that name exists.
        """
        if self._plan is None:
            return False
        point = self._plan.get(name)
        if point is None:
            return False
        if status is not None:
            point.mark(status, note)
        elif note is not None:
            point.note = note
        return True

    def verify_all(self) -> dict:
        """Run evidence-based checks for every PENDING point.

        For each point whose `evidence_type` is `SCREENSHOT` /
        `SELECTOR` / `TEXT_PRESENT`, this method inspects the current
        page (or, for `SCREENSHOT`, the screenshots directory) and
        updates the point's status. `CUSTOM` points are left untouched.

        Returns:
            Summary dict `{passed, failed, skipped, pending}` keyed by
            status name. Safe to call when no plan is attached (returns
            an empty summary).
        """
        from booking.observability.plan import (
            EvidenceType,
            PointStatus,
        )

        if self._plan is None:
            return {"passed": 0, "failed": 0, "skipped": 0, "pending": 0}

        for point in self._plan.points:
            if point.status is not PointStatus.PENDING:
                continue
            if point.evidence_type is EvidenceType.CUSTOM:
                continue
            ok, reason = self._check_evidence(point)
            point.mark(
                PointStatus.PASSED if ok else PointStatus.FAILED,
                None if ok else reason,
            )
            if (
                point.evidence_type is EvidenceType.SCREENSHOT
                and ok
                and self._screenshots_dir is not None
            ):
                rel = Path(self._screenshots_dir).name
                point.evidence_path = f"{rel}/{point.evidence_value}"

        return {
            "passed": self._plan.passed,
            "failed": self._plan.failed,
            "skipped": sum(1 for p in self._plan.points if p.status is PointStatus.SKIPPED),
            "pending": self._plan.pending,
        }

    def _check_evidence(self, point) -> tuple[bool, str | None]:
        """Check a single point's evidence against the current page.

        Returns:
            `(ok, reason)`. `ok` is True when evidence is satisfied;
            `reason` carries a short message on failure.
        """
        from booking.observability.plan import EvidenceType

        if point.evidence_type is EvidenceType.SCREENSHOT:
            if self._screenshots_dir is None:
                return False, "no screenshots dir configured"
            target = Path(self._screenshots_dir) / point.evidence_value
            return (target.exists(), f"missing screenshot: {target.name}")
        if self.page is None:
            return False, "page not initialised"
        if point.evidence_type is EvidenceType.SELECTOR:
            for sel in (point.evidence_value or "").split(","):
                sel = sel.strip()
                if not sel:
                    continue
                try:
                    if self.page.query_selector(sel):
                        return True, None
                except Exception:  # noqa: BLE001, S110
                    pass
            return False, f"selector not found: {point.evidence_value}"
        if point.evidence_type is EvidenceType.TEXT_PRESENT:
            try:
                body = self.page.inner_text("body")
            except Exception as exc:  # noqa: BLE001
                return False, f"page unreachable: {exc}"
            if (point.evidence_value or "") in body:
                return True, None
            return False, f"text not in body: {point.evidence_value!r}"
        return False, f"unsupported evidence_type: {point.evidence_type}"

    # ===== 上下文管理器 =====

    def __enter__(self):
        self._ensure_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
