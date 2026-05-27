"""
API Client for direct backend calls.

Example:
    api = ApiClient()
    api.set_cookies_from_browser(browser)

    # Get available dates
    dates = api.get_available_dates()

    # Get available time slots
    slots = api.get_time_slots(campus=1, date="2026-05-25", sport_code="004")

    # Get available venues
    venues = api.get_venues(campus=1, date="2026-05-25", sport_code="004",
                            start_time="12:00", end_time="13:00")

    # Book a venue
    result = api.book(venue_wid="xxx", date="2026-05-25", time_slot="12:00-13:00",
                     username="2023150090", name="王子豪", ...)
"""
import logging
from typing import Optional

import httpx

from .session import SessionManager
from .models import TimeSlot, Venue, BookingResponse, BookingRecord
from .errors import (
    ApiError,
    AuthenticationError,
    NetworkError,
)

logger = logging.getLogger("booking.api")


class ApiClient:
    """
    API client for booking via direct backend calls.

    Uses httpx for HTTP requests with cookie-based authentication.
    """

    BASE_URL = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy"

    def __init__(self, timeout: float = 30.0, proxy: str | None = None):
        self._timeout = timeout
        self._session = SessionManager()
        kwargs = {
            "timeout": timeout,
            "headers": self._session.headers,  # 使用我们的浏览器 headers
        }
        if proxy:
            kwargs["proxy"] = proxy
        self._http = httpx.Client(**kwargs)

    def set_cookies(self, cookies: dict):
        """Set cookies for authentication"""
        self._session.set_cookies(cookies)

    def set_cookies_from_browser(self, browser_context):
        """Extract cookies from browser context"""
        self._session.set_cookies_from_browser(browser_context)

    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid authentication"""
        return self._session.is_authenticated()

    def close(self):
        """Close HTTP client"""
        self._http.close()

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
    ) -> dict:
        """
        Make HTTP request to backend.

        Args:
            method: HTTP method (GET, POST)
            path: API path (e.g. "/sportVenue/getTimeList.do")
            data: Form data

        Returns:
            Response JSON as dict
        """
        url = f"{self.BASE_URL}{path}"
        headers = {"Cookie": self._session.get_cookie_header()}

        try:
            if method.upper() == "POST":
                response = self._http.post(url, data=data, headers=headers)
            else:
                response = self._http.get(url, params=data, headers=headers)

            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError("认证失败，请重新登录")

            if response.status_code == 404:
                raise ApiError(code="NOT_FOUND", message="接口不存在",
                             status_code=404)

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            raise NetworkError("请求超时")
        except httpx.ConnectError:
            raise NetworkError("连接失败，请检查网络")
        except httpx.HTTPStatusError as e:
            raise NetworkError(f"HTTP错误: {e.response.status_code}")
        except AuthenticationError:
            raise
        except ApiError:
            raise
        except Exception as e:
            logger.error(f"请求异常: {e}")
            raise NetworkError(f"请求异常: {str(e)}")

    # ===== Public API Methods =====

    def get_available_dates(self) -> list[str]:
        """
        Get available booking dates.

        Returns:
            List of date strings (e.g. ["2026-05-27", "2026-05-28"])
        """
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        result = self._request("POST", "/sportVenue/getRqList.do")
        if isinstance(result, list):
            return result
        return []

    def get_app_settings(self) -> dict:
        """
        Get app settings (booking start time, cancel rules, etc.).

        Returns:
            Dict with settings like YYKS (booking start time), QXYYTQ (cancel minutes)
        """
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        return self._request("POST", "/sportVenue/getAppSets.do")

    def get_sport_venue_data(self) -> dict:
        """
        Get initial sport venue data (campus list, sport list, venue list).

        Returns:
            Dict with campusList, xmList, packageVenueList
        """
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
        """
        Get available time slots for a sport on a date.

        Args:
            campus: Campus code (1=粤海, 2=丽湖)
            date: Date string (YYYY-MM-DD)
            sport_code: Sport code (004=网球, 001=羽毛球, etc.)
            booking_type: Booking type (1.0=包场, 2.0=散场)

        Returns:
            List of TimeSlot objects
        """
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        data = {
            "XQ": str(campus),
            "YYRQ": date,
            "YYLX": booking_type,
            "XMDM": sport_code,
        }

        logger.info(f"获取时间段: campus={campus}, date={date}, sport={sport_code}, type={booking_type}")

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
            raise NetworkError(f"获取时间段失败: {str(e)}")

    def get_venues(
        self,
        campus: int,
        date: str,
        sport_code: str,
        start_time: str,
        end_time: str,
        booking_type: str = "1.0",
    ) -> list[Venue]:
        """
        Get available venues for a time slot.

        Args:
            campus: Campus code (1=粤海, 2=丽湖)
            date: Date string (YYYY-MM-DD)
            sport_code: Sport code (004=网球, etc.)
            start_time: Start time (e.g. "12:00")
            end_time: End time (e.g. "13:00")
            booking_type: Booking type (1.0=包场, 2.0=散场)

        Returns:
            List of Venue objects
        """
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

        logger.info(f"获取场地: campus={campus}, date={date}, sport={sport_code}, "
                   f"time={start_time}-{end_time}")

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
            raise NetworkError(f"获取场地失败: {str(e)}")

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
        """
        Submit a booking request.

        Args:
            venue_wid: Venue WID from get_venues()
            date: Date string (YYYY-MM-DD)
            time_slot: Time slot (e.g. "12:00-13:00")
            username: Student ID
            name: Student name
            sport_code: Sport code (default: "004" for tennis)
            campus: Campus code (default: 1 for 粤海)
            venue_area_code: Venue area code (default: "015")
            booking_type: Booking type (1.0=包场, 2.0=散场)

        Returns:
            BookingResponse with success/failure info
        """
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

        logger.info(f"提交预约: venue_wid={venue_wid}, date={date}, "
                   f"time={time_slot}, user={username}")

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
            raise NetworkError(f"预约失败: {str(e)}")

    def get_my_bookings(
        self,
        page_size: int = 10,
        page_number: int = 1,
    ) -> list[BookingRecord]:
        """
        Get booking history for current user.

        Args:
            page_size: Number of records per page
            page_number: Page number (1-based)

        Returns:
            List of BookingRecord objects
        """
        if not self.is_authenticated:
            raise AuthenticationError("请先登录")

        try:
            # First call to get searchMeta
            self._request("POST", "/modules/myBooking.do", data={"*json": "1"})
            self._request("POST", "/modules/myBooking/myBookingInfo.do",
                         data={"*searchMeta": "1"})

            # Then get actual data
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
            raise NetworkError(f"获取预约记录失败: {str(e)}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False