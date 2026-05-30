"""CLI entry point for booking system."""
import subprocess
import sys
from pathlib import Path

import click

from booking.config import Config


@click.group()
def cli():
    """深圳大学体育馆预约工具"""
    pass


@cli.command()
@click.option("--config", "-c", default="configs/config.yaml", help="配置文件路径")
@click.option("--account", "-a", help="指定账号")
@click.option("--dry-run", is_flag=True, help="干跑模式")
@click.option("--all", "run_all_flag", is_flag=True, help="执行所有账号（并发），默认是成功一个就停")
def run(config, account, dry_run, run_all_flag):
    """运行预约任务

    默认行为：run_until_success — 串行尝试，一个成功就停。
    加 --all：run_all — 并发执行所有账号，适合同一账号抢多个项目。
    """
    from booking.pool import BookingPool
    from booking.observability.run_manager import RunManager

    if dry_run:
        click.echo("干跑模式，不实际预约")

    try:
        cfg = Config.load(config)
        click.echo(f"配置加载成功: {cfg.default_campus} {cfg.default_sport}")
    except FileNotFoundError:
        click.echo(f"配置文件不存在: {config}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"配置加载失败: {e}", err=True)
        raise click.Abort()

    # 生成 trace_id 并创建预约池
    import uuid
    trace_id = str(uuid.uuid4())
    pool = BookingPool(dry_run=dry_run, trace_id=trace_id)

    # 全局预约参数
    pool.update_config(
        url=cfg.venue_url,
        campus=cfg.default_campus,
        sport=cfg.default_sport,
        date_index=cfg.default_date_index,
        time_slot=cfg.default_time_slot,
    )

    # 加载账号
    import os

    def _get_password(username: str) -> str:
        """从环境变量获取密码，约定命名：SZU_PASSWORD_{后4位}"""
        suffix = username[-4:]
        return os.environ.get(f"SZU_PASSWORD_{suffix}") or os.environ.get("SZU_PASSWORD", "")

    if account:
        # --account 指定单个账号
        password = _get_password(account)
        pool.add_account(account, password)
        click.echo(f"使用指定账号: {account}")
    elif cfg.accounts:
        # config.yaml 中的多账号列表
        for acc_entry in cfg.accounts:
            username = acc_entry.get("username", "")
            if not username:
                continue
            password = _get_password(username)
            per_config = {
                k: v for k, v in acc_entry.items()
                if k in ("default_campus", "default_sport", "default_time_slot", "default_date_index") and v
            }
            if per_config:
                pool.add_account(username, password, config=per_config)
                click.echo(f"加载账号: {username} (独立配置: {per_config})")
            else:
                pool.add_account(username, password)
                click.echo(f"加载账号: {username} (使用全局配置)")
        click.echo(f"共加载 {len(cfg.accounts)} 个账号")
    else:
        # 回退：从环境变量读取
        import os
        accounts = os.environ.get("SZU_ACCOUNTS", "")
        if accounts:
            for acc in accounts.split(","):
                parts = acc.strip().split(":")
                if len(parts) >= 2:
                    pool.add_account(parts[0], parts[1])
            click.echo(f"加载了 {len(pool.accounts)} 个账号（来自环境变量）")
        else:
            username = os.environ.get("SZU_USERNAME")
            password = os.environ.get("SZU_PASSWORD")
            if username and password:
                pool.add_account(username, password)
                click.echo(f"使用默认账号: {username}")
            else:
                click.echo("没有可用的账号，请在 config.yaml 或环境变量中配置", err=True)
                raise click.Abort()

    # 启动 RunManager（使用同一个 trace_id）
    run_manager = RunManager()
    run_record = run_manager.start_run(
        campus=cfg.default_campus,
        sport=cfg.default_sport,
        dry_run=dry_run,
        trace_id=trace_id
    )
    click.echo(f"Trace ID: {trace_id}")

    # 执行预约
    try:
        if run_all_flag:
            click.echo(f"\n开始并发执行 {len(pool.accounts)} 个账号...")
            run_manager.log(f"并发执行 {len(pool.accounts)} 个账号", level="INFO")
            results = pool.run_all(concurrent=True)
            success_count = sum(1 for r in results if r.status == "success")
            for r in results:
                run_manager.log(r.message, level=r.status.upper(),
                                username=r.username, time_slot=r.time_slot)
            click.echo(f"\n执行完成: {success_count}/{len(results)} 成功")
            run_manager.end_run(success=success_count > 0)
        else:
            click.echo("\n开始执行预约（成功一个即停）...")
            result = pool.run_until_success(timeout=300)

            if result and result.status == "success":
                click.echo(f"\n[OK] 预约成功! 账号: {result.username}")
                run_manager.end_run(success=True)
            else:
                click.echo("\n[X] 预约失败，所有账号都未能成功")
                run_manager.end_run(success=False, error_message="所有账号都未能成功预约")
    except KeyboardInterrupt:
        click.echo("\n用户中断执行")
        run_manager.end_run(success=False, error_message="用户中断")
        raise click.Abort()
    except Exception as e:
        click.echo(f"\n[X] 执行出错: {e}")
        run_manager.end_run(success=False, error_message=str(e))
        raise click.Abort()


@cli.command()
@click.option("--username", "-u", required=True, help="学号")
@click.option("--password", "-p", required=True, help="密码")
@click.option("--headless", is_flag=True, help="无头模式运行浏览器")
def test_login(username, password, headless):
    """测试登录

    测试账号密码是否能够成功登录体育馆预约系统。
    """
    from booking.client import BookingClient

    click.echo(f"测试登录: {username}")
    click.echo("-" * 40)

    client = BookingClient(use_fake_browser=headless)

    try:
        # 启动浏览器
        browser = client._ensure_browser()
        browser.launch(headless=headless)

        # 打开登录页
        login_url = "https://authserver.szu.edu.cn/authserver/login"
        client.open(login_url)
        client.wait(1)

        # 执行登录
        client.login(username, password)
        client.wait(2)

        # 检查是否登录成功（通过 URL 或页面元素判断）
        current_url = client.page.url if hasattr(client, 'page') and client.page else ""

        # 登录成功后会跳转到预约页面
        if "sportVenue" in current_url or "lwSzuCgyy" in current_url:
            click.echo("[OK] 登录成功!")
            result = True
        else:
            # 检查是否有错误提示
            page_content = client.page.content() if hasattr(client, 'page') and client.page else ""
            if "密码错误" in page_content or "password" in page_content.lower():
                click.echo("[X] 登录失败: 密码错误")
            elif "不存在" in page_content or "not exist" in page_content.lower():
                click.echo("[X] 登录失败: 账号不存在")
            else:
                click.echo("? 登录状态未知，请手动检查浏览器窗口")
            result = False

    except Exception as e:
        click.echo(f"[X] 登录失败: {e}")
        result = False
    finally:
        client.close()

    click.echo("-" * 40)
    raise SystemExit(0 if result else 1)


@cli.command()
@click.option("--config", "-c", default="configs/config.yaml", help="配置文件路径")
def validate_config(config):
    """验证配置"""
    try:
        cfg = Config.load(config)
        click.echo("配置有效")
        click.echo(f"  校区: {cfg.default_campus}")
        click.echo(f"  项目: {cfg.default_sport}")
        click.echo(f"  时间段: {cfg.default_time_slot}")
    except Exception as e:
        click.echo(f"配置错误: {e}", err=True)
        raise click.Abort()


@cli.command()
def smoke():
    """运行冒烟测试"""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/smoke", "-v"],
        cwd=Path(__file__).parent.parent.parent
    )
    raise SystemExit(result.returncode)


