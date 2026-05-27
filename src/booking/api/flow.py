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
from typing import Optional
from pathlib import Path

from .client import ApiClient
from .cookie_manager import CookieManager
from .cookie_extractor import extract_cookies_from_browser
from .errors import AuthenticationError, NetworkError, BookingError

logger = logging.getLogger("booking.api")


class ApiBookingFlow:
    """
    High-level API booking flow.

    Handles login via browser -> cookie persistence -> API booking.
    """

    # Sport code mapping
    SPORT_CODES = {
        "网球": "004",
        "羽毛球": "001",
        "乒乓球": "002",
        "篮球": "003",
        "健身": "005",
        "游泳": "006",
    }

    # Campus code mapping
    CAMPUS_CODES = {
        "粤海校区": 1,
        "丽湖校区": 2,
        "粤海": 1,
        "丽湖": 2,
    }

    # Venue area codes by sport
    VENUE_AREA_CODES = {
        "网球": "015",
        "羽毛球": "016",
        "乒乓球": "017",
        "篮球": "018",
        "健身": "019",
        "游泳": "020",
    }

    def __init__(
        self,
        username: str,
        cookie_dir: Optional[Path] = None,
        browser_headless: bool = False,
    ):
        """
        Initialize API booking flow.

        Args:
            username: Student ID
            cookie_dir: Directory for cookie storage
            browser_headless: Run browser in headless mode
        """
        self._username = username
        self._password: Optional[str] = None
        self._browser_headless = browser_headless
        self._api_client = ApiClient()
        self._cookie_manager = CookieManager(cookie_dir)
        self._browser = None
        self._name: Optional[str] = None  # Student name for booking

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
        """Save cookies from browser to file"""
        if self._browser is None:
            logger.warning("No browser to extract cookies from")
            return False

        cookies = extract_cookies_from_browser(self._browser)
        if not cookies:
            logger.warning("No cookies extracted from browser")
            return False

        return self._cookie_manager.save(self._username, cookies)

    def clear_cookies(self):
        """Clear saved cookies for this user"""
        self._cookie_manager.delete(self._username)

    # ===== Browser Login =====

    def login_with_browser(
        self,
        password: str,
        name: Optional[str] = None,
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

        return self._api_client.get_time_slots(
            campus=campus_code,
            date=date,
            sport_code=sport_code,
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

        # Parse time slot
        start_time, end_time = time_slot.split("-")

        return self._api_client.get_venues(
            campus=campus_code,
            date=date,
            sport_code=sport_code,
            start_time=start_time.strip(),
            end_time=end_time.strip(),
        )

    def book(
        self,
        date: str,
        time_slot: str,
        sport: str = "网球",
        campus: str = "粤海校区",
        name: Optional[str] = None,
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
        venue_area_code = self.VENUE_AREA_CODES.get(sport, "015")
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
            venue_area_code=venue_area_code,
        )

        return {
            "success": result.is_success,
            "code": result.code,
            "message": result.message,
            "venue": venue.name,
            "datas": result.datas,
        }

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