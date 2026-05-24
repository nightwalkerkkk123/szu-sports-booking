"""
主程序入口 - 深圳大学体育馆预约

使用方法:
    export SZU_USERNAME=your_username
    export SZU_PASSWORD=your_password
    python main.py

    python main.py --username USERNAME --password PASSWORD
    python main.py --dry-run     # 干跑模式
"""
import argparse
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from booking.client import BookingClient
from booking.config import Config
from booking.chain_builder import ClickError
from booking.selectors.slot_selector import SlotUnavailableError
from booking.browser import FakeBrowserLifecycle, CloakBrowserLifecycle
from booking.observability.run_manager import RunManager
from booking.observability.report_generator import generate_and_open_report


def main():
    parser = argparse.ArgumentParser(description="深圳大学体育馆预约工具")
    parser.add_argument("--username", "-u", help="学号")
    parser.add_argument("--password", "-p", help="密码")
    parser.add_argument("--campus", "-c", help="校区")
    parser.add_argument("--sport", "-s", help="体育项目")
    parser.add_argument("--date", "-d", type=int, help="日期索引: 0=今天, 1=明天, 2=后天")
    parser.add_argument("--time-slot", "-t", help="时间段")
    parser.add_argument("--dry-run", action="store_true", help="干跑模式")
    parser.add_argument("--report", action="store_true", help="运行后打开报告")

    args = parser.parse_args()

    # Load configuration
    config = Config.load("configs/config.yaml")

    # Override with CLI args if provided
    username = args.username or os.environ.get("SZU_USERNAME")
    password = args.password or os.environ.get("SZU_PASSWORD")
    campus = args.campus or config.default_campus
    sport = args.sport or config.default_sport
    date = args.date if args.date is not None else config.default_date_index
    time_slot = args.time_slot or config.default_time_slot

    # Validate credentials
    if not username or not password:
        print("错误: 需要提供账号密码")
        print("  设置环境变量: export SZU_USERNAME=your_username SZU_PASSWORD=your_password")
        print("  或命令行参数: --username USERNAME --password PASSWORD")
        return

    # Initialize RunManager - this creates isolated run directory
    run_manager = RunManager()
    run = run_manager.start_run(
        campus=campus,
        sport=sport,
        dry_run=args.dry_run
    )

    # Mask username for display
    masked_username = username[:4] + "****" + username[-4:] if len(username) > 8 else "****"

    print("\n" + "=" * 60)
    print("深圳大学体育馆预约系统" + (" [DRY RUN]" if args.dry_run else ""))
    print("=" * 60)
    print(f"Trace ID: {run.trace_id[:8]}...")
    print(f"账号: {masked_username}")
    print(f"校区: {campus} | 项目: {sport} | 时间: {time_slot}")
    print(f"报告目录: {run.run_dir}")
    print("=" * 60 + "\n")

    run_manager.log("程序启动", campus=campus, sport=sport, dry_run=args.dry_run)

    # Run the booking
    success = False
    error_message = None

    try:
        client = BookingClient()

        if args.dry_run:
            run_manager.log("使用模拟浏览器 (dry run)")
            browser = FakeBrowserLifecycle()
        else:
            run_manager.log("使用真实浏览器")
            browser = CloakBrowserLifecycle()

        browser.launch(headless=False)
        client.set_browser(browser)

        run_manager.log_step("初始化浏览器", "success", 0)

        # Navigate
        run_manager.log_step("启动", "started")
        client.open(config.venue_url)
        run_manager.log_step("启动", "success")

        # Login
        run_manager.log_step("用户登录", "started")
        client.login(username, password)
        run_manager.log_step("用户登录", "success")

        # Select campus
        run_manager.log_step("选择校区", "started", campus=campus)
        try:
            client.select_campus(campus)
            run_manager.log_step("选择校区", "success")
        except ClickError as e:
            run_manager.log_step("选择校区", "failed", error=str(e))
            raise

        # Select sport
        run_manager.log_step("选择项目", "started", sport=sport)
        try:
            client.select_sport(sport)
            run_manager.log_step("选择项目", "success")
        except ClickError as e:
            run_manager.log_step("选择项目", "failed", error=str(e))
            raise

        # Select time slot
        run_manager.log_step("选择时间段", "started", time_slot=time_slot)
        try:
            client.select_time_slot(time_slot)
            run_manager.log_step("选择时间段", "success")
        except SlotUnavailableError as e:
            run_manager.log_step("选择时间段", "failed", error=str(e))
            raise

        # Select venue
        run_manager.log_step("选择场地", "started")
        try:
            client.select_venue()
            run_manager.log_step("选择场地", "success")
        except (SlotUnavailableError, ClickError) as e:
            run_manager.log_step("选择场地", "failed", error=str(e))
            raise

        # Confirm
        run_manager.log_step("确认预约", "started")
        client.confirm()
        run_manager.log_step("确认预约", "success")

        success = True
        run_manager.log("预约完成")

    except (ClickError, SlotUnavailableError) as e:
        error_message = str(e)
        run_manager.log("预约失败", level="ERROR", error=error_message)
        print(f"\n错误: {error_message}")

    except Exception as e:
        error_message = f"未知错误: {e}"
        run_manager.log("预约失败", level="ERROR", error=error_message)
        print(f"\n错误: {error_message}")
        import traceback
        traceback.print_exc()

    finally:
        # End run
        run_manager.end_run(success=success, error_message=error_message)

        # Save summary
        summary = {
            "trace_id": run.trace_id,
            "campus": campus,
            "sport": sport,
            "time_slot": time_slot,
            "success": success,
            "error": error_message
        }
        run_manager.save_summary(summary)

        print(f"\n报告目录: {run.run_dir}")
        print(f"Trace ID: {run.trace_id}")

        if args.report:
            html_path = generate_and_open_report(run.trace_id, run_manager)
            print(f"已打开报告: {html_path}")


if __name__ == "__main__":
    main()
