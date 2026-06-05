"""
High-level API booking flow.

Coordinates:
1. Browser login (if needed)
2. Cookie persistence
3. API booking

Example:
    flow = ApiBookingFlow(username="2023150090")
    flow.login_with_browser(password="xxx")

    # Or use saved cookies
    flow.load_cookies()

    # Book via API
    result = flow.book(
        sport="网球",
        date="2026-05-25",
        time_slot="19:00-20:00",
    )
"""
import logging
from pathlib import Path

from .client import ApiClient
from .cookie_extractor import extract_cookies_from_browser
from .cookie_manager import CookieManager
from .errors import AuthenticationError, ValidationError

logger = logging.getLogger("booking.api")


class ApiBookingFlow:
    """
    High-level API booking flow.

    Handles login via browser -> cookie persistence -> API booking.
    """

    # Sport code mapping (from HAR data)
    SPORT_CODES = {
        "羽毛球": "001",
        "足球": "002",
        "排球": "003",
        "网球": "004",
        "篮球": "005",
        "壁球": "006",
        "一楼重量型健身": "007",
        "二楼有氧健身": "008",
        "游泳": "009",
        "乒乓球": "013",
        "舞蹈": "015",
        "桌球": "016",
        "骑行": "017",
        "魔镜": "018",
        "桌游": "019",
        "健身房": "020",
        "瑜伽": "021",
        "智能健身房": "024",
        "匹克球": "030",
        "毽球": "034",
    }

    # Campus code mapping
    CAMPUS_CODES = {
        "粤海校区": 1,
        "丽湖校区": 2,
        "粤海": 1,
        "丽湖": 2,
    }

    # Default booking type per sport (1.0=包场, 2.0=散场)
    BOOKING_TYPES = {
        "羽毛球": "1.0",
        "足球": "2.0",
        "排球": "1.0",
        "网球": "1.0",
        "篮球": "2.0",
        "壁球": "1.0",
        "一楼重量型健身": "2.0",
        "二楼有氧健身": "2.0",
        "游泳": "2.0",
        "乒乓球": "1.0",
        "舞蹈": "1.0",
        "桌球": "1.0",
        "骑行": "1.0",
        "魔镜": "1.0",
        "桌游": "1.0",
        "健身房": "2.0",
        "瑜伽": "2.0",
        "智能健身房": "1.0",
        "匹克球": "1.0",
        "毽球": "1.0",
    }

    def __init__(
        self,
        username: str,
        cookie_dir: Path | None = None,
        browser_headless: bool = False,
        proxy: str | None = None,
    ):
        """
        Initialize API booking flow.

        Args:
            username: Student ID
            cookie_dir: Directory for cookie storage
            browser_headless: Run browser in headless mode
            proxy: HTTP proxy URL (e.g. "http://127.0.0.1:7897")
        """
        self._username = username
        self._password: str | None = None
        self._browser_headless = browser_headless
        self._proxy = proxy
        self._api_client = ApiClient(proxy=proxy)
        self._cookie_manager = CookieManager(cookie_dir)
        self._browser = None
        self._name: str | None = None  # Student name for booking

    @property
    def is_authenticated(self) -> bool:
        """Check if API client has valid cookies"""
        return self._api_client.is_authenticated

    # ===== Cookie Management =====

    def load_cookies(self) -> bool:
        """
        Load cookies from file.

        Returns:
            True if cookies loaded and are valid
        """
        cookies = self._cookie_manager.load(self._username)
        if cookies:
            self._api_client.set_cookies(cookies)
            logger.info(f"Loaded cookies for {self._username}")
            return True
        return False

    def save_cookies(self) -> bool:
        """Save cookies from browser to file and set on API client"""
        if self._browser is None:
            logger.warning("No browser to extract cookies from")
            return False

        cookies = extract_cookies_from_browser(self._browser)
        if not cookies:
            logger.warning("No cookies extracted from browser")
            return False

        # Set cookies on API client in memory
        self._api_client.set_cookies(cookies)

        # Persist to file
        return self._cookie_manager.save(self._username, cookies)

    def clear_cookies(self):
        """Clear saved cookies for this user"""
        self._cookie_manager.delete(self._username)

    # ===== Browser Login =====

    def login_with_browser(
        self,
        password: str,
        name: str | None = None,
        campus: str = "粤海校区",
        sport: str = "网球",
    ) -> bool:
        """
        Login via browser UI and extract cookies.

        Args:
            password: Account password
            name: Student name (for booking, optional)
            campus: Default campus (default: 粤海校区)
            sport: Default sport (default: 网球)

        Returns:
            True if login successful and cookies saved
        """
        from booking.browser.cloak_adapter import CloakBrowserLifecycle

        logger.info(f"Starting browser login for {self._username}")

        try:
            # Launch browser
            self._browser = CloakBrowserLifecycle()
            self._browser.launch(headless=self._browser_headless)
            page = self._browser.page

            # Navigate to login page
            login_url = "https://authserver.szu.edu.cn/authserver/login"
            page.goto(login_url)
            page.wait_for_load_state("domcontentloaded")

            # Fill login form
            page.fill("#username", self._username)
            page.wait_for_selector("#password", state="visible", timeout=10000)
            page.evaluate("""
                el = document.querySelector('#password');
                if (el) {
                    el.removeAttribute('readonly');
                    el.classList.remove('no-auto-input');
                }
            """)
            page.fill("#password", password)
            page.click("#login_submit")

            # Wait for redirect to booking page
            page.wait_for_load_state("domcontentloaded", timeout=30000)

            # Navigate to sport venue booking page
            venue_url = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do#/sportVenue"
            page.goto(venue_url)
            page.wait_for_load_state("domcontentloaded", timeout=15000)

            # Wait for page to stabilize
            page.wait_for_timeout(2000)

            logger.info("Browser login successful")

            # Store name for booking
            self._name = name

            # Extract and save cookies
            return self.save_cookies()

        except Exception as e:
            logger.error(f"Browser login failed: {e}")
            return False

    # ===== Booking API =====

    def _ensure_authenticated(self):
        """Ensure API client is authenticated, raise if not"""
        if not self.is_authenticated:
            raise AuthenticationError(
                "Not authenticated. Call load_cookies() or login_with_browser() first."
            )

    def get_available_dates(self) -> list[str]:
        """Get available booking dates"""
        self._ensure_authenticated()
        return self._api_client.get_available_dates()

    def get_time_slots(
        self,
        date: str,
        sport: str = "网球",
        campus: str = "粤海校区",
    ) -> list:
        """Get available time slots"""
        self._ensure_authenticated()

        sport_code = self.SPORT_CODES.get(sport, sport)
        campus_code = self.CAMPUS_CODES.get(campus, campus)
        booking_type = self.BOOKING_TYPES.get(sport, "1.0")

        return self._api_client.get_time_slots(
            campus=campus_code,
            date=date,
            sport_code=sport_code,
            booking_type=booking_type,
        )

    def get_venues(
        self,
        date: str,
        time_slot: str,
        sport: str = "网球",
        campus: str = "粤海校区",
    ) -> list:
        """Get available venues for a time slot"""
        self._ensure_authenticated()

        sport_code = self.SPORT_CODES.get(sport, sport)
        campus_code = self.CAMPUS_CODES.get(campus, campus)
        booking_type = self.BOOKING_TYPES.get(sport, "1.0")

        start_time, end_time = time_slot.split("-")

        return self._api_client.get_venues(
            campus=campus_code,
            date=date,
            sport_code=sport_code,
            start_time=start_time.strip(),
            end_time=end_time.strip(),
            booking_type=booking_type,
        )

    def book(
        self,
        date: str,
        time_slot: str,
        sport: str = "网球",
        campus: str = "粤海校区",
        name: str | None = None,
    ) -> dict:
        """
        Book a venue via API.

        Args:
            date: Date (YYYY-MM-DD)
            time_slot: Time slot (e.g. "19:00-20:00")
            sport: Sport type (default: 网球)
            campus: Campus (default: 粤海校区)
            name: Student name (uses stored name if not provided)

        Returns:
            dict with success status and details
        """
        self._ensure_authenticated()

        sport_code = self.SPORT_CODES.get(sport, sport)
        campus_code = self.CAMPUS_CODES.get(campus, campus)
        booking_type = self.BOOKING_TYPES.get(sport, "1.0")
        student_name = name or self._name

        if not student_name:
            raise ValidationError("Student name required for booking")

        # First get available venues
        venues = self.get_venues(date, time_slot, sport, campus)
        available_venues = [v for v in venues if v.is_available]

        if not available_venues:
            return {
                "success": False,
                "message": "No available venues",
                "venues": venues,
            }

        # Try to book the first available venue
        venue = available_venues[0]

        logger.info(
            f"Booking: venue={venue.name}, date={date}, "
            f"time={time_slot}, user={self._username}"
        )

        result = self._api_client.book(
            venue_wid=venue.wid,
            date=date,
            time_slot=time_slot,
            username=self._username,
            name=student_name,
            sport_code=sport_code,
            campus=campus_code,
            venue_area_code=venue.venue_area_code,
            booking_type=booking_type,
        )

        # 预约提交后查询记录验证闭环
        verified = False
        if result.is_success:
            verified = self._verify_booking(date, sport, time_slot)

        return {
            "success": result.is_success,
            "code": result.code,
            "message": result.message,
            "venue": venue.name,
            "verified": verified,
            "datas": result.datas,
        }

    def get_my_bookings(self, page_size: int = 10) -> list:
        """查询我的预约记录"""
        self._ensure_authenticated()
        return self._api_client.get_my_bookings(page_size=page_size)

    def _verify_booking(self, date: str, sport: str, time_slot: str) -> bool:
        """
        预约后查询记录验证是否成功创建。

        Args:
            date: 预约日期
            sport: 运动名称
            time_slot: 时间段

        Returns:
            True 如果在预约记录中找到了对应条目
        """
        import time as _time
        _time.sleep(1)  # 等待服务器处理

        try:
            records = self._api_client.get_my_bookings(page_size=5)
            sport_code = self.SPORT_CODES.get(sport, sport)
            # 匹配日期+项目+时间
            for r in records:
                if (date in r.time_slot
                    and r.sport_code == sport_code
                    and r.is_active):
                    logger.info(f"预约验证通过: {r.sport_name} {r.time_slot} 状态={r.status_display}")
                    return True
            logger.warning("预约验证未找到匹配记录")
            return False
        except Exception as e:
            logger.warning(f"预约验证失败: {e}")
            return False

    # ===== Context Manager =====

    def close(self):
        """Close resources (browser, HTTP client)"""
        if self._browser:
            self._browser.close()
            self._browser = None
        self._api_client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