@cli.command()
@click.option("--dir", "-d", default="logs", help="日志目录")
def report(dir):
    """生成报告"""
    from booking.observability.reporter import Reporter
    from datetime import datetime

    reporter = Reporter()
    summary = reporter.get_summary(days=7)

    click.echo("=== 预约报告 ===")
    click.echo(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"7天成功率: {summary['success_rate'] * 100:.1f}%")
    click.echo(f"最近记录: {summary['total_records']} 条")

    if summary.get("recent_records"):
        click.echo("\n最近10条记录:")
        for record in summary["recent_records"]:
            status_icon = "[OK]" if record.get("status") == "success" else "[X]"
            click.echo(f"  {status_icon} {record.get('account', '')}")


@cli.command()
@click.option("--trace-id", "-t", help="Trace ID")
@click.option("--latest", is_flag=True, help="打开最新报告")
def trace(trace_id, latest):
    """生成运行报告 HTML"""
    from booking.observability.run_manager import RunManager
    from booking.observability.report_generator import generate_and_open_report

    rm = RunManager()

    if latest:
        runs = rm.query_runs(limit=1)
        if not runs:
            click.echo("没有找到任何运行记录", err=True)
            raise click.Abort()
        trace_id = runs[0]["trace_id"]

    if not trace_id:
        click.echo("需要提供 --trace-id 或 --latest", err=True)
        raise click.Abort()

    try:
        html_path = generate_and_open_report(trace_id, rm)
        click.echo(f"[OK] 报告已生成: {html_path}")
    except ValueError as e:
        click.echo(f"错误: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--limit", "-n", default=10, help="显示条数")
def runs(limit):
    """列出最近运行记录"""
    from booking.observability.run_manager import RunManager

    rm = RunManager()
    recent = rm.query_runs(limit=limit)

    if not recent:
        click.echo("没有找到运行记录")
        return

    click.echo(f"{'Trace ID':<12} {'状态':<10} {'校区':<8} {'项目':<6} {'时间'}")
    click.echo("-" * 60)
    for r in recent:
        status_icon = {"success": "[OK]", "failed": "[X]", "running": "▶"}.get(r["status"], "?")
        campus = r.get("campus", "") or "-"
        sport = r.get("sport", "") or "-"
        time_str = r["start_time"][:19].replace("T", " ")
        click.echo(f"{r['trace_id'][:8]:<12} {status_icon}{r['status']:<8} {campus:<8} {sport:<6} {time_str}")


cli.add_command(run)
cli.add_command(test_login)
cli.add_command(validate_config)
cli.add_command(smoke)
cli.add_command(report)
cli.add_command(trace)
cli.add_command(runs)


if __name__ == "__main__":
    cli()