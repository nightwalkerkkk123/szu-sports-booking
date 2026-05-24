"""Tests for TraceViewer."""
import json
from pathlib import Path

from booking.observability.trace_viewer import generate_trace_html, generate_report_html


class TestTraceViewer:
    """Tests for trace_viewer."""

    def test_generate_trace_html(self, tmp_path):
        """generate_trace_html 生成 HTML"""
        entries = [
            {
                "timestamp": "2026-05-24T15:00:00.000000",
                "level": "INFO",
                "message": "程序启动",
                "trace_id": "test-trace"
            },
            {
                "timestamp": "2026-05-24T15:00:01.000000",
                "level": "INFO",
                "message": "登录成功",
                "trace_id": "test-trace"
            },
            {
                "timestamp": "2026-05-24T15:00:02.000000",
                "level": "ERROR",
                "message": "选择校区失败",
                "trace_id": "test-trace",
                "error": "未找到元素"
            }
        ]

        html_path = str(tmp_path / "trace_test.html")
        html = generate_trace_html("test-trace", entries, html_path)

        assert "<!DOCTYPE html>" in html
        assert "test-trace" in html
        assert Path(html_path).exists()

    def test_generate_trace_html_empty(self, tmp_path):
        """generate_trace_html 空条目"""
        html_path = str(tmp_path / "trace_empty.html")
        html = generate_trace_html("test-empty", [], html_path)

        assert "<!DOCTYPE html>" in html
        assert "test-empty" in html

    def test_generate_trace_html_has_stats(self, tmp_path):
        """generate_trace_html 包含统计信息"""
        entries = [
            {"timestamp": "2026-05-24T15:00:00", "level": "INFO",
             "message": "消息1"},
            {"timestamp": "2026-05-24T15:00:01", "level": "WARNING",
             "message": "消息2"},
            {"timestamp": "2026-05-24T15:00:02", "level": "ERROR",
             "message": "消息3"},
        ]

        html_path = str(tmp_path / "trace_stats.html")
        html = generate_trace_html("test-stats", entries, html_path)

        assert "INFO" in html
        assert "WARNING" in html
        assert "ERROR" in html

    def test_generate_trace_html_no_output_path(self):
        """generate_trace_html 不指定输出路径"""
        entries = [
            {"timestamp": "2026-05-24T15:00:00", "level": "INFO",
             "message": "测试"}
        ]
        html = generate_trace_html("test-no-path", entries)
        assert "test-no-path" in html

    def test_generate_report_html(self, tmp_path):
        """generate_report_html 生成多 trace 报告"""
        # Create log file with multiple traces
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True)

        log_data = [
            {"trace_id": "trace-aaa", "level": "INFO", "message": "消息A"},
            {"trace_id": "trace-bbb", "level": "INFO", "message": "消息B"},
            {"trace_id": "trace-aaa", "level": "ERROR", "message": "错误A"},
        ]

        log_file = log_dir / "booking.json.log"
        with open(log_file, "w") as f:
            for entry in log_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        output_dir = tmp_path / "reports"
        results = generate_report_html(
            ["trace-aaa", "trace-bbb"],
            log_dir=str(log_dir),
            output_dir=str(output_dir)
        )

        assert len(results) == 2
        assert "trace-aaa" in results

    def test_generate_report_html_missing_logs(self):
        """generate_report_html 日志文件不存在"""
        results = generate_report_html(
            ["test"], log_dir="/nonexistent", output_dir="/tmp/test"
        )
        assert results == {}
