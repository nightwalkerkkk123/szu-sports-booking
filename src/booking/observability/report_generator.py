"""HTML report generator for run reports."""
import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


def generate_html_report(
    trace_id: str,
    run_manager=None,
    output_path: str | None = None
) -> str:
    """Generate HTML report for a run.

    Args:
        trace_id: Trace ID of the run
        run_manager: RunManager instance (uses global if not provided)
        output_path: Output HTML file path

    Returns:
        Path to generated HTML file
    """
    if run_manager is None:
        from booking.observability.run_manager import get_run_manager
        run_manager = get_run_manager()

    # Get run data
    run = run_manager.get_run_by_trace(trace_id)
    if run is None:
        raise ValueError(f"Run not found: {trace_id}")

    logs = run_manager.get_run_logs(trace_id)
    steps = run_manager.get_run_steps(trace_id)

    # Calculate stats
    total_duration_ms = 0
    if steps:
        total_duration_ms = sum(s.get("duration_ms", 0) for s in steps)

    success_count = sum(1 for s in steps if s.get("status") == "success")
    failed_count = sum(1 for s in steps if s.get("status") == "failed")
    total_steps = len(steps)
    success_rate = (success_count / total_steps * 100) if total_steps > 0 else 0

    # Build HTML
    status_color = {
        "success": "#198754",
        "failed": "#dc3545",
        "running": "#0d6efd",
        "cancelled": "#ffc107"
    }.get(run["status"], "#6c757d")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>预约报告 {trace_id[:8]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .header .trace-id {{ font-family: monospace; background: rgba(255,255,255,0.2); padding: 8px 12px; border-radius: 6px; display: inline-block; }}
        .header .meta {{ display: flex; gap: 15px; margin-top: 15px; flex-wrap: wrap; }}
        .header .meta span {{ background: rgba(255,255,255,0.15); padding: 6px 12px; border-radius: 20px; font-size: 13px; }}
        .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; color: white; font-size: 12px; font-weight: 600; background: {status_color}; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat {{ background: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .stat .value {{ font-size: 28px; font-weight: 700; color: #333; }}
        .stat .label {{ font-size: 13px; color: #888; margin-top: 5px; }}
        .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; overflow: hidden; }}
        .card-header {{ padding: 15px 20px; border-bottom: 1px solid #eee; font-weight: 600; color: #333; display: flex; justify-content: space-between; align-items: center; }}
        .card-body {{ padding: 0; }}
        .steps {{ padding: 20px; }}
        .step {{ display: flex; gap: 15px; padding: 12px 0; border-bottom: 1px solid #f0f0f0; }}
        .step:last-child {{ border-bottom: none; }}
        .step .time {{ min-width: 80px; color: #666; font-size: 13px; padding-top: 2px; }}
        .step .status {{ min-width: 70px; }}
        .step .badge {{ padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; color: white; }}
        .step .badge.success {{ background: #198754; }}
        .step .badge.failed {{ background: #dc3545; }}
        .step .badge.started {{ background: #0d6efd; }}
        .step .badge.skipped {{ background: #ffc107; color: #333 !important; }}
        .step .content {{ flex: 1; }}
        .step .name {{ font-size: 14px; color: #333; margin-bottom: 4px; }}
        .step .details {{ font-size: 12px; color: #888; }}
        .step .error {{ color: #dc3545; margin-top: 4px; }}
        .step .duration {{ color: #666; font-size: 12px; margin-left: auto; }}
        .logs {{ padding: 20px; max-height: 400px; overflow-y: auto; }}
        .log-entry {{ padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; font-family: 'Monaco', 'Menlo', monospace; font-size: 13px; }}
        .log-entry.INFO {{ background: #e7f3ff; border-left: 3px solid #0d6efd; }}
        .log-entry.WARNING {{ background: #fff3cd; border-left: 3px solid #ffc107; }}
        .log-entry.ERROR {{ background: #f8d7da; border-left: 3px solid #dc3545; }}
        .log-entry .timestamp {{ color: #666; margin-right: 10px; }}
        .log-entry .message {{ color: #333; }}
        .footer {{ text-align: center; color: #888; font-size: 12px; padding: 20px; }}
        .empty {{ padding: 40px; text-align: center; color: #888; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 预约执行报告</h1>
            <div class="trace-id">{trace_id}</div>
            <div class="meta">
                <span>📊 {total_steps} 步骤</span>
                <span>⏱️ {total_duration_ms}ms</span>
                <span>📅 {run['start_time'][:19].replace('T', ' ')}</span>
                <span class="status-badge">{run['status']}</span>
                {"<span>🧪 干跑模式</span>" if run["dry_run"] else ""}
            </div>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="value">{success_count}</div>
                <div class="label">成功</div>
            </div>
            <div class="stat">
                <div class="value">{failed_count}</div>
                <div class="label">失败</div>
            </div>
            <div class="stat">
                <div class="value">{success_rate:.0f}%</div>
                <div class="label">成功率</div>
            </div>
            <div class="stat">
                <div class="value">{total_duration_ms}ms</div>
                <div class="label">总耗时</div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                📋 执行步骤
                <span style="font-weight: normal; color: #888;">{len(steps)} 步骤</span>
            </div>
            <div class="card-body">
"""

    if steps:
        html += '<div class="steps">'
        for step in steps:
            status = step.get("status", "started")
            status_class = {
                "success": "success",
                "failed": "failed",
                "started": "started",
                "skipped": "skipped"
            }.get(status, "started")

            ts = step.get("timestamp", "")
            time_str = ts[11:19] if len(ts) > 19 else ts

            html += f"""
                <div class="step">
                    <div class="time">{time_str}</div>
                    <div class="status"><span class="badge {status_class}">{status}</span></div>
                    <div class="content">
                        <div class="name">{step.get('step', 'Unknown')}</div>
"""
            if step.get("error"):
                html += f'<div class="error">错误: {step["error"]}</div>'

            details = {k: v for k, v in step.items()
                      if k not in ("timestamp", "trace_id", "step", "status", "duration_ms", "error")}
            if details:
                details_str = " | ".join(f"{k}={v}" for k, v in details.items())
                html += f'<div class="details">{details_str}</div>'

            html += f"""
                    </div>
                    <div class="duration">{step.get('duration_ms', 0)}ms</div>
                </div>
"""
        html += '</div>'
    else:
        html += '<div class="empty">暂无步骤记录</div>'

    html += """
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                📝 运行日志
                <span style="font-weight: normal; color: #888;">""" + str(len(logs)) + """ 条</span>
            </div>
            <div class="card-body">
"""

    if logs:
        html += '<div class="logs">'
        for log in logs:
            level = log.get("level", "INFO")
            ts = log.get("timestamp", "")
            time_str = ts[11:19] if len(ts) > 19 else ts
            message = log.get("message", "")

            # Filter out trace_id for display
            display_fields = {k: v for k, v in log.items()
                           if k not in ("timestamp", "level", "logger", "message", "trace_id")}
            extras = ""
            if display_fields:
                extras = " | " + " | ".join(f"{k}={v}" for k, v in display_fields.items())

            html += f"""
                <div class="log-entry {level}">
                    <span class="timestamp">{time_str}</span>
                    <span class="message">{message}{extras}</span>
                </div>
"""
        html += '</div>'
    else:
        html += '<div class="empty">暂无日志记录</div>'

    html += """
            </div>
        </div>

        <div class="footer">
            Generated by 登录体育馆 booking system
        </div>
    </div>
</body>
</html>
"""

    # Save to file
    if output_path is None:
        run_dir = Path(run["run_dir"])
        output_path = run_dir / "report.html"

    Path(output_path).write_text(html, encoding="utf-8")
    return str(output_path)


def open_report_in_browser(html_path: str) -> None:
    """Open HTML report in default browser.

    Args:
        html_path: Path to HTML file
    """
    path = Path(html_path).resolve()
    url = f"file://{path}"

    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", url])
    elif system == "Windows":
        subprocess.run(["start", "", url], shell=True)
    else:
        subprocess.run(["xdg-open", url])


def generate_and_open_report(trace_id: str, run_manager=None) -> str:
    """Generate report and open in browser.

    Args:
        trace_id: Trace ID of the run
        run_manager: RunManager instance

    Returns:
        Path to generated HTML file
    """
    html_path = generate_html_report(trace_id, run_manager)
    open_report_in_browser(html_path)
    return html_path