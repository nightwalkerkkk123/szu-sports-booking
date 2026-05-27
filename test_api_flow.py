#!/usr/bin/env python3
"""End-to-end test for API booking flow."""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()

from booking.api import ApiBookingFlow

USERNAME = "2023150090"
PASSWORD = os.getenv("SZU_PASSWORD_0090", "")
NAME = "王子豪"
PROXY = None  # 直连可用，代理已关闭


def test_flow():
    """Test the complete API booking flow."""
    flow = ApiBookingFlow(username=USERNAME, proxy=PROXY)

    # Step 1: Try to load saved cookies first
    print("=" * 50)
    print("Step 1: Loading saved cookies...")
    if flow.load_cookies():
        print("✓ Loaded cookies from file")
    else:
        print("✗ No saved cookies, need browser login")

        # Step 2: Browser login
        print("\n" + "=" * 50)
        print("Step 2: Browser login...")
        if flow.login_with_browser(password=PASSWORD, name=NAME):
            print("✓ Browser login successful, cookies saved")
        else:
            print("✗ Browser login failed")
            return

    # Step 3: Get time slots
    print("\n" + "=" * 50)
    print("Step 3: Getting time slots...")
    try:
        slots = flow.get_time_slots(date="2026-05-28", sport="网球")
        print(f"✓ Found {len(slots)} time slots")
        for slot in slots:
            status = "可预约" if slot.is_available else "已满"
            print(f"  {slot.code} - {status}")
    except Exception as e:
        print(f"✗ Failed: {e}")

    # Step 4: Get venues for a time slot
    print("\n" + "=" * 50)
    print("Step 4: Getting venues...")
    try:
        venues = flow.get_venues(
            date="2026-05-28",
            time_slot="19:00-20:00",
            sport="网球",
        )
        print(f"✓ Found {len(venues)} venues")
        for v in venues:
            status = "可预约" if v.is_available else "不可用"
            print(f"  {v.name} - {status} ({v.text})")
    except Exception as e:
        print(f"✗ Failed: {e}")

    # Step 5: Book (commented out for safety)
    # print("\n" + "=" * 50)
    # print("Step 5: Booking...")
    # result = flow.book(date="2026-05-28", time_slot="19:00-20:00")
    # print(f"Result: {result}")

    # Cleanup
    flow.close()
    print("\n" + "=" * 50)
    print("Done!")


if __name__ == "__main__":
    test_flow()