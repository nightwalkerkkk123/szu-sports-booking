"""HTML report generator for traces."""
from datetime import datetime
from pathlib import Path
from typing import Any


def generate_trace_html(trace_id: str, entries: list[dict[str, Any]], output_path: str | None = None) -> str:
    """Generate an HTML report for a trace.

    Args:
        trace_id: The trace ID
        entries: List of log entries for this trace
        output_path: Optional path to save the HTML file

    Returns:
        The HTML content as a string
    """
    # Group entries by level
    level_colors = {
        "DEBUG": "#6c757d",
        "INFO": "#0d6efd",
        "WARNING": "#ffc107",
        "ERROR": "#dc3545",
    }

    # Calculate duration from first to last entry
    if len(entries) >= 2:
        try:
            first_ts = datetime.fromisoformat(entries[0]["timestamp"])
            last_ts = datetime.fromisoformat(entries[-1]["timestamp"])
            duration_ms = int((last_ts - first_ts).total_seconds() * 1000)
            duration_str = f"{duration_ms}ms"
        except Exception:
            duration_str = "N/A"
    else:
        duration_str = "N/A"

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trace {trace_id[:8]}...</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .header .trace-id {{ font-family: monospace; background: rgba(255,255,255,0.2); padding: 8px 12px; border-radius: 6px; display: inline-block; }}
        .header .meta {{ display: flex; gap: 20px; margin-top: 15px; font-size: 14px; opacity: 0.9; }}
        .header .meta span {{ background: rgba(255,255,255,0.15); padding: 6px 12px; border-radius: 20px; }}
        .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; overflow: hidden; }}
        .card-header {{ padding: 15px 20px; border-bottom: 1px solid #eee; font-weight: 600; color: #333; }}
        .card-body {{ padding: 0; }}
        .timeline {{ padding: 20px; }}
        .entry {{ display: flex; gap: 15px; padding: 12px 0; border-bottom: 1px solid #f0f0f0; }}
        .entry:last-child {{ border-bottom: none; }}
        .entry .time {{ min-width: 80px; color: #666; font-size: 13px; padding-top: 2px; }}
        .entry .level {{ min-width: 70px; }}
        .entry .level .badge {{ padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; color: white; }}
        .entry .content {{ flex: 1; }}
        .entry .message {{ font-size: 14px; color: #333; margin-bottom: 4px; }}
        .entry .details {{ font-size: 12px; color: #888; }}
        .entry .details span {{ background: #f5f5f5; padding: 2px 8px; border-radius: 4px; margin-right: 6px; }}
        .success {{ background: #198754; }}
        .warning {{ background: #ffc107; color: #333 !important; }}
        .error {{ background: #dc3545; }}
        .info {{ background: #0d6efd; }}
        .debug {{ background: #6c757d; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
        .stat {{ background: white; padding: 20px; border-radius: 12px; text-align: center; }}
        .stat .value {{ font-size: 28px; font-weight: 700; color: #333; }}
        .stat .label {{ font-size: 13px; color: #888; margin-top: 5px; }}
        .footer {{ text-align: center; color: #888; font-size: 12px; padding: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Trace 追踪报告</h1>
            <div class="trace-id">{trace_id}</div>
            <div class="meta">
                <span>📊 {len(entries)} 条记录</span>
                <span>⏱️ {duration_str}</span>
                <span>🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
            </div>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="value">{len([e for e in entries if e.get('level') == 'INFO'])}</div>
                <div class="label">INFO</div>
            </div>
            <div class="stat">
                <div class="value">{len([e for e in entries if e.get('level') == 'WARNING'])}</div>
                <div class="label">WARNING</div>
            </div>
            <div class="stat">
                <div class="value">{len([e for e in entries if e.get('level') == 'ERROR'])}</div>
                <div class="label">ERROR</div>
            </div>
            <div class="stat">
                <div class="value">{duration_str}</div>
                <div class="label">总耗时</div>
            </div>
        </div>

        <div class="card" style="margin-top: 20px;">
            <div class="card-header">📋 执行详情</div>
            <div class="card-body">
                <div class="timeline">
"""

    for entry in entries:
        level = entry.get("level", "INFO")
        timestamp = entry.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%H:%M:%S")
        except Exception:
            time_str = timestamp

        message = entry.get("message", "")

        # Get extra fields
        extras = {k: v for k, v in entry.items()
                  if k not in ("timestamp", "level", "logger", "message", "trace_id")}
        extra_html = ""
        if extras:
            extra_parts = []
            for k, v in extras.items():
                extra_parts.append(f"<span>{k}={v}</span>")
            extra_html = f'<div class="details">{" ".join(extra_parts)}</div>'

        level_class = level.lower()
        if level == "INFO":
            level_class = "info"
        elif level == "WARNING":
            level_class = "warning"
        elif level == "ERROR":
            level_class = "error"

        html += f"""
                    <div class="entry">
                        <div class="time">{time_str}</div>
                        <div class="level"><span class="badge {level_class}">{level}</span></div>
                        <div class="content">
                            <div class="message">{message}</div>
                            {extra_html}
                        </div>
                    </div>
"""

    html += """
                </div>
            </div>
        </div>

        <div class="footer">
            Generated by 登录体育馆 booking system
        </div>
    </div>
</body>
</html>
"""

    # Save to file if output_path is provided
    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")

    return html


def generate_report_html(trace_ids: list[str], log_dir: str = "logs/booking", output_dir: str = "logs/booking") -> dict[str, str]:
    """Generate HTML reports for multiple traces.

    Args:
        trace_ids: List of trace IDs to include
        log_dir: Directory containing log files
        output_dir: Directory to save HTML reports

    Returns:
        Dictionary mapping trace_id to output file path
    """
    import json
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    log_path = Path(log_dir) / "booking.json.log"
    if not log_path.exists():
        return {}

    # Read all log entries
    all_entries: dict[str, list[dict]] = {}
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                tid = data.get("trace_id")
                if tid in trace_ids:
                    if tid not in all_entries:
                        all_entries[tid] = []
                    all_entries[tid].append(data)
            except json.JSONDecodeError:
                continue

    # Generate HTML for each trace
    results = {}
    for tid, entries in all_entries.items():
        output_file = output_path / f"trace_{tid[:8]}.html"
        generate_trace_html(tid, entries, str(output_file))
        results[tid] = str(output_file)

    return results