"""
API Client for direct backend calls with anti-detection.

Uses curl_cffi to impersonate Chrome TLS fingerprint.
Simulates real browser request sequence to avoid bot detection.

Example:
    api = ApiClient()
    api.set_cookies_from_browser(browser)

    # Get available time slots
    slots = api.get_time_slots(campus=1, date="2026-05-25", sport_code="004")

    # Book a venue
    result = api.book(venue_wid="xxx", date="2026-05-25", time_slot="12:00-13:00",
                     username="2023150090", name="王子豪", ...)
"""

import logging
import random
import time

from curl_cffi import requests as cffi_requests

from .errors import (
    ApiError,
    AuthenticationError,
    NetworkError,
)
from .models import BookingRecord, BookingResponse, TimeSlot, Venue
from .session import SessionManager

logger = logging.getLogger("booking.api")


class ApiClient:
    """
    API client with anti-detection for booking via direct backend calls.

    Uses curl_cffi to impersonate Chrome's TLS fingerprint.
    Simulates real browser request patterns to avoid bot detection.
    """

    BASE_URL = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy"

    def __init__(self, timeout: float = 30.0, proxy: str | None = None):
        self._timeout = timeout
        self._session = SessionManager()
        self._session_obj = cffi_requests.Session(impersonate="chrome")
        self._proxy = proxy
        self._page_visited = False  # 是否已模拟页面访问

    def set_cookies(self, cookies: dict):
        """Set cookies for authentication"""
        self._session.set_cookies(cookies)
        # 同步到 curl_cffi session
        for name, value in cookies.items():
            self._session_obj.cookies.set(name, value, domain="ehall.szu.edu.cn")

    def set_cookies_from_browser(self, browser_context):
        """Extract cookies from browser context"""
        self._session.set_cookies_from_browser(browser_context)

    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid authentication"""
        return self._session.is_authenticated()

    def close(self):
        """Close HTTP client"""
        self._session_obj.close()

    def _random_delay(self, min_s: float = 0.3, max_s: float = 1.0):
        """模拟人类操作的随机延迟"""
        time.sleep(random.uniform(min_s, max_s))

    def _simulate_page_visit(self):
        """
        模拟真实用户访问页面的请求序列。
        先加载主页面和静态资源，再调用 API。
        """
        if self._page_visited:
            return

        try:
            # 1. 访问主页面
            self._session_obj.get(
                f"{self.BASE_URL}/index.do",
                proxy=self._proxy,
                timeout=self._timeout,
            )
            self._random_delay(0.5, 1.5)

            # 2. 加载初始数据
            self._session_obj.get(
                f"{self.BASE_URL}/sportVenue/getSportVenueData.do",
                proxy=self._proxy,
                timeout=self._timeout,
            )
            self._random_delay(0.3, 0.8)

            self._page_visited = True
            logger.info("页面访问模拟完成")
        except Exception as e:
            logger.warning(f"页面访问模拟失败: {e}")

    def _request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
    ) -> dict:
        """
        Make HTTP request with Chrome TLS fingerprint.

        Args:
            method: HTTP method (GET, POST)
            path: API path
            data: Form data

        Returns:
            Response JSON as dict
        """
        url = f"{self.BASE_URL}{path}"
        headers = self._session.headers.copy()
        headers["Cookie"] = self._session.get_cookie_header()

        try:
            if method.upper() == "POST":
                response = self._session_obj.post(
                    url,
                    data=data,
                    headers=headers,
                    proxy=self._proxy,
                    timeout=self._timeout,
                )
            else:
                response = self._session_obj.get(
                    url,
                    params=data,
                    headers=headers,
                    proxy=self._proxy,
                    timeout=self._timeout,
                )

            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError("认证失败，请重新登录")

            if response.status_code == 404:
                raise ApiError(code="NOT_FOUND", message="接口不存在", status_code=404)

            response.raise_for_status()
            return response.json()

        except AuthenticationError:
            raise
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"请求异常: {e}")
            raise NetworkError(f"请求异常: {str(e)}") from e

    # ===== Public API Methods =====

    def get_available_dates(self) -> list[str]:
        """Get available booking dates."""
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        self._simulate_page_visit()
        result = self._request("POST", "/sportVenue/getRqList.do")
        if isinstance(result, list):
            return result
        return []

    def get_app_settings(self) -> dict:
        """Get app settings."""
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        return self._request("POST", "/sportVenue/getAppSets.do")

    def get_sport_venue_data(self) -> dict:
        """Get initial sport venue data."""
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        result = self._request("GET", "/sportVenue/getSportVenueData.do")
        return result

    def get_time_slots(
        self,
        campus: int,
        date: str,
        sport_code: str,
        booking_type: str = "1.0",
    ) -> list[TimeSlot]:
        """Get available time slots for a sport on a date."""
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        self._simulate_page_visit()

        data = {
            "XQ": str(campus),
            "YYRQ": date,
            "YYLX": booking_type,
            "XMDM": sport_code,
        }

        logger.info(
            f"获取时间段: campus={campus}, date={date}, sport={sport_code}, type={booking_type}"
        )

        self._random_delay(0.2, 0.6)

        try:
            result = self._request("POST", "/sportVenue/getTimeList.do", data)

            if isinstance(result, list):
                slots = [TimeSlot(**item) for item in result]
            elif isinstance(result, dict) and "datas" in result:
                rows = result.get("datas", {}).get("getTimeList", {}).get("rows", [])
                slots = [TimeSlot(**item) for item in rows]
            else:
                slots = []

            logger.info(f"获取到 {len(slots)} 个时间段")
            return slots

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"获取时间段失败: {e}")
            raise NetworkError(f"获取时间段失败: {str(e)}") from e

    def get_venues(
        self,
        campus: int,
        date: str,
        sport_code: str,
        start_time: str,
        end_time: str,
        booking_type: str = "1.0",
    ) -> list[Venue]:
        """Get available venues for a time slot."""
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        data = {
            "XMDM": sport_code,
            "YYRQ": date,
            "YYLX": booking_type,
            "KSSJ": start_time,
            "JSSJ": end_time,
            "XQDM": str(campus),
        }

        logger.info(
            f"获取场地: campus={campus}, date={date}, sport={sport_code}, "
            f"time={start_time}-{end_time}"
        )

        self._random_delay(0.3, 0.8)

        try:
            result = self._request("POST", "/modules/sportVenue/getOpeningRoom.do", data)

            if isinstance(result, dict) and "datas" in result:
                rows = result.get("datas", {}).get("getOpeningRoom", {}).get("rows", [])
                venues = [Venue(**item) for item in rows]
            else:
                venues = []

            logger.info(f"获取到 {len(venues)} 个场地")
            return venues

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"获取场地失败: {e}")
            raise NetworkError(f"获取场地失败: {str(e)}") from e

    def book(
        self,
        venue_wid: str,
        date: str,
        time_slot: str,
        username: str,
        name: str,
        sport_code: str = "004",
        campus: int = 1,
        venue_area_code: str = "015",
        booking_type: str = "1.0",
    ) -> BookingResponse:
        """Submit a booking request."""
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        start_time, end_time = time_slot.split("-")

        booking_data = {
            "DHID": "",
            "YYRGH": username,
            "CYRS": "1",
            "YYRXM": name,
            "CGDM": venue_area_code,
            "CDWID": venue_wid,
            "XMDM": sport_code,
            "XQWID": str(campus),
            "KYYSJD": time_slot,
            "YYRQ": date,
            "YYLX": booking_type,
            "YYKS": f"{date} {start_time.strip()}",
            "YYJS": f"{date} {end_time.strip()}",
            "PC_OR_PHONE": "pc",
        }

        logger.info(
            f"提交预约: venue_wid={venue_wid}, date={date}, time={time_slot}, user={username}"
        )

        # 预约前模拟人类停顿
        self._random_delay(1.0, 2.5)

        try:
            result = self._request(
                "POST",
                "/sportVenue/insertVenueBookingInfo.do",
                booking_data,
            )

            if isinstance(result, dict):
                response = BookingResponse(
                    code=result.get("code", "0"),
                    message=result.get("msg") or result.get("message"),
                    datas=result.get("datas"),
                )
            else:
                response = BookingResponse(code="0")

            if response.is_success:
                logger.info("预约成功")
            else:
                logger.warning(f"预约失败: code={response.code}, message={response.message}")

            return response

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"预约失败: {e}")
            raise NetworkError(f"预约失败: {str(e)}") from e

    def get_my_bookings(
        self,
        page_size: int = 10,
        page_number: int = 1,
    ) -> list[BookingRecord]:
        """Get booking history for current user."""
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        try:
            self._request("POST", "/modules/myBooking.do", data={"*json": "1"})
            self._request("POST", "/modules/myBooking/myBookingInfo.do", data={"*searchMeta": "1"})

            result = self._request("POST", "/modules/myBooking.do", data={"*json": "1"})
            result = self._request(
                "POST",
                "/modules/myBooking/myBookingInfo.do",
                data={"pageSize": str(page_size), "pageNumber": str(page_number)},
            )

            if isinstance(result, dict):
                rows = result.get("datas", {}).get("myBookingInfo", {}).get("rows", [])
                records = [BookingRecord(**item) for item in rows]
                logger.info(f"获取到 {len(records)} 条预约记录")
                return records
            return []

        except Exception as e:
            logger.error(f"获取预约记录失败: {e}")
            raise NetworkError(f"获取预约记录失败: {str(e)}") from e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
