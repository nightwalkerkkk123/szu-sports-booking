"""
临时：明确选日期=明天 的预约脚本。
修复点：main.py 解析了 --date 但没传给 select_date()。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta
from booking.client import BookingClient
from booking.browser import CloakBrowserLifecycle
from booking.config import Config
from booking.chain_builder import ClickError
from booking.selectors.slot_selector import SlotUnavailableError

USERNAME = "2023150090"
PASSWORD = "11282577"
CAMPUS = "粤海校区"
SPORT = "一楼重量型健身"
TIME_SLOT = "19:00-20:00"
DATE_INDEX = 1  # 1=明天

# 计算明天的可读日期
tomorrow = (datetime.now() + timedelta(days=DATE_INDEX)).strftime("%Y-%m-%d (%A)")
# 周几转中文
weekdays_zh = {"Monday":"周一","Tuesday":"周二","Wednesday":"周三","Thursday":"周四",
               "Friday":"周五","Saturday":"周六","Sunday":"周日"}
for en, zh in weekdays_zh.items():
    tomorrow = tomorrow.replace(en, zh)

print("=" * 60)
print("BOOK TOMORROW — 明确选日期")
print("=" * 60)
print(f"目标日期: {tomorrow}  (索引 {DATE_INDEX})")
print(f"校区: {CAMPUS} | 项目: {SPORT} | 时段: {TIME_SLOT}")
print("=" * 60)

browser = CloakBrowserLifecycle()
browser.launch(headless=False)
client = BookingClient()
client.set_browser(browser)

config = Config.load("configs/config.yaml")

try:
    client.open(config.venue_url)
    client.login(USERNAME, PASSWORD)
    client.select_campus(CAMPUS)
    client.select_sport(SPORT)

    # ★ 关键：显式选日期
    print(f"\n>>> 显式选择日期索引 {DATE_INDEX}（{tomorrow}）")
    client.select_date(DATE_INDEX)

    # 选时段 —— 通过内部方法拿到选项，确认有 19:00-20:00
    options = client.slot_selector.get_all("div.group-2", check_availability=True)
    target = next((o for o in options if "19:00-20:00" in o["text"]), None)
    if not target:
        print("[X] 没找到 19:00-20:00 这个时段")
        sys.exit(1)
    if not target.get("available", True):
        print(f"[X] 19:00-20:00 不可用：{target.get('text')}")
        sys.exit(1)
    print(f"[OK] 19:00-20:00 在 {tomorrow} 可预约")

    # 选时段
    client.select_time_slot(TIME_SLOT)
    # 选场地
    client.select_venue()
    # 确认
    result = client.confirm()
    print("\n" + "=" * 60)
    print(f"预约{'成功 ✅' if result else '失败 ❌'}")
    print(f"目标: {tomorrow} {TIME_SLOT} {CAMPUS} {SPORT}")
    print("⚠️ 提示：粤海一楼重量型健身，明天 19:00-20:00")
    print("=" * 60)
except (ClickError, SlotUnavailableError) as e:
    print(f"\n[X] 失败: {e}")
    sys.exit(1)
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    browser.close()
