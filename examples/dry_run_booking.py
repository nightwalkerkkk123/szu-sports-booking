#!/usr/bin/env python3
"""
dry_run_booking.py - 模拟预约流程（不访问真实系统）

演示如何使用 FakeBrowserLifecycle 执行模拟预约流程。
此脚本不启动真实浏览器，不访问深圳大学内网。

运行：
    PYTHONPATH=src python examples/dry_run_booking.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from booking.browser import FakeBrowserLifecycle
from booking.account import AccountManager
from booking.config import Config
from booking.observability.logger import Logger
from booking.observability.tracer import generate_trace_id


def main():
    """执行模拟预约流程。"""
    print("=" * 60)
    print("模拟预约流程（Dry Run）")
    print("=" * 60)

    # 0. 初始化日志
    trace_id = generate_trace_id()
    logger = Logger("booking")
    logger.inject_trace_id(trace_id)
    logger.info("Dry run 开始")

    # 1. 使用 FakeBrowser
    print("\n[1] 初始化浏览器（模拟）...")
    browser = FakeBrowserLifecycle()
    browser.launch(headless=True)
    print(f"    浏览器已启动: {browser.is_launched()}")
    logger.info("浏览器启动成功")

    # 2. 加载配置
    print("\n[2] 加载配置...")
    config = Config.load("configs/config.yaml")
    print(f"    校区: {config.default_campus}")
    print(f"    项目: {config.default_sport}")
    print(f"    时间段: {config.default_time_slot}")
    logger.info("配置加载完成", campus=config.default_campus, sport=config.default_sport)

    # 3. 账号管理
    print("\n[3] 账号管理...")
    manager = AccountManager()
    manager.add_account("test_user_1", "password_1", priority=2)
    manager.add_account("test_user_2", "password_2", priority=1)
    print(f"    账号数量: {len(manager)}")

    account = manager.get_available_account()
    if account:
        print(f"    选中账号: {account.username} (优先级: {account.priority})")
        logger.info("账号选中", account=account.username)

    # 4. 模拟预约流程
    print("\n[4] 模拟预约流程...")
    page = browser.page

    # 模拟登录
    print("    - 登录...")
    page.goto(config.venue_url)
    print(f"    - 导航到: {config.venue_url}")
    logger.info("页面导航", url=config.venue_url)

    # 模拟选择
    print("    - 选择校区...")
    print(f"    - 选择项目: {config.default_sport}")
    print(f"    - 选择日期索引: {config.default_date_index}")
    print(f"    - 选择时间段: {config.default_time_slot}")
    logger.info("预约流程完成")

    # 5. 完成
    print("\n[5] 完成")
    browser.close()
    print("    浏览器已关闭")
    logger.info("Dry run 结束")

    print("\n" + "=" * 60)
    print("Dry Run 完成！未访问任何真实系统。")
    print("=" * 60)


if __name__ == "__main__":
    main()