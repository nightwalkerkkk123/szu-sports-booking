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


def test_cookie_persistence():
    """Test 1: Cookie persistence - load without browser"""
    print("=" * 50)
    print("TEST 1: Cookie persistence")
    print("=" * 50)

    flow = ApiBookingFlow(username=USERNAME)
    if flow.load_cookies():
        print("✓ Cookies loaded from file (no browser needed)")
        print(f"✓ Authenticated: {flow.is_authenticated}")

        # Verify cookies work by making an API call
        try:
            slots = flow.get_time_slots(date="2026-05-28", sport="网球")
            print(f"✓ API call works with saved cookies ({len(slots)} slots)")
        except Exception as e:
            print(f"✗ Saved cookies don't work: {e}")
    else:
        print("✗ No saved cookies, doing browser login...")
        if flow.login_with_browser(password=PASSWORD, name=NAME):
            print("✓ Browser login + cookie save successful")
        else:
            print("✗ Browser login failed")

    flow.close()


def test_full_flow():
    """Test 2: Complete booking flow"""
    print("\n" + "=" * 50)
    print("TEST 2: Full booking flow")
    print("=" * 50)

    flow = ApiBookingFlow(username=USERNAME)

    # Step 1: Load cookies
    if not flow.load_cookies():
        print("✗ No saved cookies, doing browser login...")
        if not flow.login_with_browser(password=PASSWORD, name=NAME):
            print("✗ Browser login failed")
            flow.close()
            return

    # Step 2: Get time slots
    print("\n--- Time slots ---")
    slots = flow.get_time_slots(date="2026-05-28", sport="网球")
    available_slots = [s for s in slots if s.is_available]
    print(f"Total: {len(slots)}, Available: {len(available_slots)}")
    for s in slots:
        mark = "✓" if s.is_available else "✗"
        print(f"  {mark} {s.code} - {s.text}")

    if not available_slots:
        print("\nNo available slots, trying venues anyway...")

    # Step 3: Get venues for a time slot
    print("\n--- Venues (19:00-20:00) ---")
    try:
        venues = flow.get_venues(
            date="2026-05-28",
            time_slot="19:00-20:00",
            sport="网球",
        )
        available_venues = [v for v in venues if v.is_available]
        print(f"Total: {len(venues)}, Available: {len(available_venues)}")
        for v in venues:
            mark = "✓" if v.is_available else "✗"
            print(f"  {mark} {v.name} ({v.venue_area_name}) - {v.text}")
    except Exception as e:
        print(f"✗ Failed: {e}")

    # Step 4: Try booking if venues available
    if available_venues:
        print("\n--- Booking ---")
        result = flow.book(date="2026-05-28", time_slot="19:00-20:00")
        print(f"Result: {result}")
    else:
        print("\n--- Booking skipped (no available venues) ---")

    flow.close()


def test_cookie_expiry():
    """Test 3: Check cookie expiry info"""
    print("\n" + "=" * 50)
    print("TEST 3: Cookie expiry check")
    print("=" * 50)

    from booking.api import CookieManager
    import json
    from datetime import datetime

    mgr = CookieManager()
    path = mgr._get_cookie_path(USERNAME)

    if not path.exists():
        print("✗ No cookie file")
        return

    with open(path) as f:
        data = json.load(f)

    saved_at = datetime.fromisoformat(data["saved_at"])
    expires_at = datetime.fromisoformat(data["expires_at"])
    now = datetime.now()
    remaining = expires_at - now

    print(f"Saved at:   {saved_at}")
    print(f"Expires at: {expires_at}")
    print(f"Remaining:  {remaining}")
    print(f"Cookie count: {len(data['cookies'])}")
    print(f"Cookie keys: {list(data['cookies'].keys())}")

    # Check required cookies
    missing = [c for c in mgr.REQUIRED_COOKIES if c not in data["cookies"]]
    if missing:
        print(f"✗ Missing required cookies: {missing}")
    else:
        print("✓ All required cookies present")

    # Check validity
    is_valid = mgr.is_valid(USERNAME)
    print(f"✓ Cookie valid: {is_valid}")


if __name__ == "__main__":
    test_cookie_persistence()
    test_cookie_expiry()
    test_full_flow()
    print("\n" + "=" * 50)
    print("All tests done!")