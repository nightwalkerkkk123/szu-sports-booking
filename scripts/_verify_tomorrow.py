"""
临时验证脚本：手动调 BookingClient，明天 14:00-15:00 丽湖网球场
跑这个之前先 dry-run / query-only 验证。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from booking.client import BookingClient
from booking.browser import CloakBrowserLifecycle

USERNAME = "2023150090"
PASSWORD = "11282577"
CAMPUS = "丽湖校区"
SPORT = "网球"
TIME_SLOT = "14:00-15:00"
# 1 = 明天
DATE_INDEX = 1

print("=" * 60)
print("VERIFY-ONLY: 不点确认按钮")
print("=" * 60)
print(f"日期索引: {DATE_INDEX} (0=今天, 1=明天, 2=后天)")
print(f"校区: {CAMPUS} | 项目: {SPORT} | 时段: {TIME_SLOT}")
print("=" * 60)

browser = CloakBrowserLifecycle()
browser.launch(headless=False)
client = BookingClient()
client.set_browser(browser)

# 从 config 拿 URL
from booking.config import Config
config = Config.load("configs/config.yaml")
client.open(config.venue_url)
client.login(USERNAME, PASSWORD)
client.select_campus(CAMPUS)
client.select_sport(SPORT)
# 关键：显式选日期
client.select_date(DATE_INDEX)
client.select_time_slot(TIME_SLOT)
# 到了场地选择这步停下来 —— 不 confirm
print("\n[VERIFY] 停在场地选择，不会 confirm")
print("请在浏览器里核对日期是不是 6/4")
print("3 秒后自动关闭浏览器...")
import time
time.sleep(3)
browser.close()
